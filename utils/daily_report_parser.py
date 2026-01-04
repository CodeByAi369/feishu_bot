#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报解析器
解析飞书群消息中的日报内容
"""

import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DailyReportParser:
    """日报解析器类"""

    def __init__(self):
        # 日报识别关键字（任意一个存在即认为是日报）
        self.report_keywords = ["跟踪问题", "今天工作内容", "今日工作内容", "工作内容"]

    def is_daily_report(self, text: str) -> bool:
        """
        判断消息是否为日报

        Args:
            text: 消息文本

        Returns:
            bool: 是否为日报
        """
        text_lower = text.lower()
        for keyword in self.report_keywords:
            if keyword in text:
                return True
        return False

    def parse(self, text: str, sender_name: str = "未知") -> Optional[Dict]:
        """
        解析日报内容

        Args:
            text: 消息文本
            sender_name: 发送者姓名

        Returns:
            Dict: 解析后的日报数据，如果不是日报则返回 None
            {
                'sender': '发送者姓名',
                'tracking_issues': '跟踪问题',
                'work_content': '今天工作内容',
                'blocks': 'Block点',
                'next_plan': '下一工作日计划'
            }
        """
        if not self.is_daily_report(text):
            return None

        try:
            report_data = {
                'sender': sender_name,
                'tracking_issues': self._extract_tracking_issues(text),
                'work_content': self._extract_work_content(text),
                'blocks': self._extract_blocks(text),
                'next_plan': self._extract_next_plan(text)
            }

            logger.info(f"成功解析日报 - 发送者: {sender_name}")
            return report_data

        except Exception as e:
            logger.error(f"解析日报失败: {str(e)}", exc_info=True)
            return None

    def _extract_issue_numbers(self, text: str) -> str:
        """
        从文本中提取所有问题编号（TSTAS-XXX格式）

        Args:
            text: 输入文本

        Returns:
            str: 用顿号分隔的问题编号，如 "TSTAS-431、TSTAS-366"
        """
        # 查找所有 TSTAS-数字 格式的问题编号
        issue_pattern = r'TSTAS-\d+'
        issues = re.findall(issue_pattern, text, re.IGNORECASE)

        if issues:
            # 去重并保持顺序
            unique_issues = []
            seen = set()
            for issue in issues:
                issue_upper = issue.upper()  # 统一转为大写
                if issue_upper not in seen:
                    seen.add(issue_upper)
                    unique_issues.append(issue_upper)

            return '、'.join(unique_issues)

        return "无"

    def _extract_tracking_issues(self, text: str) -> str:
        """提取跟踪问题（只提取问题编号）"""
        # 匹配 "跟踪问题：TSTAS-431、TSTAS-366" 或 "跟踪问题: TSTAS-431"
        patterns = [
            # 带冒号的格式
            r'跟踪问题[：:]\s*(.+?)(?:\n|今天|今日|工作内容|block|Block|下一|下个|$)',
            # 不带冒号的格式（跟踪问题后直接换行）
            r'跟踪问题\s*\n\s*(.+?)(?:\n\n|今天|今日|工作内容|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                # 只提取问题编号
                issues = self._extract_issue_numbers(content)
                if issues != "无":
                    return issues

        # 如果没有找到跟踪问题区域，只在文本开头部分查找TSTAS（避免误提取工作内容中的编号）
        # 只在前100个字符内查找（通常跟踪问题在开头）
        text_header = text[:100]
        issues = self._extract_issue_numbers(text_header)
        return issues

    def _extract_work_content(self, text: str) -> str:
        """提取今天工作内容"""
        patterns = [
            # 匹配到Block点/lock点/下一工作日/下个工作日之前的内容
            # 支持更多变体：下工作日、次日等
            r'(?:今天|今日)工作内容[：:]\s*(.+?)(?=(?:block|lock)\s*点|下[一个]*工作日|明(?:日|天)|次日|$)',
            r'工作内容[：:]\s*(.+?)(?=(?:block|lock)\s*点|下[一个]*工作日|明(?:日|天)|次日|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                # 再次清理，移除可能的"Block点"或"lock点"之后的内容
                content = re.split(r'(?:block|lock)\s*点', content, flags=re.IGNORECASE)[0]
                content = re.split(r'下[一个]*工作日', content, flags=re.IGNORECASE)[0]
                content = re.split(r'明(?:日|天)|次日', content, flags=re.IGNORECASE)[0]
                return content.strip() if content.strip() else "无"

        return "无"

    def _extract_blocks(self, text: str) -> str:
        """提取Block点（支持block/Block/lock的各种写法）"""
        patterns = [
            # 匹配 "Block点" 或 "lock点"，直到遇到下一个区域
            # 支持多种下一工作日的表达方式：
            # - 明日/明天 (+ 可选的"计划"、"工作计划"等)
            # - 下一/下个/下工作日 (+ 可选的"的"、"计划"等)
            # - 次日 (+ 可选的"计划")
            r'(?:block|lock)\s*点[：:]?\s*(.+?)(?=明(?:日|天)|下[一个]*工作日|次日|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                blocks = match.group(1).strip()
                # 移除可能的换行和多余空白
                blocks = blocks.strip()
                # 如果blocks中还包含了"明日"或"下一/下个"等关键字，再次清理
                # 使用更全面的分割模式，包括各种变体
                blocks = re.split(r'明(?:日|天)|下[一个]*工作日|次日', blocks, flags=re.IGNORECASE)[0].strip()
                return blocks if blocks else "无"

        return "无"

    def _extract_next_plan(self, text: str) -> str:
        """提取下一工作日计划（只提取问题编号）"""
        # 支持多种表达方式：明日、明天、下一工作日、下个工作日、下工作日、次日
        patterns = [
            # 优先匹配带冒号的
            r'明(?:日|天)(?:的)?(?:计划|工作计划)?[：:]\s*(.+)',
            r'下[一个]*工作日(?:的)?(?:计划|工作计划)?[：:]\s*(.+)',
            r'次日(?:的)?(?:计划|工作计划)?[：:]\s*(.+)',
            # 匹配不带冒号的（但要确保不是在其他内容中）
            r'明(?:日|天)(?:的)?(?:计划|工作计划)?\s+(.+)',
            r'下[一个]*工作日(?:的)?(?:计划|工作计划)?\s+(.+)',
            r'次日(?:的)?(?:计划|工作计划)?\s+(.+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                # 只提取问题编号
                issues = self._extract_issue_numbers(content)
                return issues

        return "无"


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = DailyReportParser()

    # 测试日报1
    test_report1 = """跟踪问题：TSTAS-431、TSTAS-366

今天工作内容：
1、整理431相关的内容，提交patch到jira。
2、安装最新jack提供的img后，测试365相关的jack提供的windows安装包，在windows没有重现UDP包被拦截的问题。
3、继续开发整理366相关的flow。
4、开周会讨论当前工作进度和合优先级，插单437内容，讨论相关方案，明天启动开发。

Block点：无。

下一个工作日计划：
TSTAS-437"""

    # 测试日报2
    test_report2 = """跟踪问题
TSTAS-436
今天的工作内容:
1 开会确认本周jira问题，TSTAS-436 调研app上架谷歌商店提示so不支持16kb问题，命令readelf

Block点：
无

下一个工作日的工作计划
1.TSTAS-421"""

    print("=" * 60)
    print("测试日报1:")
    print("=" * 60)
    result1 = parser.parse(test_report1, "张三")
    if result1:
        for key, value in result1.items():
            print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print("测试日报2:")
    print("=" * 60)
    result2 = parser.parse(test_report2, "李四")
    if result2:
        for key, value in result2.items():
            print(f"{key}: {value}")
