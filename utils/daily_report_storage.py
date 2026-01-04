#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报存储管理器
用于存储和管理收集到的日报数据
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Dict
from threading import Lock

logger = logging.getLogger(__name__)


class DailyReportStorage:
    """日报存储管理器"""

    def __init__(self, storage_file: str = "data/daily_reports.json"):
        """
        初始化存储管理器

        Args:
            storage_file: 存储文件路径
        """
        self.storage_file = storage_file
        self.reports_by_date = {}  # {date: {'reports': [...], 'sent': False}}
        self.lock = Lock()  # 线程锁，确保并发安全

        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)

        # 加载已有数据
        self._load_reports()

    def add_report(self, report: Dict, report_date: str = None) -> bool:
        """
        添加日报

        Args:
            report: 日报数据字典
            report_date: 日报日期 (YYYY-MM-DD)，默认为今天

        Returns:
            bool: 是否添加成功
        """
        try:
            with self.lock:
                # 确定日报日期
                if report_date is None:
                    report_date = report.get('date', datetime.now().strftime('%Y-%m-%d'))

                # 确保该日期的数据结构存在
                if report_date not in self.reports_by_date:
                    self.reports_by_date[report_date] = {
                        'reports': [],
                        'sent': False
                    }

                # 获取该日期的日报列表
                reports = self.reports_by_date[report_date]['reports']

                # 去重：检查是否已存在相同发送者的日报
                sender = report.get('sender', '未知')
                existing_report = None
                for idx, existing in enumerate(reports):
                    if existing.get('sender') == sender:
                        existing_report = idx
                        break

                # 添加/更新时间戳和日期
                report['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                report['date'] = report_date
                
                # 如果报告中有 message_id，记录它
                message_id = report.get('message_id', None)

                if existing_report is not None:
                    # 如果已存在，更新（覆盖）旧的日报
                    reports[existing_report] = report
                    logger.info(f"更新日报 - 发送者: {sender}, 日期: {report_date}, 当前共 {len(reports)} 条" + 
                               (f", message_id: {message_id}" if message_id else ""))
                else:
                    # 如果不存在，添加新日报
                    reports.append(report)
                    logger.info(f"添加日报成功 - 发送者: {sender}, 日期: {report_date}, 当前共 {len(reports)} 条" +
                               (f", message_id: {message_id}" if message_id else ""))

                # 保存到文件
                self._save_reports()

                return True

        except Exception as e:
            logger.error(f"添加日报失败: {str(e)}", exc_info=True)
            return False

    def get_all_reports(self, date: str = None) -> List[Dict]:
        """
        获取指定日期的所有日报

        Args:
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            List[Dict]: 日报列表
        """
        with self.lock:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')

            if date in self.reports_by_date:
                return self.reports_by_date[date]['reports'].copy()
            return []

    def get_report_count(self, date: str = None) -> int:
        """
        获取指定日期的日报数量

        Args:
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            int: 日报数量
        """
        with self.lock:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')

            if date in self.reports_by_date:
                return len(self.reports_by_date[date]['reports'])
            return 0

    def is_sent(self, date: str = None) -> bool:
        """
        检查指定日期的日报是否已发送

        Args:
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            bool: 是否已发送
        """
        with self.lock:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')

            if date in self.reports_by_date:
                return self.reports_by_date[date]['sent']
            return False

    def mark_as_sent(self, date: str = None) -> bool:
        """
        标记指定日期的日报为已发送

        Args:
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            bool: 是否标记成功
        """
        try:
            with self.lock:
                if date is None:
                    date = datetime.now().strftime('%Y-%m-%d')

                if date not in self.reports_by_date:
                    self.reports_by_date[date] = {
                        'reports': [],
                        'sent': False
                    }

                self.reports_by_date[date]['sent'] = True
                self._save_reports()
                logger.info(f"已标记 {date} 的日报为已发送")
                return True

        except Exception as e:
            logger.error(f"标记已发送失败: {str(e)}", exc_info=True)
            return False

    def remove_report_by_message_id(self, message_id: str) -> bool:
        """
        通过 message_id 删除日报

        Args:
            message_id: 消息ID

        Returns:
            bool: 是否删除成功
        """
        try:
            with self.lock:
                # 遍历所有日期的日报
                for date, data in self.reports_by_date.items():
                    reports = data['reports']
                    for idx, report in enumerate(reports):
                        if report.get('message_id') == message_id:
                            sender = report.get('sender', '未知')
                            reports.pop(idx)
                            self._save_reports()
                            logger.info(f"已删除撤回的日报 - 发送者: {sender}, 日期: {date}, message_id: {message_id}")
                            return True
                
                logger.warning(f"未找到 message_id 为 {message_id} 的日报")
                return False

        except Exception as e:
            logger.error(f"删除日报失败: {str(e)}", exc_info=True)
            return False

    def clear_reports(self, date: str = None) -> bool:
        """
        清空指定日期的日报

        Args:
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            bool: 是否清空成功
        """
        try:
            with self.lock:
                if date is None:
                    date = datetime.now().strftime('%Y-%m-%d')

                if date in self.reports_by_date:
                    del self.reports_by_date[date]
                    self._save_reports()
                    logger.info(f"已清空 {date} 的日报")
                return True

        except Exception as e:
            logger.error(f"清空日报失败: {str(e)}", exc_info=True)
            return False

    def _load_reports(self):
        """从文件加载日报数据"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # 兼容旧格式（单日期）
                    if 'date' in data and 'reports' in data:
                        # 旧格式：{'date': 'YYYY-MM-DD', 'reports': [...]}
                        date = data['date']
                        self.reports_by_date = {
                            date: {
                                'reports': data.get('reports', []),
                                'sent': data.get('sent', False)
                            }
                        }
                        logger.info(f"加载旧格式数据，转换为新格式: {date} - {len(data.get('reports', []))} 条")
                    else:
                        # 新格式：{'YYYY-MM-DD': {'reports': [...], 'sent': False}, ...}
                        self.reports_by_date = data
                        total_reports = sum(len(v['reports']) for v in self.reports_by_date.values())
                        logger.info(f"加载 {len(self.reports_by_date)} 个日期的日报，共 {total_reports} 条")
            else:
                logger.info("未找到历史日报文件，初始化空数据")
                self.reports_by_date = {}

        except Exception as e:
            logger.error(f"加载日报数据失败: {str(e)}", exc_info=True)
            self.reports_by_date = {}

    def _save_reports(self):
        """保存日报数据到文件"""
        try:
            # 直接保存新格式：{date: {'reports': [...], 'sent': False}}
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.reports_by_date, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存日报数据失败: {str(e)}", exc_info=True)


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    storage = DailyReportStorage("test_reports.json")

    # 添加测试日报
    test_report1 = {
        'sender': '张三',
        'tracking_issues': 'TSTAS-431、TSTAS-366',
        'work_content': '1、整理431相关的内容\n2、测试365相关的问题',
        'blocks': '无',
        'next_plan': 'TSTAS-437'
    }

    test_report2 = {
        'sender': '李四',
        'tracking_issues': 'TSTAS-436',
        'work_content': '1、调研app上架问题',
        'blocks': '无',
        'next_plan': 'TSTAS-421'
    }

    storage.add_report(test_report1)
    storage.add_report(test_report2)

    print(f"当前日报数量: {storage.get_report_count()}")
    print("\n所有日报:")
    for i, report in enumerate(storage.get_all_reports(), 1):
        print(f"\n{i}. {report['sender']}:")
        print(f"   跟踪问题: {report['tracking_issues']}")
        print(f"   时间: {report['timestamp']}")

    # 清理测试文件
    if os.path.exists("test_reports.json"):
        os.remove("test_reports.json")
