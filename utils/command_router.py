#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令路由器
解析和路由用户命令
"""

import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class CommandRouter:
    """命令路由器"""

    COMMAND_PATTERNS = {
        'help': r'^[/／](?:帮助|help)$',
        'summary': r'^[/／]日报汇总(?:\s+(\d{4}-\d{2}-\d{2}))?$',
        'set_vacation': r'^[/／]设置调休\s+(\S+)(?:\s+(\d{4}-\d{2}-\d{2}))?$',
        'cancel_vacation': r'^[/／]取消调休\s+(\S+)(?:\s+(\d{4}-\d{2}-\d{2}))?$',
        'query_vacation': r'^[/／]查询调休(?:\s+(\d{4}-\d{2}-\d{2}))?$',
        'my_report': r'^[/／]我的日报(?:\s+(今天|昨天|\d{4}-\d{2}-\d{2}))?$',
    }

    def __init__(self):
        self.compiled_patterns = {
            cmd: re.compile(pattern, re.IGNORECASE)
            for cmd, pattern in self.COMMAND_PATTERNS.items()
        }

    def is_command(self, text: str) -> bool:
        if not text:
            return False

        text = text.strip()
        if not (text.startswith('/') or text.startswith('／')):
            return False

        return self.parse_command(text) is not None

    def parse_command(self, text: str) -> Optional[Dict]:
        if not text:
            return None

        text = text.strip()

        for cmd_name, pattern in self.compiled_patterns.items():
            match = pattern.match(text)
            if match:
                args = [arg for arg in match.groups() if arg is not None]
                logger.info(f"解析命令: {cmd_name}, 参数: {args}")
                return {
                    'command': cmd_name,
                    'args': args,
                    'raw_text': text
                }

        return None

    def get_help_text(self) -> str:
        return """
🤖 **飞书机器人指令帮助**

**日报相关**
• `/日报汇总 [日期]` - 生成日报汇总（默认今天）
  示例: `/日报汇总 2026-02-26`

• `/我的日报 [日期]` - 查询自己的日报
  示例: `/我的日报 昨天`

**调休管理**
• `/设置调休 <姓名> [日期]` - 设置某人调休（默认今天）
  示例: `/设置调休 张三 2026-02-26`

• `/取消调休 <姓名> [日期]` - 取消调休设置
  示例: `/取消调休 张三`

• `/查询调休 [日期]` - 查询调休人员（默认今天）
  示例: `/查询调休`

**其他**
• `/帮助` 或 `/help` - 显示本帮助信息

💡 提示：命令中的日期格式为 YYYY-MM-DD
        """.strip()


_router_instance = None


def get_command_router() -> CommandRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = CommandRouter()
    return _router_instance
