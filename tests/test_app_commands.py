#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主应用命令集成测试
"""

from utils.command_router import CommandRouter
from utils.command_handler import CommandHandler


class TestAppCommands:
    def test_command_integration_help(self):
        router = CommandRouter()
        handler = CommandHandler('test_id', 'test_secret')

        text = '/帮助'
        assert router.is_command(text) is True

        cmd = router.parse_command(text)
        result = handler.handle_command(cmd['command'], cmd['args'], {})
        assert '帮助' in result

    def test_command_integration_set_vacation(self):
        router = CommandRouter()
        handler = CommandHandler('test_id', 'test_secret')

        text = '/设置调休 张三 2026-02-27'
        cmd = router.parse_command(text)
        result = handler.handle_command(cmd['command'], cmd['args'], {})
        assert '成功设置调休' in result
