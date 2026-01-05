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
from datetime import datetime, timedelta
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.ws import Client as WSClient
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Timer
from config.config import Config
from utils.keyword_matcher import KeywordMatcher
from utils.email_sender import EmailSender
from utils.daily_report_parser import DailyReportParser
from utils.daily_report_storage import DailyReportStorage
from utils.report_table_generator import ReportTableGenerator
from utils.reminder_sender import ReminderSender

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

# 初始化配置和工具类
config = Config()
keyword_matcher = KeywordMatcher(config)
email_sender = EmailSender(config)

# 初始化日报相关工具类
report_parser = DailyReportParser()
report_storage = DailyReportStorage(config.DAILY_REPORT_STORAGE_FILE)
table_generator = ReportTableGenerator()
reminder_sender = ReminderSender(config.APP_ID, config.APP_SECRET, config.DAILY_REPORT_REQUIRED_USERS)

# 初始化定时任务调度器
scheduler = BackgroundScheduler()

# 用户级别的容错期管理
# 结构：{sender_name: {'timer': Timer对象, 'message_id': str, 'submit_time': datetime}}
user_timers = {}

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
            trigger_keywords = ["汇总日报", "发送日报", "日报汇总", "汇总", "发送汇总"]
            if any(keyword in text for keyword in trigger_keywords):
                logger.info("🎯 检测到汇总命令，开始执行汇总...")
                send_daily_report_summary()
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


def send_daily_report_summary():
    """定时汇总并发送日报邮件"""
    try:
        logger.info("=" * 60)
        logger.info("📊 开始执行日报汇总任务...")

        # 获取所有日报
        reports = report_storage.get_all_reports()
        report_count = len(reports)

        logger.info(f"当前收集到 {report_count} 份日报")

        # 生成HTML表格（使用新的日期格式）
        current_date = datetime.now().strftime('%Y/%m/%d')  # 修改日期格式为 YYYY/MM/DD
        html_content = table_generator.generate_html_table(reports, current_date)

        # 发送邮件
        recipients = config.DAILY_REPORT_RECIPIENTS
        if not recipients:
            logger.warning("未配置日报收件人，跳过发送")
            return

        # 修改邮件标题格式
        subject = f"［Realtek]［资源共享］Realtek-TS-Task开发日报 {current_date} - 共 {report_count} 份"

        success = email_sender.send_email(
            recipients=recipients,
            subject=subject,
            body=html_content,
            cc=config.DAILY_REPORT_CC if config.DAILY_REPORT_CC else None,
            bcc=config.DAILY_REPORT_BCC if config.DAILY_REPORT_BCC else None
        )

        if success:
            logger.info(f"✅ 日报汇总邮件发送成功 - 收件人: {recipients}")
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
        
        # 检查是否所有用户的计时器都已结束（即所有人都已稳定）
        active_timers = sum(1 for info in user_timers.values() if info.get('timer') and info['timer'].is_alive())
        
        if active_timers > 0:
            logger.info(f"⏱️  还有 {active_timers} 个用户在容错期内，暂不发送")
            return
        
        # 所有条件满足，发送邮件
        logger.info(f"🎉 所有 {current_count} 位用户已稳定，发送日报汇总邮件")
        send_daily_report_summary()
        
        # 标记为已发送
        report_storage.mark_as_sent()
        
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
        
        # 创建新的10分钟延迟任务（用户特定）
        def user_timer_callback():
            logger.info(f"⏰ {sender_name} 的10分钟容错期结束")
            # 检查是否可以发送
            check_and_send_if_all_ready()
        
        timer = Timer(600.0, user_timer_callback)  # 600秒 = 10分钟
        timer.daemon = True
        timer.start()
        
        # 记录用户计时器信息
        user_timers[sender_name] = {
            'timer': timer,
            'message_id': message_id,
            'submit_time': datetime.now()
        }
        
        send_time = (datetime.now() + timedelta(minutes=10)).strftime('%H:%M:%S')
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
     .register_p2_im_message_recalled_v1(handle_message_recalled) \
     .build()

    logger.info("✅ 已注册事件处理器：")
    logger.info("   - im.message.receive_v1 (消息接收)")
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

    # 重连计数器
    reconnect_count = 0
    max_reconnect_attempts = 3  # 最多连续重连3次后提示

    try:
        logger.info("=" * 60)
        logger.info("🔌 正在连接飞书服务器...")
        logger.info("   - 使用WebSocket长连接")
        logger.info("   - 自动重连已启用")
        logger.info("=" * 60)

        # 启动长连接（会阻塞）
        ws_client.start()

    except KeyboardInterrupt:
        logger.info("\n收到退出信号，正在关闭...")
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
    finally:
        # 关闭定时任务调度器
        if config.DAILY_REPORT_ENABLED and scheduler.running:
            scheduler.shutdown()
            logger.info("定时任务调度器已关闭")
        logger.info("服务已停止")
