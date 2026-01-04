#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
休假管理器
用于管理团队成员的休假状态
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Set
from threading import Lock

logger = logging.getLogger(__name__)


class VacationManager:
    """休假管理器"""

    def __init__(self, storage_file: str = "data/vacations.json"):
        """
        初始化休假管理器

        Args:
            storage_file: 休假数据存储文件路径
        """
        self.storage_file = storage_file
        self.vacations = {}  # {date: [user_names]}
        self.lock = Lock()

        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)

        # 加载已有数据
        self._load_vacations()

    def set_vacation(self, user_name: str, date: str = None) -> bool:
        """
        设置某人休假

        Args:
            user_name: 用户姓名
            date: 休假日期 (YYYY-MM-DD)，默认为今天

        Returns:
            bool: 是否设置成功
        """
        try:
            with self.lock:
                if date is None:
                    date = datetime.now().strftime('%Y-%m-%d')

                # 确保日期键存在
                if date not in self.vacations:
                    self.vacations[date] = []

                # 添加休假（避免重复）
                if user_name not in self.vacations[date]:
                    self.vacations[date].append(user_name)
                    self._save_vacations()
                    logger.info(f"✅ 已设置休假 - {user_name} ({date})")
                    return True
                else:
                    logger.info(f"💡 {user_name} 在 {date} 已经设置过休假")
                    return True

        except Exception as e:
            logger.error(f"设置休假失败: {str(e)}", exc_info=True)
            return False

    def cancel_vacation(self, user_name: str, date: str = None) -> bool:
        """
        取消某人的休假

        Args:
            user_name: 用户姓名
            date: 休假日期 (YYYY-MM-DD)，默认为今天

        Returns:
            bool: 是否取消成功
        """
        try:
            with self.lock:
                if date is None:
                    date = datetime.now().strftime('%Y-%m-%d')

                if date in self.vacations and user_name in self.vacations[date]:
                    self.vacations[date].remove(user_name)

                    # 如果该日期没有休假人员了，删除该日期键
                    if not self.vacations[date]:
                        del self.vacations[date]

                    self._save_vacations()
                    logger.info(f"✅ 已取消休假 - {user_name} ({date})")
                    return True
                else:
                    logger.info(f"💡 {user_name} 在 {date} 没有设置休假")
                    return False

        except Exception as e:
            logger.error(f"取消休假失败: {str(e)}", exc_info=True)
            return False

    def is_on_vacation(self, user_name: str, date: str = None) -> bool:
        """
        检查某人是否在休假

        Args:
            user_name: 用户姓名
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            bool: 是否在休假
        """
        with self.lock:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')

            return date in self.vacations and user_name in self.vacations[date]

    def get_vacation_users(self, date: str = None) -> List[str]:
        """
        获取某天的休假人员列表

        Args:
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            List[str]: 休假人员姓名列表
        """
        with self.lock:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')

            return self.vacations.get(date, []).copy()

    def get_all_vacations(self) -> Dict[str, List[str]]:
        """
        获取所有休假数据

        Returns:
            Dict[str, List[str]]: 休假数据 {日期: [姓名列表]}
        """
        with self.lock:
            return self.vacations.copy()

    def _load_vacations(self):
        """从文件加载休假数据"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.vacations = json.load(f)
                    logger.info(f"加载休假数据: {len(self.vacations)} 个日期")
            else:
                logger.info("未找到休假数据文件，初始化空数据")
                self.vacations = {}

        except Exception as e:
            logger.error(f"加载休假数据失败: {str(e)}", exc_info=True)
            self.vacations = {}

    def _save_vacations(self):
        """保存休假数据到文件"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.vacations, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存休假数据失败: {str(e)}", exc_info=True)


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    manager = VacationManager("test_vacations.json")

    # 测试设置休假
    manager.set_vacation("张三", "2025-10-21")
    manager.set_vacation("李四", "2025-10-21")
    manager.set_vacation("王五", "2025-10-22")

    # 测试查询
    print(f"张三今天是否休假: {manager.is_on_vacation('张三', '2025-10-21')}")
    print(f"今天休假人员: {manager.get_vacation_users('2025-10-21')}")

    # 测试取消休假
    manager.cancel_vacation("李四", "2025-10-21")
    print(f"取消后今天休假人员: {manager.get_vacation_users('2025-10-21')}")

    # 清理测试文件
    if os.path.exists("test_vacations.json"):
        os.remove("test_vacations.json")
