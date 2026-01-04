#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键字匹配器
支持模糊匹配
"""

import logging
import re

logger = logging.getLogger(__name__)


class KeywordMatcher:
    """关键字匹配器"""

    def __init__(self, config):
        """
        初始化关键字匹配器
        :param config: 配置对象
        """
        self.keywords = config.KEYWORDS
        self.case_sensitive = config.CASE_SENSITIVE
        logger.info(f"关键字匹配器初始化完成，共加载 {len(self.keywords)} 个关键字规则")

    def match(self, text):
        """
        匹配文本中的关键字（模糊匹配）
        :param text: 待匹配的文本
        :return: 匹配到的关键字列表，每个元素包含 keyword 和 recipients
        """
        matched = []

        for keyword_info in self.keywords:
            keyword = keyword_info['keyword']
            recipients = keyword_info['recipients']

            # 模糊匹配：关键字在文本中出现即匹配
            if self._fuzzy_match(text, keyword):
                matched.append({
                    'keyword': keyword,
                    'recipients': recipients
                })
                logger.info(f"匹配成功 - 关键字: {keyword}, 文本: {text}")

        return matched

    def _fuzzy_match(self, text, keyword):
        """
        模糊匹配
        :param text: 文本
        :param keyword: 关键字
        :return: 是否匹配
        """
        if self.case_sensitive:
            # 区分大小写
            return keyword in text
        else:
            # 不区分大小写
            return keyword.lower() in text.lower()

    def match_regex(self, text, pattern):
        """
        正则表达式匹配（高级功能，可选）
        :param text: 文本
        :param pattern: 正则表达式
        :return: 是否匹配
        """
        try:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            return re.search(pattern, text, flags) is not None
        except Exception as e:
            logger.error(f"正则匹配失败: {str(e)}")
            return False
