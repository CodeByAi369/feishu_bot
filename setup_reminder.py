#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速配置日报提醒功能
"""

import os
import json


def setup_reminder():
    """配置日报提醒功能"""
    
    print("\n" + "=" * 60)
    print("🔔 日报提醒功能配置向导")
    print("=" * 60 + "\n")
    
    # 检查 .env 文件
    env_file = '.env'
    if not os.path.exists(env_file):
        print("❌ 未找到 .env 文件")
        print("请先复制 .env.example 为 .env 并配置基本信息")
        return
    
    print("✅ 找到 .env 文件\n")
    
    # 读取现有配置
    with open(env_file, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    # 检查是否已配置提醒功能
    if 'DAILY_REPORT_REMINDER_ENABLED' in env_content:
        print("✅ 日报提醒配置已存在\n")
    else:
        print("⚠️  .env 文件中缺少日报提醒配置")
        print("正在添加配置...\n")
        
        reminder_config = """
# ============================================
# 日报提醒功能配置（@未提交日报的人）
# ============================================

# 是否启用日报提醒功能
DAILY_REPORT_REMINDER_ENABLED=True

# 日报提醒时间（24小时制，格式 HH:MM）
# 例如：21:00 表示每天晚上9点检查并提醒未提交日报的人
DAILY_REPORT_REMINDER_TIME=21:00
"""
        
        with open(env_file, 'a', encoding='utf-8') as f:
            f.write(reminder_config)
        
        print("✅ 已添加日报提醒配置到 .env 文件\n")
    
    # 检查用户名单文件
    user_names_file = 'config/user_names.json'
    if os.path.exists(user_names_file):
        with open(user_names_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            users = data.get('映射', {})
        
        print(f"✅ 找到用户名单文件，共 {len(users)} 个用户：")
        for user_id, name in users.items():
            print(f"   - {name} ({user_id})")
        print()
    else:
        print("⚠️  未找到用户名单文件")
        print("启动机器人后，在群组发送「获取成员列表」命令自动生成\n")
    
    # 配置总结
    print("=" * 60)
    print("📋 配置总结")
    print("=" * 60)
    print()
    print("✅ 必需配置：")
    print("   1. FEISHU_APP_ID - 飞书应用ID")
    print("   2. FEISHU_APP_SECRET - 飞书应用密钥")
    print("   3. DAILY_REPORT_CHAT_ID - 日报群组ID")
    print("   4. DAILY_REPORT_REMINDER_TIME - 提醒时间（如 21:00）")
    print()
    print("✅ 可选配置：")
    print("   1. DAILY_REPORT_REMINDER_ENABLED - 是否启用提醒（默认True）")
    print()
    print("📝 下一步操作：")
    print("   1. 编辑 .env 文件，填写必需的配置项")
    print("   2. 启动机器人：./start_ws.sh")
    print("   3. 在群组发送「获取成员列表」生成用户名单")
    print("   4. 测试提醒功能：python test_reminder.py")
    print()
    print("=" * 60)
    print()


if __name__ == '__main__':
    setup_reminder()
