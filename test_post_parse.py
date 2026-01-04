#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试富文本消息解析
"""

import json
import logging
from utils.daily_report_parser import DailyReportParser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_text_from_post(content_json: dict) -> str:
    """
    从 post 类型消息中提取纯文本内容（与app_ws.py中的函数相同）
    """
    try:
        text_parts = []

        # post 消息可能有两种结构：
        # 1. 直接格式: {"title": "", "content": [[...]]}
        # 2. 多语言格式: {"zh_cn": {"title": "", "content": [[...]]}}

        # 先尝试多语言格式
        lang_content = content_json.get('zh_cn') or content_json.get('en_us')

        # 如果没有多语言格式，使用直接格式
        if not lang_content:
            lang_content = content_json

        # 获取标题
        title = lang_content.get('title', '')
        if title and title.strip():
            text_parts.append(title.strip())

        # 获取内容块
        content_blocks = lang_content.get('content', [])

        # 遍历每个段落
        for paragraph in content_blocks:
            # 跳过空段落或None
            if not paragraph:
                # 空段落也要保留（作为段落分隔）
                text_parts.append('')
                continue

            paragraph_text = []

            # 遍历段落中的每个元素
            for element in paragraph:
                if not isinstance(element, dict):
                    continue

                tag = element.get('tag', '')

                if tag == 'text':
                    # 纯文本
                    text = element.get('text', '')
                    if text:
                        paragraph_text.append(text)
                elif tag == 'a':
                    # 链接
                    text = element.get('text', '')
                    if text:
                        paragraph_text.append(text)
                elif tag == 'at':
                    # @某人
                    text = element.get('text', '')
                    if text:
                        paragraph_text.append(text)

            # 合并段落文本
            if paragraph_text:
                combined_text = ''.join(paragraph_text)
                # 只添加非空的段落文本
                if combined_text.strip():
                    text_parts.append(combined_text)

        # 用换行符连接所有部分
        result = '\n'.join(text_parts)
        
        # 清理多余的空行（超过2个连续换行符的情况）
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()

    except Exception as e:
        logger.error(f"提取 post 消息文本失败: {str(e)}", exc_info=True)
        return ""


def test_post_extraction():
    """测试富文本消息提取"""
    
    # 你提供的富文本JSON
    test_post_json = {
        "title": "", 
        "content": [
            [{"tag": "text", "text": "10月20 工作日报：", "style": ["bold"]}], 
            [{"tag": "text", "text": "跟踪问题：", "style": []}], 
            [{"tag": "text", "text": "TSTAS-396", "style": []}], 
            [{"tag": "text", "text": "今天工作内容：", "style": []}], 
            [{"tag": "text", "text": "1. ", "style": []}, {"tag": "text", "text": "合入TSTAS-396 代码，合入TSTAS-396 客户提供的review 代码", "style": []}], 
            [{"tag": "text", "text": "2. ", "style": []}, {"tag": "text", "text": "研究用脚本自动化打包： 已经打包出archive 和crossShare.app", "style": []}], 
            [], 
            [{"tag": "text", "text": "Block 点：", "style": []}], 
            [{"tag": "text", "text": "无", "style": []}], 
            [{"tag": "text", "text": "明日计划：", "style": []}], 
            [{"tag": "text", "text": "  TSTAS-396 完成对打包后的crossShare.app 签名，打包成pkg 签名pkg, 公证pkg 等流程", "style": []}]
        ]
    }
    
    print("=" * 80)
    print("测试富文本消息提取")
    print("=" * 80)
    print("\n原始JSON:")
    print(json.dumps(test_post_json, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("提取的纯文本:")
    print("=" * 80)
    
    # 提取文本
    extracted_text = extract_text_from_post(test_post_json)
    print(extracted_text)
    
    print("\n" + "=" * 80)
    print("日报解析测试:")
    print("=" * 80)
    
    # 测试日报解析
    parser = DailyReportParser()
    is_report = parser.is_daily_report(extracted_text)
    print(f"\n是否为日报: {is_report}")
    
    if is_report:
        report_data = parser.parse(extracted_text, "测试用户")
        print("\n解析结果:")
        for key, value in report_data.items():
            print(f"\n{key}:")
            print(f"  {value}")


if __name__ == '__main__':
    test_post_extraction()
