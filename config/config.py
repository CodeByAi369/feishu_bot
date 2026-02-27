#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
从环境变量和配置文件加载配置
"""

import os
import json
from dotenv import load_dotenv


class Config:
    """配置类"""

    def __init__(self):
        # 加载 .env 文件中的环境变量
        load_dotenv()

        # Flask服务配置
        self.HOST = os.getenv('HOST', '0.0.0.0')
        self.PORT = int(os.getenv('PORT', 5000))
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

        # 飞书机器人配置
        self.APP_ID = os.getenv('FEISHU_APP_ID', '')
        self.APP_SECRET = os.getenv('FEISHU_APP_SECRET', '')
        self.VERIFICATION_TOKEN = os.getenv('FEISHU_VERIFICATION_TOKEN', '')
        self.ENCRYPT_KEY = os.getenv('FEISHU_ENCRYPT_KEY', '')  # 可选，用于验证签名

        # SMTP邮件配置
        self.SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
        self.SMTP_USER = os.getenv('SMTP_USER', '')
        self.SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
        self.FROM_EMAIL = os.getenv('FROM_EMAIL', self.SMTP_USER)
        self.FROM_NAME = os.getenv('FROM_NAME', '飞书机器人')
        self.USE_TLS = os.getenv('USE_TLS', 'True').lower() == 'true'

        # 关键字匹配配置
        self.CASE_SENSITIVE = os.getenv('CASE_SENSITIVE', 'False').lower() == 'true'

        # 加载关键字规则
        self.KEYWORDS = self._load_keywords()

        # 日报汇总配置
        self.DAILY_REPORT_ENABLED = os.getenv('DAILY_REPORT_ENABLED', 'True').lower() == 'true'
        self.DAILY_REPORT_CHAT_ID = os.getenv('DAILY_REPORT_CHAT_ID', '')  # 日报群组ID
        self.DAILY_REPORT_SEND_MODE = os.getenv('DAILY_REPORT_SEND_MODE', 'scheduled').lower()  # realtime 或 scheduled
        self.DAILY_REPORT_SCHEDULE_TIME = os.getenv('DAILY_REPORT_SCHEDULE_TIME', '18:00')
        self.DAILY_REPORT_RECIPIENTS = [
            email.strip()
            for email in os.getenv('DAILY_REPORT_RECIPIENTS', '').split(',')
            if email.strip()
        ]
        self.DAILY_REPORT_CC = [
            email.strip()
            for email in os.getenv('DAILY_REPORT_CC', '').split(',')
            if email.strip()
        ]
        self.DAILY_REPORT_BCC = [
            email.strip()
            for email in os.getenv('DAILY_REPORT_BCC', '').split(',')
            if email.strip()
        ]
        self.DAILY_REPORT_STORAGE_FILE = os.getenv('DAILY_REPORT_STORAGE_FILE', 'data/daily_reports.json')
        
        # 日报提醒配置
        self.DAILY_REPORT_REMINDER_ENABLED = os.getenv('DAILY_REPORT_REMINDER_ENABLED', 'True').lower() == 'true'
        self.DAILY_REPORT_REMINDER_TIME = os.getenv('DAILY_REPORT_REMINDER_TIME', '21:00')  # 提醒时间
        
        # 需要提交日报的用户ID列表（用逗号分隔，为空表示user_names.json中的所有用户）
        required_users_str = os.getenv('DAILY_REPORT_REQUIRED_USERS', '')
        self.DAILY_REPORT_REQUIRED_USERS = [
            user_id.strip() 
            for user_id in required_users_str.split(',') 
            if user_id.strip()
        ] if required_users_str else []

        # 日报即时汇总配置
        self.DAILY_REPORT_EXPECTED_COUNT = int(os.getenv('DAILY_REPORT_EXPECTED_COUNT', '5'))  # 预期日报人数
        self.DAILY_REPORT_AUTO_SEND_ON_COMPLETE = os.getenv('DAILY_REPORT_AUTO_SEND_ON_COMPLETE', 'True').lower() == 'true'  # 全员提交后自动发送

        # 第二天补充汇总配置
        self.DAILY_REPORT_NEXT_DAY_SUMMARY_ENABLED = os.getenv('DAILY_REPORT_NEXT_DAY_SUMMARY_ENABLED', 'True').lower() == 'true'
        self.DAILY_REPORT_NEXT_DAY_SUMMARY_TIME = os.getenv('DAILY_REPORT_NEXT_DAY_SUMMARY_TIME', '10:00')  # 第二天汇总时间

        # 休假管理配置
        self.VACATION_STORAGE_FILE = os.getenv('VACATION_STORAGE_FILE', 'data/vacations.json')

        # 工作日日历配置
        self.HOLIDAY_API_URL = os.getenv('HOLIDAY_API_URL', 'http://timor.tech/api/holiday/year/{year}')
        self.HOLIDAY_CACHE_FILE = os.getenv('HOLIDAY_CACHE_FILE', 'data/holidays_cache.json')
        self.HOLIDAY_CONFIG_FILE = os.getenv('HOLIDAY_CONFIG_FILE', 'config/holidays.json')

        # 命令功能配置
        self.COMMAND_ENABLED = os.getenv('COMMAND_ENABLED', 'True').lower() == 'true'
        admin_users = os.getenv('COMMAND_ADMIN_USERS', '')
        self.COMMAND_ADMIN_USERS = [
            user_id.strip() for user_id in admin_users.split(',') if user_id.strip()
        ]

    def _load_keywords(self):
        """
        加载关键字配置
        从环境变量或配置文件加载
        """
        # 优先从配置文件加载
        config_file = os.getenv('KEYWORDS_CONFIG_FILE', 'config/keywords.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载关键字配置文件失败: {str(e)}")

        # 从环境变量加载（JSON格式）
        keywords_json = os.getenv('KEYWORDS_JSON', '[]')
        try:
            return json.loads(keywords_json)
        except Exception as e:
            print(f"解析关键字JSON失败: {str(e)}")
            return []

    def validate(self):
        """
        验证配置是否完整
        :return: (是否有效, 错误信息列表)
        """
        errors = []

        # 验证飞书配置
        if not self.APP_ID:
            errors.append("缺少飞书 APP_ID")
        if not self.APP_SECRET:
            errors.append("缺少飞书 APP_SECRET")

        # 验证邮件配置
        if not self.SMTP_SERVER:
            errors.append("缺少 SMTP_SERVER")
        if not self.SMTP_USER:
            errors.append("缺少 SMTP_USER")
        if not self.SMTP_PASSWORD:
            errors.append("缺少 SMTP_PASSWORD")

        # 验证关键字配置
        if not self.KEYWORDS:
            errors.append("未配置任何关键字规则")

        return len(errors) == 0, errors
