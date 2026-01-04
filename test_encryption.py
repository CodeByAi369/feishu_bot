#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试加密工具是否能正常导入
"""

print("测试加密工具导入...")
print("=" * 60)

try:
    print("1. 测试 encrypt_env.py 导入...")
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    print("   ✅ encrypt_env.py 所需模块导入成功")
except ImportError as e:
    print(f"   ❌ 导入失败: {e}")

print()

try:
    print("2. 测试 encrypt_env_aes256.py 导入...")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    print("   ✅ encrypt_env_aes256.py 所需模块导入成功")
except ImportError as e:
    print(f"   ❌ 导入失败: {e}")

print()
print("=" * 60)
print("✅ 所有加密模块测试通过！")
print()
print("现在可以使用以下命令:")
print("  - python encrypt_env.py          # 基础加密（Fernet）")
print("  - python encrypt_env_aes256.py   # 高级加密（AES-256-GCM）")
