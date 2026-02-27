#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令处理器测试
"""

from unittest.mock import patch

from utils.command_handler import CommandHandler


class TestCommandHandler:
    def setup_method(self):
        self.handler = CommandHandler(app_id='test_id', app_secret='test_secret')

    def test_handle_help(self):
        result = self.handler.handle_help()
        assert result is not None
        assert '帮助' in result or 'help' in result.lower()

    def test_handle_unknown_command(self):
        result = self.handler.handle_command('unknown', [])
        assert '未知命令' in result or 'unknown' in result.lower()

    def test_handle_summary_today(self):
        self.handler.report_storage.get_all_reports = lambda date: [
            {'sender': '张三', 'work_content': '完成了XXX'}
        ]
        result = self.handler.handle_summary([], {})
        assert '日报汇总' in result
        assert '张三' in result

    def test_handle_summary_with_date(self):
        self.handler.report_storage.get_all_reports = lambda date: []
        result = self.handler.handle_summary(['2026-02-26'], {})
        assert '日报汇总' in result
        assert '2026-02-26' in result

    def test_handle_my_report(self):
        self.handler.report_storage.get_all_reports = lambda date: [
            {'sender': '测试用户', 'work_content': '今日完成X', 'timestamp': '2026-02-26 10:00:00'}
        ]
        context = {'user_id': 'test_user', 'user_name': '测试用户'}
        result = self.handler.handle_my_report([], context)
        assert '日报' in result
        assert '今日完成X' in result

    def test_handle_set_vacation(self):
        result = self.handler.handle_set_vacation(['张三', '2026-02-26'], {})
        assert '成功' in result or '设置' in result

    def test_handle_cancel_vacation(self):
        self.handler.vacation_mgr.set_vacation('张三', '2026-02-26')
        result = self.handler.handle_cancel_vacation(['张三', '2026-02-26'], {})
        assert '取消' in result or '成功' in result

    def test_handle_query_vacation(self):
        self.handler.vacation_mgr.set_vacation('张三', '2026-02-26')
        result = self.handler.handle_query_vacation(['2026-02-26'], {})
        assert '调休' in result
        assert '张三' in result
