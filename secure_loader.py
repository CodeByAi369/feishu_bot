#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存解密启动器 - 安全版本
直接在内存中解密配置，不生成 .env 文件
"""

import os
import sys
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


def derive_key(password: str, salt: bytes) -> Fernet:
    """从密码派生加密密钥"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return Fernet(key)


def decrypt_to_memory(encrypted_file: str, password: str) -> dict:
    """
    解密配置文件到内存，返回环境变量字典
    不生成实际的 .env 文件
    """
    # 读取加密文件
    with open(encrypted_file, 'rb') as f:
        data = f.read()

    # 提取盐值和加密数据
    salt = data[:16]
    encrypted = data[16:]

    # 派生密钥
    cipher = derive_key(password, salt)

    try:
        # 解密数据
        decrypted = cipher.decrypt(encrypted)
        
        # 解析环境变量
        env_vars = {}
        for line in decrypted.decode('utf-8').splitlines():
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            # 解析 KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # 处理值中的注释（去除 # 后面的内容）
                if '#' in value:
                    value = value.split('#')[0].strip()
                
                env_vars[key] = value
        
        return env_vars

    except Exception as e:
        print(f"❌ 解密失败: {str(e)}")
        print("可能是密码错误")
        return None


def load_encrypted_env(encrypted_file: str = '.env.encrypted'):
    """
    加载加密的环境变量到系统环境
    """
    if not os.path.exists(encrypted_file):
        print(f"❌ 加密文件不存在: {encrypted_file}")
        print("请先运行 encrypt_env.py 加密 .env 文件")
        sys.exit(1)

    print("🔐 安全启动模式")
    print("=" * 60)
    print("环境变量将在内存中解密，不会生成 .env 文件")
    print("=" * 60)
    print()

    # 获取密码
    password = getpass.getpass("请输入解密密码: ")

    # 解密到内存
    print("正在解密...")
    env_vars = decrypt_to_memory(encrypted_file, password)

    if env_vars is None:
        sys.exit(1)

    # 将环境变量加载到系统环境
    for key, value in env_vars.items():
        os.environ[key] = value

    print(f"✅ 成功加载 {len(env_vars)} 个环境变量到内存")
    print("配置已安全加载，未生成任何文件")
    print("=" * 60)
    print()

    return True


if __name__ == '__main__':
    # 测试解密
    if load_encrypted_env():
        print("测试：读取环境变量")
        print(f"FEISHU_APP_ID: {os.environ.get('FEISHU_APP_ID', '未设置')[:10]}...")
        print(f"SMTP_USER: {os.environ.get('SMTP_USER', '未设置')}")
