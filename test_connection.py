#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人连接测试脚本
用于验证配置和网络连接是否正常
"""

import os
import sys
import logging
from dotenv import load_dotenv
import lark_oapi as lark

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title):
    """打印分隔线"""
    logger.info("=" * 60)
    logger.info(f"  {title}")
    logger.info("=" * 60)

def check_env_file():
    """检查环境变量文件"""
    print_section("1. 检查环境变量配置文件")

    if not os.path.exists('.env'):
        logger.error("❌ 未找到 .env 配置文件")
        logger.info("请复制 .env.example 为 .env 并填写配置")
        return False

    logger.info("✅ .env 文件存在")
    return True

def check_required_configs():
    """检查必需的配置项"""
    print_section("2. 检查必需配置项")

    load_dotenv()

    required_configs = {
        'FEISHU_APP_ID': 'cli_',
        'FEISHU_APP_SECRET': '',
        'FEISHU_VERIFICATION_TOKEN': '',
    }

    all_valid = True

    for key, prefix in required_configs.items():
        value = os.getenv(key, '')

        if not value:
            logger.error(f"❌ {key} 未配置")
            all_valid = False
        elif prefix and not value.startswith(prefix):
            logger.warning(f"⚠️  {key} 格式可能不正确（应该以 '{prefix}' 开头）")
            logger.info(f"   当前值: {value[:10]}...")
            all_valid = False
        else:
            logger.info(f"✅ {key}: {value[:15]}...")

    return all_valid

def check_optional_configs():
    """检查可选配置项"""
    print_section("3. 检查可选配置项")

    all_valid = True

    # 日报群组ID
    chat_id = os.getenv('DAILY_REPORT_CHAT_ID', '')
    if chat_id:
        if chat_id.startswith('oc_'):
            logger.info(f"✅ DAILY_REPORT_CHAT_ID: {chat_id}")
            logger.info("   群组过滤已启用，只会处理该群组的消息")
        else:
            logger.warning(f"⚠️  DAILY_REPORT_CHAT_ID 格式可能不正确")
            logger.info(f"   应该是 'oc_' 开头的群组ID，当前值: {chat_id}")
            all_valid = False
    else:
        logger.warning("⚠️  DAILY_REPORT_CHAT_ID 未配置")
        logger.info("   机器人将处理所有群组的消息，建议配置目标群组ID")

    # 邮件配置
    smtp_server = os.getenv('SMTP_SERVER', '')
    smtp_user = os.getenv('SMTP_USER', '')

    if smtp_server and smtp_user:
        logger.info(f"✅ SMTP配置: {smtp_server} ({smtp_user})")
    else:
        logger.warning("⚠️  SMTP邮件配置不完整（日报功能需要）")

    return all_valid

def test_network_connection():
    """测试网络连接"""
    print_section("4. 测试网络连接")

    try:
        import urllib.request
        import socket

        # 设置超时
        socket.setdefaulttimeout(10)

        logger.info("正在测试飞书API连接...")

        # 测试飞书开放平台连接
        response = urllib.request.urlopen('https://open.feishu.cn')
        if response.status == 200:
            logger.info("✅ 飞书开放平台连接正常")
        else:
            logger.warning(f"⚠️  飞书开放平台返回状态码: {response.status}")

        return True

    except Exception as e:
        logger.error(f"❌ 网络连接失败: {str(e)}")
        logger.info("可能的原因：")
        logger.info("  1. 网络不可用")
        logger.info("  2. 防火墙阻止连接")
        logger.info("  3. 代理配置问题")
        logger.info("  4. VPN干扰")
        return False

def test_feishu_client():
    """测试飞书客户端初始化"""
    print_section("5. 测试飞书SDK客户端")

    try:
        app_id = os.getenv('FEISHU_APP_ID', '')
        app_secret = os.getenv('FEISHU_APP_SECRET', '')

        if not app_id or not app_secret:
            logger.error("❌ APP_ID 或 APP_SECRET 未配置")
            return False

        logger.info("正在初始化飞书客户端...")

        # 创建客户端
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.ERROR) \
            .build()

        logger.info("✅ 飞书客户端初始化成功")
        logger.info("💡 注意：实际凭证验证将在启动服务时进行")
        return True

    except Exception as e:
        logger.error(f"❌ 飞书客户端初始化失败: {str(e)}")
        logger.info("请检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET 是否正确")
        return False

def print_summary(results):
    """打印测试摘要"""
    print_section("测试摘要")

    total = len(results)
    # 过滤掉None值
    passed = sum(1 for v in results.values() if v is True)

    logger.info(f"总计: {total} 项测试")
    logger.info(f"通过: {passed} 项")
    logger.info(f"失败: {total - passed} 项")
    logger.info("")

    if all(results.values()):
        logger.info("🎉 所有测试通过！可以启动服务了")
        logger.info("")
        logger.info("启动命令：")
        logger.info("  macOS/Linux: ./start_ws_robust.sh")
        logger.info("  Windows:     start_ws_robust.bat")
    else:
        logger.info("❌ 部分测试失败，请根据上述提示修复问题")
        logger.info("")
        logger.info("常见问题：")
        logger.info("  1. 配置 .env 文件中的飞书凭证")
        logger.info("  2. 配置 DAILY_REPORT_CHAT_ID 群组ID")
        logger.info("  3. 检查网络连接（关闭VPN）")
        logger.info("  4. 查看详细排查指南: WebSocket连接问题排查指南.md")

    logger.info("=" * 60)

def main():
    """主函数"""
    print_section("飞书机器人连接测试")
    logger.info("此脚本将测试配置和网络连接是否正常")
    logger.info("")

    results = {}

    # 执行测试
    results['env_file'] = check_env_file()
    if results['env_file']:
        results['required_configs'] = check_required_configs()
        results['optional_configs'] = check_optional_configs()
        results['network'] = test_network_connection()
        results['feishu_client'] = test_feishu_client()

    # 打印摘要
    logger.info("")
    print_summary(results)

    # 返回退出码
    return 0 if all(results.values()) else 1

if __name__ == '__main__':
    sys.exit(main())
