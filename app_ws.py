#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人消息监听与邮件转发服务
使用飞书官方 lark-oapi SDK 的长连接模式（WebSocket）
支持日报自动收集和定时汇总功能
"""

import json
import logging
import os
import sys
import signal
import time
from datetime import datetime, timedelta
from threading import Thread, Event, Timer
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.ws import Client as WSClient
from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from config.config import Config
from utils.keyword_matcher import KeywordMatcher
from utils.email_sender import EmailSender
from utils.daily_report_parser import DailyReportParser
from utils.daily_report_storage import DailyReportStorage
from utils.report_table_generator import ReportTableGenerator
from utils.reminder_sender import ReminderSender
from utils.vacation_manager import VacationManager
from utils.command_router import get_command_router
from utils.command_handler import CommandHandler

# 确保 logs 目录存在
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 屏蔽飞书 SDK 的 WebSocket 连接日志噪音
# "no close frame received or sent" 是正常的连接刷新，不是真正的错误
logging.getLogger('Lark').setLevel(logging.CRITICAL)  # 只显示严重错误

# 初始化配置和工具类
config = Config()
keyword_matcher = KeywordMatcher(config)
email_sender = EmailSender(config)

# 初始化日报相关工具类
report_parser = DailyReportParser()
report_storage = DailyReportStorage(config.DAILY_REPORT_STORAGE_FILE)
table_generator = ReportTableGenerator()
reminder_sender = ReminderSender(config.APP_ID, config.APP_SECRET, config.DAILY_REPORT_REQUIRED_USERS)
vacation_manager = VacationManager(config.VACATION_STORAGE_FILE)
command_router = get_command_router()
command_handler = CommandHandler(config.APP_ID, config.APP_SECRET)

# 初始化定时任务调度器
scheduler = BackgroundScheduler()

# 用户级别的容错期管理
# 结构：{sender_name: {'timer': Timer对象, 'message_id': str, 'submit_time': datetime}}
user_timers = {}

# WebSocket连接管理
ws_client = None
shutdown_event = Event()

# 加载用户姓名映射
user_names_map = {}
try:
    user_names_file = 'config/user_names.json'
    if os.path.exists(user_names_file):
        with open(user_names_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            user_names_map = data.get('映射', {})
            logger.info(f"加载用户姓名映射: {len(user_names_map)} 个用户")
except Exception as e:
    logger.warning(f"加载用户姓名映射失败: {str(e)}")


def parse_date_from_command(text: str) -> str:
    """
    从命令中解析日期参数
    
    支持格式：
    - "汇总昨天日报" -> 昨天的日期
    - "汇总1.14日报" -> 2026-01-14
    - "汇总1月14日报" -> 2026-01-14
    - "汇总2026-01-14日报" -> 2026-01-14
    - "汇总日报" -> 智能判断（如果今天有日报用今天，否则用昨天）
    
    Args:
        text: 命令文本
        
    Returns:
        str: 日期字符串 (YYYY-MM-DD)
    """
    import re
    
    # 检查是否指定了"昨天"
    if "昨天" in text or "昨日" in text:
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime('%Y-%m-%d')
    
    # 检查是否指定了"前天"
    if "前天" in text:
        day_before_yesterday = datetime.now() - timedelta(days=2)
        return day_before_yesterday.strftime('%Y-%m-%d')
    
    # 检查完整日期格式：YYYY-MM-DD 或 YYYY/MM/DD
    match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 检查月日格式：MM.DD 或 M.D
    match = re.search(r'(\d{1,2})\.(\d{1,2})', text)
    if match:
        month, day = match.groups()
        year = datetime.now().year
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 检查中文月日格式：M月D日 或 M月D号
    match = re.search(r'(\d{1,2})月(\d{1,2})[日号]', text)
    if match:
        month, day = match.groups()
        year = datetime.now().year
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 如果没有指定日期，智能判断
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = report_storage.get_report_count(today)
    
    if today_count > 0:
        # 今天有日报，使用今天
        return today
    else:
        # 今天没有日报，使用昨天
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_date = yesterday.strftime('%Y-%m-%d')
        yesterday_count = report_storage.get_report_count(yesterday_date)
        
        if yesterday_count > 0:
            logger.info(f"💡 今天无日报，自动使用昨天的日期: {yesterday_date} ({yesterday_count}份)")
            return yesterday_date
        else:
            # 都没有，还是返回今天
            logger.info(f"⚠️  今天和昨天都没有日报，使用今天日期: {today}")
            return today



def get_user_name(sender_data, chat_id: str) -> str:
    """
    获取用户真实姓名（优先使用 user_names.json 中的配置映射）

    Args:
        sender_data: 飞书消息事件的sender对象
        chat_id: 群组ID

    Returns:
        str: 用户姓名
    """
    global user_names_map  # 在函数开始声明global

    try:
        # 安全获取 user_id，处理可能的 None 值
        if not sender_data or not sender_data.sender_id:
            return "未知用户"

        user_id = sender_data.sender_id.user_id
        if not user_id:  # user_id 为 None 或空字符串
            return "未知用户"

        # 1. 优先从 user_names.json 配置文件中获取（手动配置的映射不会被覆盖）
        if user_id in user_names_map:
            return user_names_map[user_id]

        # 2. 尝试从群成员列表API获取所有成员信息并缓存
        try:
            from lark_oapi.api.im.v1 import GetChatMembersRequest

            logger.info(f"正在从群成员列表API获取用户信息...")

            # 创建客户端
            client = lark.Client.builder() \
                .app_id(config.APP_ID) \
                .app_secret(config.APP_SECRET) \
                .build()

            # 构建请求
            request = GetChatMembersRequest.builder() \
                .chat_id(chat_id) \
                .member_id_type("user_id") \
                .page_size(100) \
                .build()

            # 发起请求
            response = client.im.v1.chat_members.get(request)

            if response.success() and response.data.items:
                members = response.data.items
                logger.info(f"✅ 获取到 {len(members)} 个群成员")

                # 缓存所有成员信息（但不覆盖已有的手动配置）
                for member in members:
                    member_user_id = member.member_id
                    member_name = member.name if hasattr(member, 'name') and member.name else f"用户_{member_user_id[-6:]}"
                    
                    # 只在用户不存在时才添加，保护手动配置的映射
                    if member_user_id not in user_names_map:
                        user_names_map[member_user_id] = member_name
                        save_user_to_config(member_user_id, member_name)

                # 返回目标用户的姓名
                if user_id in user_names_map:
                    logger.info(f"✅ 获取用户名成功: {user_id} -> {user_names_map[user_id]}")
                    return user_names_map[user_id]
            else:
                logger.warning(f"获取群成员列表失败: {response.msg if hasattr(response, 'msg') else '未知错误'}")

        except Exception as e:
            logger.warning(f"调用群成员列表API异常: {str(e)}")

        # 3. API失败，使用默认名称
        default_name = f"用户_{user_id[-6:]}"

        # 保存到内存缓存和配置文件
        user_names_map[user_id] = default_name
        save_user_to_config(user_id, default_name)

        logger.info(f"💡 用户 {user_id} 使用默认名称: {default_name}")
        logger.info(f"   可编辑 config/user_names.json 修改为真实姓名")

        return default_name

    except Exception as e:
        logger.error(f"获取用户名异常: {str(e)}", exc_info=True)
        return "未知用户"


def save_user_to_config(user_id: str, name: str):
    """
    保存用户映射到配置文件

    Args:
        user_id: 用户ID
        name: 用户名
    """
    try:
        user_names_file = 'config/user_names.json'
        existing_data = {
            "说明": "配置飞书用户ID到真实姓名的映射，格式：user_id: 姓名",
            "映射": {}
        }

        if os.path.exists(user_names_file):
            with open(user_names_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # 如果这个user_id还不在映射中，添加
        if user_id not in existing_data.get('映射', {}):
            existing_data.setdefault('映射', {})[user_id] = name

            with open(user_names_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.warning(f"保存用户映射到配置文件失败: {str(e)}")


def send_text_message(chat_id: str, text: str, receive_id_type: str = "chat_id"):
    """发送文本消息到群聊"""
    client = lark.Client.builder() \
        .app_id(config.APP_ID) \
        .app_secret(config.APP_SECRET) \
        .build()

    request = CreateMessageRequest.builder() \
        .receive_id_type(receive_id_type) \
        .request_body(CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(json.dumps({"text": text}, ensure_ascii=False))
            .build()) \
        .build()

    response = client.im.v1.message.create(request)
    if not response.success():
        raise RuntimeError(f"发送文本消息失败: {response.msg}")


def send_interactive_card(chat_id: str, card: dict, receive_id_type: str = "chat_id"):
    """发送交互式卡片消息"""
    client = lark.Client.builder() \
        .app_id(config.APP_ID) \
        .app_secret(config.APP_SECRET) \
        .build()

    request = CreateMessageRequest.builder() \
        .receive_id_type(receive_id_type) \
        .request_body(CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("interactive")
            .content(json.dumps({"card": card}, ensure_ascii=False))
            .build()) \
        .build()

    response = client.im.v1.message.create(request)
    if not response.success():
        raise RuntimeError(f"发送卡片消息失败: {response.msg}")


def build_command_menu_card() -> dict:
    """构建命令菜单卡片（类似TG键盘的点选体验）"""
    return {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "template": "blue",
            "title": {
                "tag": "plain_text",
                "content": "🤖 飞书机器人快捷指令菜单"
            }
        },
        "elements": [
            {
                "tag": "markdown",
                "content": "点击下面按钮直接执行命令（常用操作一键触发）"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📊 今日日报汇总"},
                        "type": "primary",
                        "value": {"cmd": "summary_today"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 我的日报"},
                        "type": "default",
                        "value": {"cmd": "my_report_today"}
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🏖️ 查询今日调休"},
                        "type": "default",
                        "value": {"cmd": "query_vacation_today"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📚 命令说明"},
                        "type": "default",
                        "value": {"cmd": "help_text"}
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "➕ 设置调休（表单）"},
                        "type": "primary",
                        "value": {"cmd": "open_set_vacation_form"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "➖ 取消调休（表单）"},
                        "type": "danger",
                        "value": {"cmd": "open_cancel_vacation_form"}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "设置/取消调休请继续使用：/设置调休 姓名 [日期]、/取消调休 姓名 [日期]"
                    }
                ]
            }
        ]
    }


def build_set_vacation_form_card() -> dict:
    """构建设置调休表单卡片"""
    return {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "template": "green",
            "title": {
                "tag": "plain_text",
                "content": "➕ 设置调休"
            }
        },
        "elements": [
            {
                "tag": "input",
                "name": "vacation_name",
                "required": True,
                "placeholder": {
                    "tag": "plain_text",
                    "content": "请输入姓名（如：张三）"
                }
            },
            {
                "tag": "date_picker",
                "name": "vacation_date",
                "placeholder": {
                    "tag": "plain_text",
                    "content": "请选择日期（不选默认今天）"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "提交设置"},
                        "type": "primary",
                        "value": {"cmd": "set_vacation_submit"}
                    }
                ]
            }
        ]
    }


def build_cancel_vacation_form_card() -> dict:
    """构建取消调休表单卡片"""
    return {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "template": "red",
            "title": {
                "tag": "plain_text",
                "content": "➖ 取消调休"
            }
        },
        "elements": [
            {
                "tag": "input",
                "name": "vacation_name",
                "required": True,
                "placeholder": {
                    "tag": "plain_text",
                    "content": "请输入姓名（如：张三）"
                }
            },
            {
                "tag": "date_picker",
                "name": "vacation_date",
                "placeholder": {
                    "tag": "plain_text",
                    "content": "请选择日期（不选默认今天）"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "提交取消"},
                        "type": "danger",
                        "value": {"cmd": "cancel_vacation_submit"}
                    }
                ]
            }
        ]
    }


def handle_card_action(data: P2CardActionTrigger):
    """处理卡片按钮点击回调"""
    try:
        action_value = (data.event.action.value if data and data.event and data.event.action else {}) or {}
        form_value = (data.event.action.form_value if data and data.event and data.event.action else {}) or {}
        cmd = action_value.get('cmd')
        open_chat_id = data.event.context.open_chat_id if data and data.event and data.event.context else None
        operator_user_id = data.event.operator.user_id if data and data.event and data.event.operator else None

        logger.info(f"🎛️ 收到卡片点击回调: cmd={cmd}, user_id={operator_user_id}, form_keys={list(form_value.keys())}")

        if not open_chat_id or not cmd:
            logger.warning("卡片回调缺少 open_chat_id 或 cmd")
            return

        user_name = user_names_map.get(operator_user_id, '未知用户') if operator_user_id else '未知用户'
        context = {
            'user_id': operator_user_id,
            'user_name': user_name,
            'chat_id': open_chat_id,
        }

        response_text = None
        if cmd == 'summary_today':
            response_text = command_handler.handle_command('summary', [], context)
        elif cmd == 'my_report_today':
            response_text = command_handler.handle_command('my_report', [], context)
        elif cmd == 'query_vacation_today':
            response_text = command_handler.handle_command('query_vacation', [], context)
        elif cmd == 'help_text':
            response_text = command_handler.handle_command('help', [], context)
        elif cmd == 'open_set_vacation_form':
            send_interactive_card(open_chat_id, build_set_vacation_form_card(), receive_id_type="open_chat_id")
            return
        elif cmd == 'open_cancel_vacation_form':
            send_interactive_card(open_chat_id, build_cancel_vacation_form_card(), receive_id_type="open_chat_id")
            return
        elif cmd == 'set_vacation_submit':
            name = (form_value.get('vacation_name') or '').strip()
            date = (form_value.get('vacation_date') or '').strip()
            args = [name] + ([date] if date else [])
            response_text = command_handler.handle_command('set_vacation', args, context)
        elif cmd == 'cancel_vacation_submit':
            name = (form_value.get('vacation_name') or '').strip()
            date = (form_value.get('vacation_date') or '').strip()
            args = [name] + ([date] if date else [])
            response_text = command_handler.handle_command('cancel_vacation', args, context)

        if response_text:
            send_text_message(open_chat_id, response_text, receive_id_type="open_chat_id")
    except Exception as e:
        logger.error(f"处理卡片回调失败: {e}", exc_info=True)


def extract_text_from_post(content_json: dict) -> str:
    """
    从 post 类型消息中提取纯文本内容

    Args:
        content_json: post 消息的 content JSON 对象

    Returns:
        str: 提取的纯文本
    """
    try:
        text_parts = []

        # post 消息可能有两种结构：
        # 1. 直接格式: {"title": "", "content": [[...]]}
        # 2. 多语言格式: {"zh_cn": {"title": "", "content": [[...]]}}

        # 先尝试多语言格式
        lang_content = content_json.get('zh_cn') or content_json.get('en_us')

        # 如果没有多语言格式，使用直接格式
        if not lang_content:
            lang_content = content_json

        # 获取标题
        title = lang_content.get('title', '')
        if title and title.strip():
            text_parts.append(title.strip())

        # 获取内容块
        content_blocks = lang_content.get('content', [])

        # 遍历每个段落
        for paragraph in content_blocks:
            # 跳过空段落或None
            if not paragraph:
                # 空段落也要保留（作为段落分隔）
                text_parts.append('')
                continue

            paragraph_text = []

            # 遍历段落中的每个元素
            for element in paragraph:
                if not isinstance(element, dict):
                    continue

                tag = element.get('tag', '')

                if tag == 'text':
                    # 纯文本
                    text = element.get('text', '')
                    if text:
                        paragraph_text.append(text)
                elif tag == 'a':
                    # 链接
                    text = element.get('text', '')
                    if text:
                        paragraph_text.append(text)
                elif tag == 'at':
                    # @某人
                    text = element.get('text', '')
                    if text:
                        paragraph_text.append(text)

            # 合并段落文本
            if paragraph_text:
                combined_text = ''.join(paragraph_text)
                # 只添加非空的段落文本
                if combined_text.strip():
                    text_parts.append(combined_text)

        # 用换行符连接所有部分
        result = '\n'.join(text_parts)
        
        # 清理多余的空行（超过2个连续换行符的情况）
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()

    except Exception as e:
        logger.error(f"提取 post 消息文本失败: {str(e)}", exc_info=True)
        return ""


def handle_message_recalled(data):
    """处理消息撤回事件"""
    global user_timers

    try:
        # 获取撤回的消息ID（注意是单个message_id，不是list）
        message_id = data.event.message_id

        if not message_id:
            logger.warning("收到撤回事件但没有消息ID")
            return

        logger.info(f"📢 收到消息撤回事件 - message_id: {message_id}")

        # 查找是哪个用户撤回的
        sender_name = None
        for name, info in user_timers.items():
            if info.get('message_id') == message_id:
                sender_name = name
                break

        # 从存储中删除对应的日报
        success = report_storage.remove_report_by_message_id(message_id)

        if success:
            logger.info(f"✅ 已删除撤回消息对应的日报 - message_id: {message_id}")

            # 取消该用户的计时器
            if sender_name and sender_name in user_timers:
                timer = user_timers[sender_name].get('timer')
                if timer and timer.is_alive():
                    timer.cancel()
                    logger.info(f"⏱️  已取消 {sender_name} 的容错期计时器")
                del user_timers[sender_name]

            # 检查撤回后的状态
            current_count = report_storage.get_report_count()
            expected_count = config.DAILY_REPORT_EXPECTED_COUNT

            logger.info(f"📝 撤回后人数变为 {current_count}/{expected_count}")
            logger.info(f"💡 用户可以重新发送正确的日报")
        else:
            logger.info(f"ℹ️  撤回的消息不是日报或已被处理 - message_id: {message_id}")

    except Exception as e:
        logger.error(f"处理消息撤回事件失败: {str(e)}", exc_info=True)


def handle_message(data: P2ImMessageReceiveV1):
    """处理接收到的消息事件"""
    try:
        # 获取消息内容
        message = data.event.message
        message_type = message.message_type

        # 获取群聊信息（提前获取，用于过滤）
        chat_id = message.chat_id

        # ====================================
        # 群组过滤：只处理配置的目标群组消息
        # ====================================
        if config.DAILY_REPORT_CHAT_ID and chat_id != config.DAILY_REPORT_CHAT_ID:
            # 非目标群组，直接返回，不打印日志（避免干扰）
            logger.debug(f"忽略非目标群组的消息 - 群组: {chat_id}")
            return

        # 解析消息内容
        content = json.loads(message.content)
        text = ""

        # 处理不同类型的消息
        if message_type == 'text':
            # 纯文本消息
            text = content.get('text', '').strip()
        elif message_type == 'post':
            # 富文本消息 - 先打印原始内容用于调试
            logger.info(f"富文本消息原始内容: {json.dumps(content, ensure_ascii=False)}")
            text = extract_text_from_post(content).strip()
            logger.info(f"处理富文本消息，提取文本长度: {len(text)}")
            if text:
                logger.info(f"提取的文本内容:\n{text}")
        else:
            logger.info(f"忽略不支持的消息类型: {message_type}")
            return

        if not text:
            return

        # 0.1 优先处理斜杠命令
        if config.COMMAND_ENABLED and command_router.is_command(text):
            logger.info(f"💬 检测到命令: {text}")
            cmd_info = command_router.parse_command(text)
            if not cmd_info:
                logger.warning(f"命令解析失败: {text}")
                return

            # /帮助 使用交互式卡片菜单（类似TG键盘点选）
            if cmd_info['command'] == 'help':
                try:
                    send_interactive_card(chat_id, build_command_menu_card())
                except Exception as send_err:
                    logger.error(f"发送命令菜单卡片失败: {send_err}", exc_info=True)
                    # 兜底：发送纯文本帮助
                    fallback_text = command_handler.handle_command('help', [], {})
                    send_text_message(chat_id, fallback_text)
                return

            # 获取发送者信息用于命令上下文
            sender = data.event.sender
            sender_user_id = sender.sender_id.user_id if (sender.sender_id and sender.sender_id.user_id) else None
            sender_name = get_user_name(sender, chat_id)

            context = {
                'user_id': sender_user_id,
                'user_name': sender_name,
                'chat_id': chat_id,
            }
            response_text = command_handler.handle_command(
                cmd_info['command'],
                cmd_info['args'],
                context,
            )

            if response_text:
                try:
                    send_text_message(chat_id, response_text)
                except Exception as send_err:
                    logger.error(f"发送命令响应失败: {send_err}", exc_info=True)
            return

        # 获取发送者信息
        sender = data.event.sender
        sender_id = sender.sender_id.open_id if (sender.sender_id and sender.sender_id.open_id) else 'unknown'
        sender_user_id = sender.sender_id.user_id if (sender.sender_id and sender.sender_id.user_id) else None

        # 获取发送者真实姓名（需要 chat_id 参数）
        sender_name = get_user_name(sender, chat_id)

        # 获取消息时间
        create_time = message.create_time
        msg_time = datetime.fromtimestamp(int(create_time) / 1000).strftime('%Y-%m-%d %H:%M:%S') if create_time else 'unknown'

        logger.info(f"处理消息 - 发送者: {sender_name} ({sender_user_id}), 群组: {chat_id}, 内容: {text}")

        # 0. 检查是否为休假命令 (格式: @某人#休假 或 某人#休假)
        if "#休假" in text:
            logger.info("🏖️  检测到休假命令...")
            # 支持两种格式：
            # 1. @某人#休假 -> 从text中提取 @_user_X#休假，然后从 sender_name 或配置中查找真实姓名
            # 2. 某人#休假 -> 直接从文本提取姓名
            
            import re
            # 尝试匹配 "姓名#休假" 格式
            vacation_match = re.search(r'([^@\s]+)#休假', text)
            if vacation_match:
                name_part = vacation_match.group(1)
                
                # 如果是 _user_X 格式，说明是 @mention，需要从 user_names_map 反查
                if name_part.startswith('_user_'):
                    # 从富文本中获取被@的用户ID
                    # 由于无法直接获取，我们需要从配置的必填用户列表中匹配
                    logger.info(f"检测到 @mention 休假命令，文本: {text}")
                    # 暂时跳过，提示用户使用姓名格式
                    logger.warning("⚠️  暂不支持 @mention 格式设置休假，请使用 '姓名#休假' 格式")
                    logger.warning("   例如: 李尚璋#休假")
                    return
                else:
                    # 直接使用提取的姓名
                    vacation_user = name_part.strip()
                    
                    # 设置休假
                    success = vacation_manager.set_vacation(vacation_user)
                    if success:
                        logger.info(f"✅ 已设置 {vacation_user} 休假")
                        
                        # 自动为该用户生成休假日报
                        today = datetime.now().strftime('%Y-%m-%d')
                        vacation_report = {
                            'sender': vacation_user,
                            'tracking_issues': '-',
                            'work_content': '休假',
                            'blocks': '-',
                            'next_plan': '-',
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'date': today,
                            'message_id': f"vacation_{vacation_user}_{today}"
                        }
                        
                        # 检查是否已有日报（通过查找发送者）
                        existing_reports = report_storage.get_all_reports(today)
                        has_report = any(r.get('sender') == vacation_user for r in existing_reports)
                        
                        if not has_report:
                            report_storage.add_report(vacation_report)
                            current_count = report_storage.get_report_count()
                            logger.info(f"📝 已自动添加休假日报 - {vacation_user}，当前共 {current_count} 份日报")
                        else:
                            logger.info(f"💡 {vacation_user} 今天已有日报记录，跳过添加休假日报")
                    return
            else:
                logger.warning("⚠️  无法解析休假命令格式，请使用: 姓名#休假")
                return

        # 1. 检查是否为获取成员列表命令
        get_members_keywords = ["获取成员列表", "成员列表", "群成员", "获取群成员"]
        if any(keyword in text for keyword in get_members_keywords):
            logger.info("📋 检测到获取成员列表命令...")
            get_chat_members(chat_id)
            return

        # 1.5 检查是否为测试提醒命令
        test_reminder_keywords = ["测试提醒", "测试日报提醒", "提醒测试"]
        if any(keyword in text for keyword in test_reminder_keywords):
            logger.info("🧪 检测到测试提醒命令...")
            check_and_send_reminder()
            return

        # 2. 检查是否为手动触发汇总命令
        if config.DAILY_REPORT_ENABLED and config.DAILY_REPORT_SEND_MODE == 'manual':
            # 检测汇总命令：支持 "汇总日报"、"发送日报"、"日报汇总" 等
            trigger_keywords = ["汇总日报", "发送日报", "日报汇总", "汇总", "发送汇总", "邮件汇总"]
            if any(keyword in text for keyword in trigger_keywords):
                logger.info("🎯 检测到汇总命令，开始执行汇总...")
                
                # 解析日期参数
                target_date = parse_date_from_command(text)
                logger.info(f"📅 汇总目标日期: {target_date}")
                
                # 检查该日期是否已发送
                if report_storage.is_sent(target_date):
                    report_count = report_storage.get_report_count(target_date)
                    logger.info(f"ℹ️  {target_date} 的日报汇总已发送（共{report_count}份），忽略本次手动汇总命令")
                    return

                send_daily_report_summary(target_date)
                return  # 处理完汇总命令后直接返回

        # 2. 检查是否为日报并存储
        if config.DAILY_REPORT_ENABLED:
            # 现在已经通过群组过滤，所有到达这里的消息都是目标群组的
            if report_parser.is_daily_report(text):
                # 解析日报（使用真实姓名）
                report_data = report_parser.parse(text, sender_name)
                if report_data:
                    # 添加 message_id 用于撤回时定位
                    report_data['message_id'] = message.message_id

                    # 存储日报
                    report_storage.add_report(report_data)
                    current_count = report_storage.get_report_count()
                    logger.info(f"✅ 日报已收集 - 发送者: {sender_name}, message_id: {message.message_id}, 当前共 {current_count} 份日报")

                    # 实时模式：立即发送日报
                    if config.DAILY_REPORT_SEND_MODE == 'realtime':
                        logger.info("🚀 实时发送模式 - 立即发送日报")
                        send_single_report(report_data)
                    
                    # 启动延迟发送机制（给每个用户独立的10分钟容错期）
                    elif config.DAILY_REPORT_AUTO_SEND_ON_COMPLETE:
                        expected_count = config.DAILY_REPORT_EXPECTED_COUNT
                        
                        # 检查今天的日报是否已经发送过
                        if report_storage.is_sent():
                            logger.info(f"ℹ️  今日日报汇总已发送，不再自动发送（当前 {current_count} 份）")
                        else:
                            # 为该用户启动独立的10分钟容错期
                            logger.info(f"📝 进度：{current_count}/{expected_count} 份日报")
                            schedule_user_timer(sender_name, message.message_id)
                            
                            if current_count >= expected_count:
                                logger.info(f"✅ 已达到预期人数，等待所有用户容错期结束后自动发送")

        # 2. 检查关键字匹配
        matched_keywords = keyword_matcher.match(text)

        if matched_keywords:
            logger.info(f"匹配到关键字: {matched_keywords}")

            # 发送邮件
            for keyword_info in matched_keywords:
                keyword = keyword_info['keyword']
                recipients = keyword_info['recipients']

                email_subject = f"[飞书消息提醒] 检测到关键字: {keyword}"
                email_body = f"""
<html>
<body>
    <h2>飞书消息提醒</h2>
    <p><strong>触发关键字:</strong> {keyword}</p>
    <p><strong>发送者:</strong> {sender_user_id} ({sender_id})</p>
    <p><strong>群组ID:</strong> {chat_id}</p>
    <p><strong>时间:</strong> {msg_time}</p>
    <hr>
    <h3>消息内容:</h3>
    <p>{text}</p>
</body>
</html>
"""

                # 发送邮件
                success = email_sender.send_email(
                    recipients=recipients,
                    subject=email_subject,
                    body=email_body
                )

                if success:
                    logger.info(f"邮件发送成功 - 关键字: {keyword}, 收件人: {recipients}")
                else:
                    logger.error(f"邮件发送失败 - 关键字: {keyword}, 收件人: {recipients}")

    except Exception as e:
        logger.error(f"处理消息失败: {str(e)}", exc_info=True)


def get_chat_members(chat_id: str, force_update: bool = False):
    """
    获取群聊成员列表并生成姓名映射配置

    Args:
        chat_id: 群组ID
        force_update: 是否强制更新已有的用户名映射（默认False保留手动配置的名称）
    """
    global user_names_map  # 需要更新全局变量

    try:
        from lark_oapi.api.im.v1 import GetChatMembersRequest

        logger.info(f"正在获取群组 {chat_id} 的成员列表...")

        # 创建客户端
        client = lark.Client.builder() \
            .app_id(config.APP_ID) \
            .app_secret(config.APP_SECRET) \
            .build()

        # 构建请求
        request = GetChatMembersRequest.builder() \
            .chat_id(chat_id) \
            .member_id_type("user_id") \
            .page_size(100) \
            .build()

        # 发起请求
        response = client.im.v1.chat_members.get(request)

        if not response.success():
            logger.error(f"获取群成员列表失败: {response.msg}")
            return

        members = response.data.items
        if not members:
            logger.warning("未获取到群成员")
            return

        logger.info(f"获取到 {len(members)} 个群成员")

        # 生成姓名映射配置
        user_mapping = {}
        for member in members:
            user_id = member.member_id
            name = member.name if hasattr(member, 'name') and member.name else f"用户_{user_id[-6:]}"
            user_mapping[user_id] = name
            logger.info(f"  - {user_id}: {name}")

        # 保存到配置文件
        user_names_file = 'config/user_names.json'

        # 读取现有配置
        existing_data = {
            "说明": "配置飞书用户ID到真实姓名的映射，格式：user_id: 姓名",
            "映射": {}
        }

        if os.path.exists(user_names_file):
            try:
                with open(user_names_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                pass

        # 合并配置
        existing_mapping = existing_data.get('映射', {})

        if force_update:
            # 强制更新模式：覆盖所有值
            existing_mapping.update(user_mapping)
            logger.info(f"💡 强制更新模式：已更新所有用户姓名")
        else:
            # 保护模式：只添加新用户，保留已有配置
            for user_id, name in user_mapping.items():
                if user_id not in existing_mapping:
                    existing_mapping[user_id] = name

        existing_data['映射'] = existing_mapping

        # 同时更新全局内存映射
        user_names_map.clear()
        user_names_map.update(existing_mapping)

        # 保存配置到文件
        with open(user_names_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        logger.info("=" * 60)
        logger.info(f"✅ 群成员信息已保存到 {user_names_file}")
        logger.info(f"共 {len(existing_mapping)} 个用户")
        if not force_update:
            logger.info("💡 提示：请编辑该文件，将自动生成的姓名替换为真实姓名")
            logger.info("修改后需要重启服务才能生效")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"获取群成员列表异常: {str(e)}", exc_info=True)


def send_single_report(report_data: dict):
    """实时发送单个日报邮件"""
    try:
        # 生成HTML表格（只包含这一份日报）
        current_date = datetime.now().strftime('%Y/%m/%d')  # 修改日期格式为 YYYY/MM/DD
        html_content = table_generator.generate_html_table([report_data], current_date)

        # 发送邮件
        recipients = config.DAILY_REPORT_RECIPIENTS
        if not recipients:
            logger.warning("未配置日报收件人，跳过发送")
            return

        sender_name = report_data.get('sender', '未知')
        # 修改邮件标题格式
        subject = f"［Realtek]［资源共享］Realtek-TS-Task开发日报 {current_date} - {sender_name}"

        success = email_sender.send_email(
            recipients=recipients,
            subject=subject,
            body=html_content,
            cc=config.DAILY_REPORT_CC if config.DAILY_REPORT_CC else None,
            bcc=config.DAILY_REPORT_BCC if config.DAILY_REPORT_BCC else None
        )

        if success:
            logger.info(f"✅ 日报邮件发送成功 - 发送者: {sender_name}, 收件人: {recipients}")
        else:
            logger.error(f"❌ 日报邮件发送失败 - 发送者: {sender_name}")

    except Exception as e:
        logger.error(f"发送单个日报失败: {str(e)}", exc_info=True)


def send_daily_report_summary(target_date: str = None):
    """定时汇总并发送日报邮件
    
    Args:
        target_date: 目标日期 (YYYY-MM-DD)，默认为今天
    """
    try:
        logger.info("=" * 60)
        logger.info("📊 开始执行日报汇总任务...")

        # 确定目标日期
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        # 获取指定日期的日报
        reports = report_storage.get_all_reports(target_date)
        report_count = len(reports)

        logger.info(f"当前收集到 {report_count} 份日报（日期: {target_date}）")

        # 生成HTML表格（使用新的日期格式）
        display_date = datetime.strptime(target_date, '%Y-%m-%d').strftime('%Y/%m/%d')
        html_content = table_generator.generate_html_table(reports, display_date)

        # 发送邮件
        recipients = config.DAILY_REPORT_RECIPIENTS
        if not recipients:
            logger.warning("未配置日报收件人，跳过发送")
            return

        # 修改邮件标题格式
        subject = f"［Realtek]［资源共享］Realtek-TS-Task开发日报 {display_date} - 共 {report_count} 份"

        success = email_sender.send_email(
            recipients=recipients,
            subject=subject,
            body=html_content,
            cc=config.DAILY_REPORT_CC if config.DAILY_REPORT_CC else None,
            bcc=config.DAILY_REPORT_BCC if config.DAILY_REPORT_BCC else None
        )

        if success:
            logger.info(f"✅ 日报汇总邮件发送成功 - 收件人: {recipients}")
            # 标记为已发送，避免自动/手动重复发送
            report_storage.mark_as_sent(target_date)
            # 清空已发送的日报
            # report_storage.clear_reports()  # 可选：如果希望发送后清空
        else:
            logger.error(f"❌ 日报汇总邮件发送失败")

        logger.info("日报汇总任务完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"日报汇总任务失败: {str(e)}", exc_info=True)


def check_and_send_if_all_ready():
    """检查是否所有用户都已稳定（10分钟无变动），如果是则发送"""
    global user_timers
    
    try:
        logger.info("⏰ 检查是否可以发送日报汇总...")
        
        # 检查今天的日报是否已经发送过
        if report_storage.is_sent():
            logger.info("ℹ️  今日日报汇总已发送，跳过")
            return
        
        # 获取当前日报数量
        current_count = report_storage.get_report_count()
        expected_count = config.DAILY_REPORT_EXPECTED_COUNT
        
        # 检查是否达到预期人数
        if current_count < expected_count:
            logger.info(f"📝 当前 {current_count}/{expected_count} 份日报，未达到预期人数，不发送")
            return
        
        # 检查是否所有用户都已超过10分钟容错期
        # 注意：Timer 的回调执行期间 is_alive() 仍可能为 True（会导致误判“还有1人容错期内”）。
        now = datetime.now()
        grace_seconds = 600

        # 清理已过期的容错期记录，避免影响统计
        expired_names = []
        for name, info in user_timers.items():
            submit_time = info.get('submit_time')
            if isinstance(submit_time, datetime):
                if (now - submit_time).total_seconds() >= grace_seconds:
                    expired_names.append(name)

        for name in expired_names:
            # 不依赖 cancel：到期后可能正在执行回调
            user_timers.pop(name, None)

        # 仍在容错期内的用户数（基于 submit_time 判定）
        active_timers = 0
        active_users = []
        for name, info in user_timers.items():
            submit_time = info.get('submit_time')
            if isinstance(submit_time, datetime):
                elapsed = (now - submit_time).total_seconds()
                if elapsed < grace_seconds:
                    active_timers += 1
                    remaining = grace_seconds - elapsed
                    active_users.append(f"{name}(剩余{remaining:.0f}秒)")
        
        if active_timers > 0:
            logger.info(f"⏱️  还有 {active_timers} 个用户在容错期内: {', '.join(active_users)}，暂不发送")
            return
        
        # 所有条件满足，发送邮件
        logger.info(f"🎉 所有 {current_count} 位用户已稳定，发送日报汇总邮件")
        send_daily_report_summary()
        
        # 清空用户计时器
        user_timers.clear()
        
    except Exception as e:
        logger.error(f"检查发送失败: {str(e)}", exc_info=True)


def schedule_user_timer(sender_name: str, message_id: str):
    """为特定用户安排10分钟容错期计时器"""
    global user_timers
    
    try:
        # 如果该用户已有计时器，先取消
        if sender_name in user_timers:
            old_timer = user_timers[sender_name].get('timer')
            if old_timer and old_timer.is_alive():
                old_timer.cancel()
                logger.info(f"⏱️  取消 {sender_name} 之前的容错期计时器")
        
        submit_time = datetime.now()

        # 创建新的10分钟延迟任务（用户特定）
        def user_timer_callback():
            logger.info(f"⏰ {sender_name} 的10分钟容错期结束")
            # 关键修复：回调触发时先移除本人的容错记录。
            # 否则在极端情况下（回调略早于600秒），check 会认为“还有1人容错期内”而直接 return，
            # 且之后没有新的回调触发检查，导致永远不自动发送。
            user_timers.pop(sender_name, None)

            logger.info(f"📋 当前容错期状态: {len(user_timers)} 个用户在容错队列中")
            for uname, uinfo in user_timers.items():
                usubmit = uinfo.get('submit_time')
                if isinstance(usubmit, datetime):
                    uelapsed = (datetime.now() - usubmit).total_seconds()
                    logger.info(f"   - {uname}: 已提交 {uelapsed:.0f} 秒")
            # 检查是否可以发送
            check_and_send_if_all_ready()
        
        timer = Timer(600.0, user_timer_callback)  # 600秒 = 10分钟
        timer.daemon = True
        timer.start()
        
        # 记录用户计时器信息
        user_timers[sender_name] = {
            'timer': timer,
            'message_id': message_id,
            'submit_time': submit_time
        }
        
        send_time = (submit_time + timedelta(minutes=10)).strftime('%H:%M:%S')
        logger.info(f"⏱️  已为 {sender_name} 启动10分钟容错期，将在 {send_time} 结束")
        
    except Exception as e:
        logger.error(f"安排用户计时器失败: {str(e)}", exc_info=True)


def check_and_send_reminder():
    """检查并发送日报提醒（@未提交日报的人）"""
    try:
        if not config.DAILY_REPORT_CHAT_ID:
            logger.warning("未配置 DAILY_REPORT_CHAT_ID，无法发送提醒")
            return

        # 获取当前已收集的日报
        reports = report_storage.get_all_reports()

        # 检查并发送提醒
        reminder_sender.check_and_remind(
            chat_id=config.DAILY_REPORT_CHAT_ID,
            reports=reports,
            user_names_file='config/user_names.json'
        )

    except Exception as e:
        logger.error(f"日报提醒任务失败: {str(e)}", exc_info=True)


# ============================================================
# 注意：已移除基于"无消息超时"的健康监控
# ============================================================
# 原因：群里没人说话是正常情况，不应该触发重启
# WebSocket SDK已经内置了 auto_reconnect=True 功能，会自动处理连接断开
# 如果确实需要监控，应该使用SDK的连接状态回调或心跳机制

def monitor_websocket_health():
    """[已禁用] 旧的健康监控逻辑有缺陷"""
    # 这个函数已经不再使用
    # 原逻辑问题：5分钟没消息就认为连接断开是错误的判断
    # 正确做法：依赖SDK的auto_reconnect功能
    pass


def signal_handler(signum, frame):
    """处理退出信号"""
    logger.info("\n收到退出信号，正在关闭...")
    shutdown_event.set()
    
    # 关闭定时任务调度器
    if config.DAILY_REPORT_ENABLED and scheduler.running:
        scheduler.shutdown()
        logger.info("定时任务调度器已关闭")
    
    logger.info("服务已停止")
    sys.exit(0)



if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("启动飞书机器人邮件转发服务（长连接模式）...")
    logger.info("使用飞书官方 lark-oapi SDK - WebSocket 长连接")
    logger.info(f"已加载 {len(config.KEYWORDS)} 个关键字规则")

    # 启动日报功能
    if config.DAILY_REPORT_ENABLED:
        logger.info(f"📊 日报功能已启用")

        # 初始化群成员列表（如果配置了 CHAT_ID）
        if config.DAILY_REPORT_CHAT_ID:
            logger.info(f"   - 日报群组: {config.DAILY_REPORT_CHAT_ID}")
            logger.info(f"   - 正在初始化群成员列表...")
            try:
                # 启动时不强制更新，保护手动配置的用户姓名映射
                get_chat_members(config.DAILY_REPORT_CHAT_ID, force_update=False)
                logger.info(f"   ✅ 成功初始化 {len(user_names_map)} 个用户姓名映射")
            except Exception as e:
                logger.error(f"   ❌ 初始化群成员列表失败: {str(e)}")
        else:
            logger.warning(f"   ⚠️  未配置 DAILY_REPORT_CHAT_ID，将在首次收到消息时获取成员信息")

        if config.DAILY_REPORT_SEND_MODE == 'realtime':
            logger.info(f"   - 发送模式: 🚀 实时发送（收到日报后立即发送邮件）")
            logger.info(f"   - 收件人: {', '.join(config.DAILY_REPORT_RECIPIENTS)}")
            logger.info(f"   ⚠️  测试模式：每收到一份日报就会立即发送邮件")
        elif config.DAILY_REPORT_SEND_MODE == 'manual':
            logger.info(f"   - 发送模式: 🎯 手动触发（收集日报，发送命令后统一汇总）")
            logger.info(f"   - 收件人: {', '.join(config.DAILY_REPORT_RECIPIENTS)}")
            logger.info(f"   ⚠️  测试模式：收集日报后，发送以下命令触发汇总：")
            logger.info(f"      '汇总日报' 或 '发送日报' 或 '日报汇总'")
        else:
            logger.info(f"   - 发送模式: ⏰ 定时汇总（每天固定时间汇总发送）")
            logger.info(f"   - 汇总时间: 每天 {config.DAILY_REPORT_SCHEDULE_TIME}")
            logger.info(f"   - 收件人: {', '.join(config.DAILY_REPORT_RECIPIENTS)}")

            # 解析汇总时间（格式：HH:MM）
            try:
                hour, minute = map(int, config.DAILY_REPORT_SCHEDULE_TIME.split(':'))

                # 添加定时任务
                scheduler.add_job(
                    send_daily_report_summary,
                    'cron',
                    hour=hour,
                    minute=minute,
                    id='daily_report_summary'
                )

                # 启动调度器
                scheduler.start()
                logger.info(f"   - 定时任务已启动")

            except Exception as e:
                logger.error(f"启动日报定时任务失败: {str(e)}")

        # 启动日报提醒功能
        if config.DAILY_REPORT_REMINDER_ENABLED and config.DAILY_REPORT_CHAT_ID:
            logger.info(f"🔔 日报提醒功能已启用")
            logger.info(f"   - 提醒时间: 每天 {config.DAILY_REPORT_REMINDER_TIME}")
            logger.info(f"   - 提醒方式: 在群组中@未提交日报的人")

            # 解析提醒时间（格式：HH:MM）
            try:
                reminder_hour, reminder_minute = map(int, config.DAILY_REPORT_REMINDER_TIME.split(':'))

                # 添加提醒定时任务
                if not scheduler.running:
                    scheduler.start()

                scheduler.add_job(
                    check_and_send_reminder,
                    'cron',
                    hour=reminder_hour,
                    minute=reminder_minute,
                    id='daily_report_reminder'
                )

                logger.info(f"   - 提醒定时任务已启动")

            except Exception as e:
                logger.error(f"启动日报提醒定时任务失败: {str(e)}")

    logger.info("=" * 60)

    # 创建事件处理器
    event_handler = lark.EventDispatcherHandler.builder(
        config.ENCRYPT_KEY if config.ENCRYPT_KEY else "",
        config.VERIFICATION_TOKEN,
        lark.LogLevel.ERROR  # 修改为ERROR级别，减少SDK的日志干扰
    ).register_p2_im_message_receive_v1(handle_message) \
     .register_p2_card_action_trigger(handle_card_action) \
     .register_p2_im_message_recalled_v1(handle_message_recalled) \
     .build()

    logger.info("✅ 已注册事件处理器：")
    logger.info("   - im.message.receive_v1 (消息接收)")
    logger.info("   - card.action.trigger (卡片按钮点击)")
    logger.info("   - im.message.recalled_v1 (消息撤回)")

    # 群组过滤提醒
    if config.DAILY_REPORT_CHAT_ID:
        logger.info(f"🔒 群组过滤已启用 - 只处理群组: {config.DAILY_REPORT_CHAT_ID}")
        logger.info(f"   其他群组的消息将被自动忽略")
    else:
        logger.warning("⚠️  未配置 DAILY_REPORT_CHAT_ID，将处理所有群组消息")

    # 创建 WebSocket 客户端
    ws_client = WSClient(
        app_id=config.APP_ID,
        app_secret=config.APP_SECRET,
        log_level=lark.LogLevel.ERROR,  # 修改为ERROR级别，减少日志干扰
        event_handler=event_handler,
        auto_reconnect=True  # 自动重连
    )

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 重连计数器
    reconnect_count = 0
    max_reconnect_attempts = 5  # 增加到5次

    try:
        logger.info("=" * 60)
        logger.info("🔌 正在连接飞书服务器...")
        logger.info("   - 使用WebSocket长连接")
        logger.info("   - SDK自动重连已启用")
        logger.info("   - 连接异常时会自动尝试重连")
        logger.info("=" * 60)

        # 启动长连接（会阻塞）
        ws_client.start()

    except KeyboardInterrupt:
        logger.info("\n收到退出信号，正在关闭...")
        shutdown_event.set()
    except Exception as e:
        reconnect_count += 1
        logger.error(f"❌ 长连接异常 (第{reconnect_count}次): {str(e)}", exc_info=True)

        if reconnect_count >= max_reconnect_attempts:
            logger.error("=" * 60)
            logger.error("⚠️  连接失败次数过多，请检查：")
            logger.error("   1. 网络连接是否正常")
            logger.error("   2. FEISHU_APP_ID 和 FEISHU_APP_SECRET 是否正确")
            logger.error("   3. 是否有防火墙或代理阻止WebSocket连接")
            logger.error("   4. 尝试切换网络环境（如关闭VPN）")
            logger.error("=" * 60)
            shutdown_event.set()
    finally:
        # 设置退出标志
        shutdown_event.set()
        
        # 关闭定时任务调度器
        if config.DAILY_REPORT_ENABLED and scheduler.running:
            scheduler.shutdown()
            logger.info("定时任务调度器已关闭")
        logger.info("服务已停止")
