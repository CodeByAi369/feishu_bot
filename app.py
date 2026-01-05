#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人消息监听与邮件转发服务
使用飞书官方 lark-oapi SDK
"""

import json
import logging
import os
from datetime import datetime
from flask import Flask
import lark_oapi as lark
from lark_oapi.adapter.flask import *
from lark_oapi.api.im.v1 import *
from config.config import Config
from utils.keyword_matcher import KeywordMatcher
from utils.email_sender import EmailSender

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

# 初始化飞书客户端
client = lark.Client.builder() \
    .app_id(config.APP_ID) \
    .app_secret(config.APP_SECRET) \
    .log_level(lark.LogLevel.INFO) \
    .build()

# Flask应用
app = Flask(__name__)


def handle_message(data: P2ImMessageReceiveV1):
    """处理接收到的消息事件"""
    try:
        # 获取消息内容
        message = data.event.message
        message_type = message.message_type

        # 只处理文本消息
        if message_type != 'text':
            logger.info(f"忽略非文本消息: {message_type}")
            return

        # 解析消息文本内容
        content = json.loads(message.content)
        text = content.get('text', '').strip()

        if not text:
            return

        # 获取发送者信息
        sender = data.event.sender
        sender_id = sender.sender_id.open_id if sender.sender_id else 'unknown'
        sender_user_id = sender.sender_id.user_id if sender.sender_id else 'unknown'

        # 获取消息时间
        create_time = message.create_time
        msg_time = datetime.fromtimestamp(int(create_time) / 1000).strftime('%Y-%m-%d %H:%M:%S') if create_time else 'unknown'

        # 获取群聊信息
        chat_id = message.chat_id

        logger.info(f"处理消息 - 发送者: {sender_user_id} ({sender_id}), 群组: {chat_id}, 内容: {text}")

        # 检查关键字匹配
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


# 创建事件处理器
event_handler = lark.EventDispatcherHandler.builder(
    config.ENCRYPT_KEY if config.ENCRYPT_KEY else "",
    config.VERIFICATION_TOKEN,
    lark.LogLevel.INFO
).register_p2_im_message_receive_v1(handle_message).build()


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收飞书事件回调"""
    try:
        # 使用官方 SDK 的事件处理器
        # SDK 会自动处理 URL 验证、签名验证等
        oapi_request = parse_req()
        oapi_resp = event_handler.do(oapi_request)

        logger.info("收到并处理飞书事件回调")

        return parse_resp(oapi_resp)

    except Exception as e:
        logger.error(f"处理webhook请求失败: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查接口"""
    return {
        "status": "ok",
        "service": "feishu-bot-mailer",
        "sdk": "lark-oapi",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == '__main__':
    logger.info("启动飞书机器人邮件转发服务...")
    logger.info("使用飞书官方 lark-oapi SDK")
    logger.info(f"监听端口: {config.PORT}")
    logger.info(f"已加载 {len(config.KEYWORDS)} 个关键字规则")

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
