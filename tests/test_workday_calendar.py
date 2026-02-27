#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作日日历模块测试
"""

import pytest
import os
import json
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock
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
        # 2026-02-06 (周五) 春节前调休为工作日
        # 2026-02-14 (周六) 春节后调休为工作日
        assert self.calendar.is_workday('2026-02-06') == True
        assert self.calendar.is_workday('2026-02-14') == True
    
    def test_cache_creation(self):
        """测试缓存文件创建"""
        self.calendar.refresh_cache(2026)
        assert os.path.exists(self.test_cache_file)
    
    def test_get_holidays_for_year(self):
        """测试获取年度节假日"""
        holidays = self.calendar.get_holidays(2026)
        assert isinstance(holidays, dict)
        assert '2026-01-01' in holidays  # 元旦应该在列表中


class TestWorkdayCalendarWithMocks:
    """工作日日历模拟测试类 - 使用mock隔离外部依赖"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.test_cache_file = 'data/test_mocked_cache.json'
        self.test_config_file = 'config/test_holidays.json'
    
    def teardown_method(self):
        """每个测试后的清理"""
        if os.path.exists(self.test_cache_file):
            os.remove(self.test_cache_file)
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
    
    @patch('utils.workday_calendar.requests.get')
    def test_fetch_from_api_success(self, mock_get):
        """测试API获取成功"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'holiday': {
                '01-01': {
                    'date': '2026-01-01',
                    'name': '元旦',
                    'holiday': True
                },
                '02-06': {
                    'date': '2026-02-06',
                    'name': '春节调休',
                    'holiday': False
                }
            }
        }
        mock_get.return_value = mock_response
        
        calendar = WorkdayCalendar(cache_file=self.test_cache_file)
        result = calendar._fetch_from_api(2026)
        
        assert result == True
        assert '2026' in calendar.holidays_data
        assert '2026-01-01' in calendar.holidays_data['2026']
        assert calendar.holidays_data['2026']['2026-01-01']['is_workday'] == False
        assert calendar.holidays_data['2026']['2026-02-06']['is_workday'] == True
    
    @patch('utils.workday_calendar.requests.get')
    def test_fetch_from_api_retry_on_failure(self, mock_get):
        """测试API失败时的重试逻辑"""
        # 模拟前两次失败，第三次成功
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'code': 0,
            'holiday': {
                '01-01': {
                    'date': '2026-01-01',
                    'name': '元旦',
                    'holiday': True
                }
            }
        }
        
        mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
        
        calendar = WorkdayCalendar(cache_file=self.test_cache_file)
        result = calendar._fetch_from_api(2026)
        
        assert result == True
        assert mock_get.call_count == 3  # 应该调用3次
    
    @patch('utils.workday_calendar.requests.get')
    def test_fetch_from_api_all_retries_fail(self, mock_get):
        """测试所有重试都失败"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        calendar = WorkdayCalendar(cache_file=self.test_cache_file)
        result = calendar._fetch_from_api(2026)
        
        assert result == False
        assert mock_get.call_count == 3  # 应该重试3次
    
    @patch('utils.workday_calendar.requests.get')
    def test_refresh_cache_fallback_to_config(self, mock_get):
        """测试API失败后降级到本地配置"""
        # 模拟API失败
        mock_get.side_effect = Exception("Network error")
        
        # 创建本地配置文件
        test_config_data = {
            '2026': {
                '2026-01-01': {
                    'name': '元旦',
                    'is_workday': False,
                    'type': 'holiday'
                }
            }
        }
        os.makedirs(os.path.dirname(self.test_config_file), exist_ok=True)
        with open(self.test_config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config_data, f)
        
        calendar = WorkdayCalendar(
            cache_file=self.test_cache_file,
            config_file=self.test_config_file
        )
        result = calendar.refresh_cache(2026)
        
        assert result == True
        assert '2026' in calendar.holidays_data
        assert '2026-01-01' in calendar.holidays_data['2026']
    
    def test_invalid_date_format(self):
        """测试无效日期格式"""
        calendar = WorkdayCalendar(cache_file=self.test_cache_file)
        
        # 无效日期格式应该返回False
        assert calendar.is_workday('2026/01/01') == False
        assert calendar.is_workday('invalid-date') == False
        assert calendar.is_workday('2026-13-01') == False
    
    def test_missing_cache_file(self):
        """测试缺失缓存文件的情况"""
        # 确保缓存文件不存在
        non_existent_cache = 'data/non_existent_cache.json'
        if os.path.exists(non_existent_cache):
            os.remove(non_existent_cache)
        
        calendar = WorkdayCalendar(cache_file=non_existent_cache)
        
        # 应该能正常工作，fallback到周末判断
        assert calendar.is_workday('2026-02-02') == True  # 周一
        assert calendar.is_workday('2026-02-07') == False  # 周六
    
    def test_missing_config_file(self):
        """测试缺失配置文件的情况"""
        non_existent_config = 'config/non_existent_config.json'
        if os.path.exists(non_existent_config):
            os.remove(non_existent_config)
        
        calendar = WorkdayCalendar(
            cache_file=self.test_cache_file,
            config_file=non_existent_config
        )
        
        # _load_from_config应该返回False
        result = calendar._load_from_config(2026)
        assert result == False
    
    def test_year_boundary_cases(self):
        """测试年份边界情况"""
        calendar = WorkdayCalendar(cache_file=self.test_cache_file)

        # 注入跨年测试数据，避免依赖外部API与实时节假日数据
        calendar.holidays_data['2026'] = {
            '2026-12-31': {
                'name': '年末工作日',
                'is_workday': True,
                'type': 'workday'
            }
        }
        calendar.holidays_data['2027'] = {
            '2027-01-01': {
                'name': '元旦',
                'is_workday': False,
                'type': 'holiday'
            }
        }

        # 测试年末和年初
        assert calendar.is_workday('2026-12-31') == True
        assert calendar.is_workday('2027-01-01') == False
    
    @patch('utils.workday_calendar.requests.get')
    def test_api_invalid_json_response(self, mock_get):
        """测试API返回无效JSON"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        calendar = WorkdayCalendar(cache_file=self.test_cache_file)
        result = calendar._fetch_from_api(2026)
        
        assert result == False
    
    def test_cache_load_and_save(self):
        """测试缓存的加载和保存"""
        calendar = WorkdayCalendar(cache_file=self.test_cache_file)
        
        # 手动设置数据
        calendar.holidays_data = {
            '2026': {
                '2026-01-01': {
                    'name': '元旦',
                    'is_workday': False,
                    'type': 'holiday'
                }
            }
        }
        
        # 保存缓存
        result = calendar._save_cache()
        assert result == True
        assert os.path.exists(self.test_cache_file)
        
        # 创建新实例并加载缓存
        calendar2 = WorkdayCalendar(cache_file=self.test_cache_file)
        assert '2026' in calendar2.holidays_data
        assert '2026-01-01' in calendar2.holidays_data['2026']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

