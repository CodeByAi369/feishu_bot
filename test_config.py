#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置测试脚本
用于测试SMTP连接和配置是否正确
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from config.config import Config
from utils.email_sender import EmailSender


def test_config():
    """测试配置"""
    print("=" * 60)
    print("飞书机器人配置测试")
    print("=" * 60)

    config = Config()

    # 验证配置
    is_valid, errors = config.validate()

    if not is_valid:
        print("\n❌ 配置验证失败：")
        for error in errors:
            print(f"  - {error}")
        return False

    print("\n✅ 配置验证通过")

    # 显示配置信息
    print("\n【服务配置】")
    print(f"  - 监听地址: {config.HOST}:{config.PORT}")
    print(f"  - 调试模式: {config.DEBUG}")

    print("\n【飞书配置】")
    print(f"  - App ID: {config.APP_ID[:10]}...")
    print(f"  - App Secret: {'*' * 20}")
    print(f"  - Encrypt Key: {'已配置' if config.ENCRYPT_KEY else '未配置'}")

    print("\n【邮件配置】")
    print(f"  - SMTP服务器: {config.SMTP_SERVER}:{config.SMTP_PORT}")
    print(f"  - 发件人: {config.FROM_NAME} <{config.FROM_EMAIL}>")
    print(f"  - 使用TLS: {config.USE_TLS}")

    print("\n【关键字规则】")
    print(f"  - 规则数量: {len(config.KEYWORDS)}")
    print(f"  - 大小写敏感: {config.CASE_SENSITIVE}")
    for i, kw in enumerate(config.KEYWORDS, 1):
        print(f"  {i}. '{kw['keyword']}' -> {', '.join(kw['recipients'])}")

    return True


def test_smtp():
    """测试SMTP连接"""
    print("\n" + "=" * 60)
    print("SMTP连接测试")
    print("=" * 60)

    config = Config()
    email_sender = EmailSender(config)

    print("\n正在连接SMTP服务器...")
    if email_sender.test_connection():
        print("✅ SMTP连接测试成功")
        return True
    else:
        print("❌ SMTP连接测试失败，请检查配置和网络")
        return False


def send_test_email():
    """发送测试邮件"""
    print("\n" + "=" * 60)
    print("发送测试邮件")
    print("=" * 60)

    config = Config()
    email_sender = EmailSender(config)

    # 获取测试收件人
    test_recipient = input("\n请输入测试收件人邮箱地址: ").strip()
    if not test_recipient:
        print("❌ 收件人地址不能为空")
        return False

    # 发送测试邮件
    subject = "[测试] 飞书机器人邮件转发系统"
    body = """
<html>
<body>
    <h2>这是一封测试邮件</h2>
    <p>如果您收到这封邮件，说明飞书机器人邮件转发系统配置正确！</p>
    <hr>
    <p><strong>系统信息：</strong></p>
    <ul>
        <li>SMTP服务器: {}</li>
        <li>发件人: {}</li>
    </ul>
</body>
</html>
""".format(config.SMTP_SERVER, config.FROM_EMAIL)

    print(f"\n正在发送测试邮件到 {test_recipient}...")
    if email_sender.send_email([test_recipient], subject, body):
        print("✅ 测试邮件发送成功，请检查收件箱")
        return True
    else:
        print("❌ 测试邮件发送失败，请查看日志")
        return False


def main():
    """主函数"""
    print("\n🤖 飞书机器人配置测试工具\n")

    # 测试配置
    if not test_config():
        sys.exit(1)

    # 测试SMTP连接
    if not test_smtp():
        print("\n提示: 请检查SMTP配置和网络连接")
        sys.exit(1)

    # 询问是否发送测试邮件
    choice = input("\n是否发送测试邮件? (y/n): ").strip().lower()
    if choice == 'y':
        send_test_email()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 确保配置正确")
    print("2. 启动服务: ./start.sh")
    print("3. 配置飞书开放平台的Webhook地址")
    print("4. 在群组中发送包含关键字的消息进行测试")


if __name__ == '__main__':
    main()
