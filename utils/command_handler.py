#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令处理器
处理具体的命令逻辑
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

import lark_oapi as lark

from utils.command_router import get_command_router
from utils.vacation_manager import VacationManager
from utils.daily_report_storage import DailyReportStorage

logger = logging.getLogger(__name__)


class CommandHandler:
    """命令处理器"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.router = get_command_router()
        self.vacation_mgr = VacationManager()
        self.report_storage = DailyReportStorage()

        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .build()

    def handle_command(self, command: str, args: list, context: Dict[str, Any] = None) -> str:
        context = context or {}

        handler_map = {
            'help': self.handle_help,
            'summary': self.handle_summary,
            'set_vacation': self.handle_set_vacation,
            'cancel_vacation': self.handle_cancel_vacation,
            'query_vacation': self.handle_query_vacation,
            'my_report': self.handle_my_report,
        }

        handler = handler_map.get(command)
        if handler is None:
            return f"❌ 未知命令: {command}\n\n输入 /帮助 查看可用命令"

        try:
            return handler(args, context)
        except Exception as e:
            logger.error(f"处理命令失败: {command}, 错误: {e}", exc_info=True)
            return f"❌ 命令执行失败: {str(e)}\n\n请检查命令格式，输入 /帮助 查看帮助"

    def handle_help(self, args: list = None, context: Dict = None) -> str:
        return self.router.get_help_text()

    def handle_summary(self, args: list, context: Dict) -> str:
        date = args[0] if args else datetime.now().strftime('%Y-%m-%d')
        reports = self.report_storage.get_all_reports(date)

        if not reports:
            return f"📊 **日报汇总 - {date}**\n\n暂无日报数据"

        summary = f"📊 **日报汇总 - {date}**\n\n"
        summary += f"共收到 {len(reports)} 份日报：\n\n"

        for i, report in enumerate(reports, 1):
            name = report.get('sender', report.get('name', '未知'))
            content = report.get('work_content') or report.get('content') or '无内容'
            if len(content) > 100:
                content = content[:100] + '...'
            summary += f"{i}. **{name}**\n"
            summary += f"   {content}\n\n"

        vacation_users = self.vacation_mgr.get_vacation_users(date)
        if vacation_users:
            summary += "🏖️ **调休人员**:\n"
            for user in vacation_users:
                summary += f"  • {user}\n"

        return summary

    def handle_set_vacation(self, args: list, context: Dict) -> str:
        if not args:
            return "❌ 参数错误\n\n格式: `/设置调休 <姓名> [日期]`\n示例: `/设置调休 张三 2026-02-26`"

        name = args[0]
        date = args[1] if len(args) > 1 else datetime.now().strftime('%Y-%m-%d')

        success = self.vacation_mgr.set_vacation(name, date)
        if success:
            return f"✅ 成功设置调休\n\n**姓名**: {name}\n**日期**: {date}"
        return "❌ 设置调休失败\n\n请检查参数是否正确"

    def handle_cancel_vacation(self, args: list, context: Dict) -> str:
        if not args:
            return "❌ 参数错误\n\n格式: `/取消调休 <姓名> [日期]`\n示例: `/取消调休 张三 2026-02-26`"

        name = args[0]
        date = args[1] if len(args) > 1 else datetime.now().strftime('%Y-%m-%d')

        success = self.vacation_mgr.cancel_vacation(name, date)
        if success:
            return f"✅ 成功取消调休\n\n**姓名**: {name}\n**日期**: {date}"
        return "❌ 取消调休失败\n\n该用户可能未设置调休"

    def handle_query_vacation(self, args: list, context: Dict) -> str:
        date = args[0] if args else datetime.now().strftime('%Y-%m-%d')
        vacation_users = self.vacation_mgr.get_vacation_users(date)

        result = f"🏖️ **调休人员查询 - {date}**\n\n"
        if not vacation_users:
            return result + "暂无调休人员"

        result += f"共 {len(vacation_users)} 人：\n\n"
        for user in vacation_users:
            result += f"  • {user}\n"
        return result

    def handle_my_report(self, args: list, context: Dict) -> str:
        user_name = context.get('user_name', '未知用户')
        date_str = args[0] if args else None

        if date_str in (None, '今天'):
            date = datetime.now().strftime('%Y-%m-%d')
        elif date_str == '昨天':
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            date = date_str

        reports = self.report_storage.get_all_reports(date)
        my_report = next((r for r in reports if r.get('sender') == user_name or r.get('name') == user_name), None)

        if not my_report:
            return f"📝 **我的日报 - {date}**\n\n暂无日报记录"

        content = my_report.get('work_content') or my_report.get('content') or '无内容'
        submit_time = my_report.get('timestamp') or my_report.get('time') or '未知'

        return (
            f"📝 **我的日报 - {date}**\n\n"
            f"**提交时间**: {submit_time}\n\n"
            f"**内容**:\n{content}"
        )
