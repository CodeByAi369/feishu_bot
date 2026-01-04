#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全启动脚本 - 使用内存解密
直接启动机器人，配置在内存中解密，不生成 .env 文件
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 首先加载加密的环境变量到内存
from secure_loader import load_encrypted_env

print("=" * 70)
print("🔐 飞书机器人 - 安全启动模式")
print("=" * 70)
print()

# 加载加密配置（不生成文件）
if not load_encrypted_env('.env.encrypted'):
    print("❌ 配置加载失败")
    sys.exit(1)

# 确保 .env 文件不存在
if os.path.exists('.env'):
    print("⚠️  检测到 .env 文件存在，正在删除...")
    os.remove('.env')
    print("✅ .env 文件已删除（使用内存配置）")
    print()

# 导入并启动主程序
print("启动飞书机器人...")
print("=" * 70)
print()

# 标记：使用内存中的环境变量，跳过 .env 文件检查
os.environ['USE_MEMORY_ENV'] = 'true'

# 直接运行 app_ws.py 的主程序
# 使用 runpy 模块来执行，这样 __name__ == '__main__' 会生效
import runpy
runpy.run_path('app_ws.py', run_name='__main__')
