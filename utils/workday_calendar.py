#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作日日历管理器
支持中国法定节假日和调休的工作日判断
"""

import json
import logging
import os
import requests
from datetime import datetime
from typing import Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class WorkdayCalendar:
    """工作日日历管理器"""
    
    # 节假日API地址
    API_URL = "http://timor.tech/api/holiday/year/{year}"
    
    def __init__(self, 
                 cache_file: str = "data/holidays_cache.json",
                 config_file: str = "config/holidays.json"):
        """
        初始化工作日日历
        
        Args:
            cache_file: 缓存文件路径
            config_file: 本地配置文件路径（降级方案）
        """
        self.cache_file = cache_file
        self.config_file = config_file
        self.holidays_data: Dict[str, Dict] = {}
        self.lock = Lock()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        if self.config_file:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # 加载缓存
        self._load_cache()
    
    def is_workday(self, date: Optional[str] = None) -> bool:
        """
        判断指定日期是否为工作日
        
        Args:
            date: 日期字符串 YYYY-MM-DD，None表示今天
            
        Returns:
            bool: True表示工作日，False表示休息日
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 解析日期
        try:
            dt = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            logger.error(f"日期格式错误: {date}")
            return False
        
        year = dt.year
        
        # 确保有当年的数据
        if str(year) not in self.holidays_data:
            self.refresh_cache(year)
        
        # 检查是否在节假日数据中
        year_data = self.holidays_data.get(str(year), {})
        if date in year_data:
            return year_data[date].get('is_workday', False)
        
        # 如果不在数据中，按周末规则判断
        weekday = dt.weekday()
        return weekday < 5  # 0-4 是周一到周五
    
    def get_holidays(self, year: Optional[int] = None) -> Dict:
        """
        获取指定年份的节假日数据
        
        Args:
            year: 年份，None表示当年
            
        Returns:
            dict: {date: {name, is_workday, type}}
        """
        if year is None:
            year = datetime.now().year
        
        # 确保有数据
        if str(year) not in self.holidays_data:
            self.refresh_cache(year)
        
        return self.holidays_data.get(str(year), {})
    
    def refresh_cache(self, year: Optional[int] = None) -> bool:
        """
        刷新缓存（从API或本地配置）
        
        Args:
            year: 年份，None表示当年
            
        Returns:
            bool: 是否成功
        """
        if year is None:
            year = datetime.now().year
        
        with self.lock:
            # 首先尝试从API获取
            if self._fetch_from_api(year):
                logger.info(f"成功从API获取{year}年节假日数据")
                self._save_cache()
                return True
            
            # API失败，尝试从本地配置加载
            logger.warning(f"API获取失败，尝试从本地配置加载")
            if self._load_from_config(year):
                logger.info(f"成功从本地配置加载{year}年节假日数据")
                self._save_cache()  # 保存到缓存文件
                return True
            
            # 都失败了
            logger.error(f"无法获取{year}年节假日数据")
            return False
    
    def _fetch_from_api(self, year: int) -> bool:
        """从API获取节假日数据"""
        try:
            url = self.API_URL.format(year=year)
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"API返回错误: {response.status_code}")
                return False
            
            data = response.json()
            
            # timor.tech API 返回格式：
            # {
            #   "code": 0,
            #   "holiday": {
            #     "01-01": {"holiday": true, "name": "元旦", "wage": 3, "date": "2026-01-01"}
            #   }
            # }
            
            if data.get('code') != 0:
                logger.error(f"API返回错误代码: {data.get('code')}")
                return False
            
            holiday_data = data.get('holiday', {})
            
            # 转换格式
            year_holidays = {}
            for day_key, day_info in holiday_data.items():
                date_str = day_info.get('date')
                if not date_str:
                    continue
                
                # 判断是否为工作日
                # holiday=true 表示休息，holiday=false 或不存在表示工作日
                is_holiday = day_info.get('holiday', False)
                
                year_holidays[date_str] = {
                    'name': day_info.get('name', ''),
                    'is_workday': not is_holiday,
                    'type': 'holiday' if is_holiday else 'workday'
                }
            
            self.holidays_data[str(year)] = year_holidays
            return True
            
        except requests.RequestException as e:
            logger.error(f"API请求失败: {e}")
            return False
        except Exception as e:
            logger.error(f"解析API数据失败: {e}")
            return False
    
    def _load_from_config(self, year: int) -> bool:
        """从本地配置加载"""
        try:
            if not os.path.exists(self.config_file):
                return False
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if str(year) in config_data:
                self.holidays_data[str(year)] = config_data[str(year)]
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"从本地配置加载失败: {e}")
            return False
    
    def _load_cache(self) -> bool:
        """加载缓存文件"""
        try:
            if not os.path.exists(self.cache_file):
                return False
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.holidays_data = json.load(f)
            
            logger.info(f"成功加载缓存，包含{len(self.holidays_data)}年的数据")
            return True
            
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return False
    
    def _save_cache(self) -> bool:
        """保存到缓存文件"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.holidays_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"缓存已保存到 {self.cache_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
            return False
