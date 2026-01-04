#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报表格生成器
将日报数据生成HTML表格格式的邮件
"""

import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportTableGenerator:
    """日报表格生成器"""

    def generate_html_table(self, reports: List[Dict], date: str = None) -> str:
        """
        生成HTML表格

        Args:
            reports: 日报列表
            date: 日期，如果为None则使用当前日期

        Returns:
            str: HTML格式的表格
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        if not reports:
            return self._generate_empty_report(date)

        # 生成表格HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: "Microsoft YaHei", Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #4a90e2;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .header p {{
            margin: 5px 0 0 0;
            font-size: 14px;
        }}
        .content {{
            background-color: white;
            padding: 20px;
            border-radius: 0 0 5px 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th {{
            background-color: #5a9fd4;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: bold;
            border: 1px solid #ddd;
        }}
        th.name-col {{
            background-color: #4a7ba7;
        }}
        td {{
            padding: 10px 8px;
            border: 1px solid #ddd;
            vertical-align: top;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #f0f7ff;
        }}
        .name-col {{
            width: 100px;
            font-weight: bold;
            text-align: center;
        }}
        td.name-col {{
            background-color: #e8f4fd;
            font-size: 14px;
            vertical-align: middle;
        }}
        .issue-col {{
            width: 150px;
        }}
        .content-col {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .block-col {{
            width: 100px;
        }}
        .plan-col {{
            width: 150px;
        }}
        .footer {{
            margin-top: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
            color: #666;
            font-size: 12px;
        }}
        .summary {{
            margin-bottom: 15px;
            padding: 10px;
            background-color: #e8f4fd;
            border-left: 4px solid #4a90e2;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 团队日报汇总</h1>
        <p>日期: {date} | 共收到 {len(reports)} 份日报</p>
    </div>
    <div class="content">
        <div class="summary">
            <strong>📌 汇总说明：</strong> 本邮件汇总了团队成员今日提交的所有日报，请查阅。
        </div>
        <table>
            <thead>
                <tr>
                    <th class="name-col">姓名</th>
                    <th class="issue-col">跟踪问题</th>
                    <th class="content-col">今天工作内容</th>
                    <th class="block-col">Block点</th>
                    <th class="plan-col">下一工作日计划</th>
                </tr>
            </thead>
            <tbody>
"""

        # 添加每条日报
        for report in reports:
            sender = self._escape_html(report.get('sender', '未知'))
            # 特殊处理：人员姓名替换（保持连续性）
            if sender == '李尚璋':
                sender = '蔡绍朋'
            if sender == 'FrankCheng':
                sender = '成良雨'
            tracking_issues = self._escape_html(report.get('tracking_issues', '无'))
            work_content = self._escape_html(report.get('work_content', '无'))
            blocks = self._escape_html(report.get('blocks', '无'))
            next_plan = self._escape_html(report.get('next_plan', '无'))

            html += f"""
                <tr>
                    <td class="name-col">{sender}</td>
                    <td class="issue-col">{tracking_issues}</td>
                    <td class="content-col">{work_content}</td>
                    <td class="block-col">{blocks}</td>
                    <td class="plan-col">{next_plan}</td>
                </tr>
"""

        # 添加尾部
        html += f"""
            </tbody>
        </table>
    </div>
    <div class="footer">
        <p>🤖 本邮件由飞书消息提醒机器人自动生成并发送</p>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""

        return html

    def _generate_empty_report(self, date: str) -> str:
        """生成空日报提醒"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: "Microsoft YaHei", Arial, sans-serif;
            margin: 20px;
        }}
        .empty-message {{
            padding: 30px;
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            text-align: center;
        }}
        .empty-message h2 {{
            color: #856404;
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="empty-message">
        <h2>⚠️ 暂无日报</h2>
        <p>截至目前（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}），{date} 尚未收到任何日报。</p>
    </div>
</body>
</html>
"""
        return html

    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        if not text:
            return ""

        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#39;')

        return text


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    generator = ReportTableGenerator()

    # 测试数据
    test_reports = [
        {
            'sender': '熊延福',
            'tracking_issues': 'TSTAS-431、TSTAS-366',
            'work_content': '1、整理431相关的内容，提交patch到jira。\n2、安装最新jack提供的img后，测试365相关的jack提供的windows安装包，在windows没有重现UDP包被拦截的问题。\n3、继续开发整理366相关的flow。\n4、开周会讨论当前工作进度和合优先级，插单437内容，讨论相关方案，明天启动开发。',
            'blocks': '无',
            'next_plan': 'TSTAS-437',
            'timestamp': '2025-10-21 14:30:00'
        },
        {
            'sender': '蔡绍朋',
            'tracking_issues': 'TSTAS-436',
            'work_content': '1 开会确认本周jira问题，TSTAS-436 调研app上架谷歌商店提示so不支持16kb问题，命令readelf；尝试用NDK命令编译so，但是ndk25以后不带lld，不支持--enable-compat-16kb参数。还在继续整理',
            'blocks': '无',
            'next_plan': '1.TSTAS-421',
            'timestamp': '2025-10-21 15:00:00'
        }
    ]

    html = generator.generate_html_table(test_reports, '2025-10-21')

    # 保存为HTML文件以便预览
    with open('test_report.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("HTML表格已生成，保存为 test_report.html")
    print(f"生成了 {len(test_reports)} 条日报的汇总表格")
