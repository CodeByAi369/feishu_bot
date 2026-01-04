#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送器
支持SMTP协议发送HTML邮件
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""

    def __init__(self, config):
        """
        初始化邮件发送器
        :param config: 配置对象
        """
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.smtp_user = config.SMTP_USER
        self.smtp_password = config.SMTP_PASSWORD
        self.from_email = config.FROM_EMAIL
        self.from_name = config.FROM_NAME
        self.use_tls = config.USE_TLS

        logger.info(f"邮件发送器初始化完成 - SMTP服务器: {self.smtp_server}:{self.smtp_port}")

    def send_email(self, recipients, subject, body, is_html=True, cc=None, bcc=None):
        """
        发送邮件
        :param recipients: 收件人列表
        :param subject: 邮件主题
        :param body: 邮件正文
        :param is_html: 是否为HTML格式
        :param cc: 抄送列表（可选）
        :param bcc: 密送列表（可选）
        :return: 是否发送成功
        """
        try:
            # 确保参数是列表
            if isinstance(recipients, str):
                recipients = [recipients]
            if cc and isinstance(cc, str):
                cc = [cc]
            if bcc and isinstance(bcc, str):
                bcc = [bcc]

            # 创建邮件对象
            message = MIMEMultipart()
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = ', '.join(recipients)
            message['Subject'] = Header(subject, 'utf-8')

            # 添加抄送
            if cc:
                message['Cc'] = ', '.join(cc)

            # 注意：密送不添加到邮件头，只在 sendmail 时添加到收件人列表

            # 添加邮件正文
            if is_html:
                message.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                message.attach(MIMEText(body, 'plain', 'utf-8'))

            # 连接SMTP服务器
            if self.use_tls:
                # 使用TLS加密
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                # 使用SSL加密（通常是465端口）
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

            # 登录
            server.login(self.smtp_user, self.smtp_password)

            # 合并所有收件人（收件人 + 抄送 + 密送）
            all_recipients = recipients.copy()
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)

            # 发送邮件
            server.sendmail(self.from_email, all_recipients, message.as_string())

            # 断开连接
            server.quit()

            log_msg = f"邮件发送成功 - 收件人: {recipients}"
            if cc:
                log_msg += f", 抄送: {cc}"
            if bcc:
                log_msg += f", 密送: {len(bcc)}人"
            log_msg += f", 主题: {subject}"
            logger.info(log_msg)
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}", exc_info=True)
            return False

    def test_connection(self):
        """
        测试SMTP连接
        :return: 是否连接成功
        """
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)

            server.login(self.smtp_user, self.smtp_password)
            server.quit()

            logger.info("SMTP连接测试成功")
            return True

        except Exception as e:
            logger.error(f"SMTP连接测试失败: {str(e)}")
            return False
