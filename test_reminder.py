#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日报提醒功能
"""

import logging
import os
from dotenv import load_dotenv
from utils.reminder_sender import ReminderSender
from utils.daily_report_storage import DailyReportStorage

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_reminder():
    """测试日报提醒功能"""
    
    # 从环境变量获取配置
    app_id = os.getenv('FEISHU_APP_ID', '')
    app_secret = os.getenv('FEISHU_APP_SECRET', '')
    chat_id = os.getenv('DAILY_REPORT_CHAT_ID', '')
    
    if not app_id or not app_secret:
        logger.error("请在 .env 文件中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        return
    
    if not chat_id:
        logger.error("请在 .env 文件中配置 DAILY_REPORT_CHAT_ID（日报群组ID）")
        return
    
    # 创建提醒发送器
    reminder = ReminderSender(app_id, app_secret)
    
    # 获取已收集的日报
    storage = DailyReportStorage('data/daily_reports.json')
    reports = storage.get_all_reports()
    
    logger.info("=" * 60)
    logger.info("📋 当前日报收集情况：")
    logger.info(f"已收集 {len(reports)} 份日报")
    for report in reports:
        logger.info(f"  - {report.get('sender', '未知')}")
    logger.info("=" * 60)
    
    # 执行检查并提醒
    reminder.check_and_remind(
        chat_id=chat_id,
        reports=reports,
        user_names_file='config/user_names.json'
    )


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🔔 日报提醒功能测试")
    print("=" * 60 + "\n")
    
    test_reminder()
    
    print("\n测试完成！")
