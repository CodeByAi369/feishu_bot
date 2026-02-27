#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令路由器测试
"""

from utils.command_router import CommandRouter


class TestCommandRouter:
    def setup_method(self):
        self.router = CommandRouter()

    def test_is_command_help(self):
        assert self.router.is_command('/帮助') is True
        assert self.router.is_command('/help') is True
        assert self.router.is_command('帮助') is False

    def test_is_command_summary(self):
        assert self.router.is_command('/日报汇总') is True
        assert self.router.is_command('/日报汇总 2026-02-26') is True

    def test_parse_command_help(self):
        cmd = self.router.parse_command('/帮助')
        assert cmd['command'] == 'help'
        assert cmd['args'] == []

    def test_parse_command_summary(self):
        cmd = self.router.parse_command('/日报汇总 2026-02-26')
        assert cmd['command'] == 'summary'
        assert cmd['args'] == ['2026-02-26']

    def test_parse_command_set_vacation(self):
        cmd = self.router.parse_command('/设置调休 张三 2026-02-26')
        assert cmd['command'] == 'set_vacation'
        assert '张三' in cmd['args']
        assert '2026-02-26' in cmd['args']

    def test_not_a_command(self):
        assert self.router.is_command('今天的日报') is False
        assert self.router.parse_command('普通消息') is None
