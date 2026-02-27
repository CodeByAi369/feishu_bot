#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试提醒器工作日集成
"""

from unittest.mock import Mock, patch
from utils.reminder_sender import ReminderSender


class TestReminderWithWorkday:
    """测试提醒器工作日功能"""

    def test_skip_reminder_on_weekend(self):
        """测试周末跳过提醒"""
        sender = ReminderSender('test_app_id', 'test_secret')

        with patch('utils.reminder_sender.WorkdayCalendar') as mock_calendar:
            mock_instance = Mock()
            mock_instance.is_workday.return_value = False
            mock_calendar.return_value = mock_instance

            result = sender.check_and_send_reminders(
                chat_id='test_chat_id',
                check_date='2026-02-08',
                reports=[]
            )
            assert result == []

    def test_send_reminder_on_workday(self):
        """测试工作日发送提醒"""
        sender = ReminderSender('test_app_id', 'test_secret')

        with patch('utils.reminder_sender.WorkdayCalendar') as mock_calendar:
            mock_instance = Mock()
            mock_instance.is_workday.return_value = True
            mock_calendar.return_value = mock_instance

            with patch.object(sender, 'get_all_users', return_value={'u1': '张三', 'u2': '李四'}):
                with patch.object(sender, 'send_reminder', return_value=True) as mock_send:
                    reports = [{'sender': '张三'}]
                    reminded = sender.check_and_send_reminders(
                        chat_id='test_chat_id',
                        check_date='2026-02-09',
                        reports=reports
                    )

                    assert reminded == ['u2']
                    mock_send.assert_called_once()
