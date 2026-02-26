#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作日日历模块测试
"""

import pytest
import os
import json
from datetime import datetime
from utils.workday_calendar import WorkdayCalendar


class TestWorkdayCalendar:
    """工作日日历测试类"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.test_cache_file = 'data/test_holidays_cache.json'
        self.calendar = WorkdayCalendar(cache_file=self.test_cache_file)
    
    def teardown_method(self):
        """每个测试后的清理"""
        if os.path.exists(self.test_cache_file):
            os.remove(self.test_cache_file)
    
    def test_is_workday_monday(self):
        """测试周一是工作日"""
        # 2026-02-02 是周一
        assert self.calendar.is_workday('2026-02-02') == True
    
    def test_is_workday_saturday(self):
        """测试周六不是工作日"""
        # 2026-02-07 是周六
        assert self.calendar.is_workday('2026-02-07') == False
    
    def test_is_workday_holiday(self):
        """测试法定节假日不是工作日"""
        # 测试数据：2026-01-01 元旦
        assert self.calendar.is_workday('2026-01-01') == False
    
    def test_is_workday_adjusted_workday(self):
        """测试调休工作日"""
        # 测试数据：如果某个周末调休为工作日
        # 需要根据实际2026年数据调整
        pass
    
    def test_cache_creation(self):
        """测试缓存文件创建"""
        self.calendar.refresh_cache(2026)
        assert os.path.exists(self.test_cache_file)
    
    def test_get_holidays_for_year(self):
        """测试获取年度节假日"""
        holidays = self.calendar.get_holidays(2026)
        assert isinstance(holidays, dict)
        assert '2026-01-01' in holidays  # 元旦应该在列表中


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
