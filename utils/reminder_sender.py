#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报提醒发送器
用于在指定时间检查并提醒未提交日报的人
"""

import logging
import json
import os
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from typing import List, Set

logger = logging.getLogger(__name__)


class ReminderSender:
    """日报提醒发送器"""

    def __init__(self, app_id: str, app_secret: str, required_users: List[str] = None):
        """
        初始化提醒发送器

        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            required_users: 需要提交日报的用户ID列表（为None或空表示所有用户）
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.required_users = required_users or []
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .build()

    def get_all_users(self, user_names_file: str = 'config/user_names.json') -> dict:
        """
        获取所有需要提交日报的用户

        Args:
            user_names_file: 用户姓名映射文件路径

        Returns:
            dict: 用户ID到姓名的映射 {user_id: name}
        """
        try:
            if os.path.exists(user_names_file):
                with open(user_names_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_users = data.get('映射', {})
                    
                    # 优先使用配置文件中的日报白名单
                    whitelist = data.get('日报白名单', [])
                    if whitelist:
                        filtered_users = {
                            user_id: name.replace('（领导）', '')  # 去除标记
                            for user_id, name in all_users.items() 
                            if user_id in whitelist
                        }
                        logger.info(f"使用日报白名单，共 {len(filtered_users)} 人需要提交日报")
                        return filtered_users
                    
                    # 如果没有白名单但配置了required_users，使用required_users
                    if self.required_users:
                        filtered_users = {
                            user_id: name.replace('（领导）', '') 
                            for user_id, name in all_users.items() 
                            if user_id in self.required_users
                        }
                        logger.info(f"使用配置的必需用户列表，过滤后: {len(filtered_users)} 人")
                        return filtered_users
                    
                    # 去除所有姓名中的标记
                    clean_users = {
                        user_id: name.replace('（领导）', '')
                        for user_id, name in all_users.items()
                    }
                    return clean_users
            else:
                logger.warning(f"用户姓名映射文件不存在: {user_names_file}")
                return {}
        except Exception as e:
            logger.error(f"读取用户姓名映射文件失败: {str(e)}", exc_info=True)
            return {}

    def get_submitted_users(self, reports: List[dict]) -> Set[str]:
        """
        获取已提交日报的用户姓名集合

        Args:
            reports: 日报列表

        Returns:
            Set[str]: 已提交日报的用户姓名集合
        """
        return {report.get('sender', '') for report in reports if report.get('sender')}

    def find_missing_users(self, all_users: dict, submitted_users: Set[str]) -> List[tuple]:
        """
        找出未提交日报的用户

        Args:
            all_users: 所有用户映射 {user_id: name}
            submitted_users: 已提交日报的用户姓名集合

        Returns:
            List[tuple]: 未提交日报的用户列表 [(user_id, name), ...]
        """
        missing_users = []
        for user_id, name in all_users.items():
            if name not in submitted_users:
                missing_users.append((user_id, name))

        return missing_users

    def send_reminder(self, chat_id: str, missing_users: List[tuple]) -> bool:
        """
        发送提醒消息到群组，@未提交日报的人

        Args:
            chat_id: 群组ID
            missing_users: 未提交日报的用户列表 [(user_id, name), ...]

        Returns:
            bool: 是否发送成功
        """
        try:
            if not missing_users:
                logger.info("所有人都已提交日报，无需发送提醒")
                return True

            # 构建提醒消息
            # 飞书富文本消息格式
            at_elements = []
            names = []

            for user_id, name in missing_users:
                # 添加@用户元素
                at_elements.append({
                    "tag": "at",
                    "user_id": user_id
                })
                at_elements.append({
                    "tag": "text",
                    "text": " "
                })
                names.append(name)

            # 构建完整的消息内容
            content_elements = [
                {
                    "tag": "text",
                    "text": "📝 日报提醒\n\n以下同学还未提交今日日报，请尽快提交：\n\n"
                }
            ]
            content_elements.extend(at_elements)
            content_elements.append({
                "tag": "text",
                "text": f"\n\n还有 {len(missing_users)} 人未提交，请及时补充！"
            })

            # 构建post消息
            post_content = {
                "zh_cn": {
                    "title": "⏰ 日报提醒",
                    "content": [content_elements]
                }
            }

            # 构建请求
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("post")
                    .content(json.dumps(post_content))
                    .build()) \
                .build()

            # 发送消息
            response = self.client.im.v1.message.create(request)

            if response.success():
                logger.info(f"✅ 日报提醒发送成功 - 共提醒 {len(missing_users)} 人: {', '.join(names)}")
                return True
            else:
                logger.error(f"❌ 日报提醒发送失败: {response.msg}")
                return False

        except Exception as e:
            logger.error(f"发送日报提醒失败: {str(e)}", exc_info=True)
            return False

    def check_and_remind(self, chat_id: str, reports: List[dict], 
                        user_names_file: str = 'config/user_names.json') -> bool:
        """
        检查并发送提醒（主方法）

        Args:
            chat_id: 群组ID
            reports: 已收集的日报列表
            user_names_file: 用户姓名映射文件路径

        Returns:
            bool: 是否成功
        """
        try:
            logger.info("=" * 60)
            logger.info("🔔 开始检查日报提交情况...")

            # 1. 获取所有需要提交日报的用户
            all_users = self.get_all_users(user_names_file)
            if not all_users:
                logger.warning("未找到需要提交日报的用户列表")
                return False

            logger.info(f"应提交日报人数: {len(all_users)}")
            logger.info(f"应提交人员: {', '.join(all_users.values())}")

            # 2. 获取已提交日报的用户
            submitted_users = self.get_submitted_users(reports)
            logger.info(f"已提交日报人数: {len(submitted_users)}")
            if submitted_users:
                logger.info(f"已提交人员: {', '.join(submitted_users)}")

            # 3. 找出未提交的用户
            missing_users = self.find_missing_users(all_users, submitted_users)

            if not missing_users:
                logger.info("✅ 所有人都已提交日报，无需提醒")
                logger.info("=" * 60)
                return True

            logger.info(f"⚠️  未提交日报人数: {len(missing_users)}")
            logger.info(f"未提交人员: {', '.join([name for _, name in missing_users])}")

            # 4. 发送提醒消息
            success = self.send_reminder(chat_id, missing_users)

            logger.info("=" * 60)
            return success

        except Exception as e:
            logger.error(f"检查并提醒失败: {str(e)}", exc_info=True)
            return False


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # 测试数据
    test_reports = [
        {'sender': '秦意军'},
        {'sender': '李尚璋'},
        {'sender': '孙康'}
    ]

    # 创建提醒发送器（需要真实的APP_ID和APP_SECRET）
    reminder = ReminderSender("your_app_id", "your_app_secret")

    # 获取所有用户
    all_users = reminder.get_all_users()
    print(f"所有用户: {all_users}")

    # 获取已提交的用户
    submitted = reminder.get_submitted_users(test_reports)
    print(f"已提交: {submitted}")

    # 找出未提交的用户
    missing = reminder.find_missing_users(all_users, submitted)
    print(f"未提交: {missing}")
