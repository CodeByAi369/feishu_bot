#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.env 文件加密/解密工具
使用密码加密 .env 文件，防止敏感信息泄露
"""

import os
import sys
import getpass
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

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

def encrypt_file(input_file: str, output_file: str, password: str):
    """加密文件"""
    # 生成随机盐值
    salt = os.urandom(16)

    # 派生密钥
    cipher = derive_key(password, salt)

    # 读取原文件
    with open(input_file, 'rb') as f:
        data = f.read()

    # 加密数据
    encrypted = cipher.encrypt(data)

    # 保存：盐值 + 加密数据
    with open(output_file, 'wb') as f:
        f.write(salt + encrypted)

    print(f"✅ 文件已加密: {output_file}")

def decrypt_file(input_file: str, output_file: str, password: str):
    """解密文件"""
    # 读取加密文件
    with open(input_file, 'rb') as f:
        data = f.read()

    # 提取盐值和加密数据
    salt = data[:16]
    encrypted = data[16:]

    # 派生密钥
    cipher = derive_key(password, salt)

    try:
        # 解密数据
        decrypted = cipher.decrypt(encrypted)

        # 保存解密文件
        with open(output_file, 'wb') as f:
            f.write(decrypted)

        print(f"✅ 文件已解密: {output_file}")
        return True
    except Exception as e:
        print(f"❌ 解密失败: {str(e)}")
        print("可能是密码错误")
        return False

def main():
    print("=" * 60)
    print(".env 文件加密/解密工具")
    print("=" * 60)
    print()

    # 选择操作
    print("请选择操作:")
    print("1. 加密 .env 文件")
    print("2. 解密 .env.encrypted 文件")
    print("3. 退出")
    print()

    choice = input("请输入选项 (1/2/3): ").strip()

    if choice == "1":
        # 加密操作
        if not os.path.exists('.env'):
            print("❌ 错误: .env 文件不存在")
            return

        print()
        print("加密 .env 文件")
        print("请设置加密密码（建议使用强密码）:")
        password1 = getpass.getpass("密码: ")
        password2 = getpass.getpass("确认密码: ")

        if password1 != password2:
            print("❌ 两次密码不一致")
            return

        if len(password1) < 6:
            print("❌ 密码太短，至少需要6个字符")
            return

        # 加密文件
        encrypt_file('.env', '.env.encrypted', password1)

        print()
        print("⚠️  重要提示:")
        print("1. 已生成加密文件: .env.encrypted")
        print("2. 请妥善保管密码，忘记密码将无法恢复")
        print("3. 建议删除原始 .env 文件:")

        delete = input("\n是否删除原始 .env 文件？(y/n): ").strip().lower()
        if delete == 'y':
            os.remove('.env')
            print("✅ 原始 .env 文件已删除")
        else:
            print("⚠️  原始 .env 文件仍然存在，请手动删除")

    elif choice == "2":
        # 解密操作
        if not os.path.exists('.env.encrypted'):
            print("❌ 错误: .env.encrypted 文件不存在")
            return

        if os.path.exists('.env'):
            print("⚠️  警告: .env 文件已存在")
            overwrite = input("是否覆盖？(y/n): ").strip().lower()
            if overwrite != 'y':
                print("操作已取消")
                return

        print()
        print("解密 .env.encrypted 文件")
        password = getpass.getpass("请输入密码: ")

        # 解密文件
        success = decrypt_file('.env.encrypted', '.env', password)

        if success:
            print()
            print("✅ 解密成功！现在可以运行程序了")

    elif choice == "3":
        print("退出")
        return

    else:
        print("❌ 无效的选项")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
