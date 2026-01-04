#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.env 文件加密/解密工具 - AES-256-GCM版本
使用 AES-256-GCM 模式加密，提供最高级别的安全性
"""

import os
import sys
import getpass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def derive_key_256(password: str, salt: bytes) -> bytes:
    """从密码派生AES-256密钥（32字节）"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # AES-256需要32字节密钥
        salt=salt,
        iterations=200000,  # 更高的迭代次数，更安全
    )
    return kdf.derive(password.encode('utf-8'))

def encrypt_file_aes256(input_file: str, output_file: str, password: str):
    """使用AES-256-GCM加密文件"""
    # 生成随机盐值（16字节）
    salt = os.urandom(16)

    # 派生AES-256密钥
    key = derive_key_256(password, salt)

    # 创建AES-GCM加密器
    aesgcm = AESGCM(key)

    # 生成随机nonce（12字节，GCM推荐）
    nonce = os.urandom(12)

    # 读取原文件
    with open(input_file, 'rb') as f:
        plaintext = f.read()

    # 加密数据（GCM模式自动添加认证标签）
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # 保存：盐值(16) + nonce(12) + 密文+认证标签
    with open(output_file, 'wb') as f:
        f.write(salt + nonce + ciphertext)

    print(f"✅ 文件已加密 (AES-256-GCM): {output_file}")
    print(f"   - 盐值长度: {len(salt)} 字节")
    print(f"   - Nonce长度: {len(nonce)} 字节")
    print(f"   - 加密后大小: {len(ciphertext)} 字节")

def decrypt_file_aes256(input_file: str, output_file: str, password: str):
    """使用AES-256-GCM解密文件"""
    # 读取加密文件
    with open(input_file, 'rb') as f:
        data = f.read()

    # 提取盐值、nonce和密文
    salt = data[:16]
    nonce = data[16:28]
    ciphertext = data[28:]

    # 派生AES-256密钥
    key = derive_key_256(password, salt)

    # 创建AES-GCM解密器
    aesgcm = AESGCM(key)

    try:
        # 解密并验证（GCM会自动验证认证标签）
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        # 保存解密文件
        with open(output_file, 'wb') as f:
            f.write(plaintext)

        print(f"✅ 文件已解密: {output_file}")
        print(f"   - 解密后大小: {len(plaintext)} 字节")
        return True

    except Exception as e:
        print(f"❌ 解密失败: {str(e)}")
        print("可能原因:")
        print("  1. 密码错误")
        print("  2. 文件已被篡改")
        print("  3. 文件损坏")
        return False

def get_file_info(filename: str):
    """显示加密文件信息"""
    if not os.path.exists(filename):
        print(f"❌ 文件不存在: {filename}")
        return

    with open(filename, 'rb') as f:
        data = f.read()

    print(f"\n文件信息: {filename}")
    print(f"  - 总大小: {len(data)} 字节")

    if len(data) >= 28:
        print(f"  - 盐值: {data[:16].hex()}")
        print(f"  - Nonce: {data[16:28].hex()}")
        print(f"  - 密文大小: {len(data[28:])} 字节")
        print(f"  - 加密算法: AES-256-GCM")
        print(f"  - 密钥派生: PBKDF2-SHA256 (200,000 iterations)")

def main():
    print("=" * 70)
    print(".env 文件加密/解密工具 - AES-256-GCM版本")
    print("=" * 70)
    print()
    print("加密参数:")
    print("  - 算法: AES-256-GCM")
    print("  - 密钥长度: 256 bits (32 bytes)")
    print("  - 密钥派生: PBKDF2-SHA256 with 200,000 iterations")
    print("  - 认证: GCM内置认证（防篡改）")
    print()

    # 选择操作
    print("请选择操作:")
    print("1. 加密 .env 文件 (AES-256-GCM)")
    print("2. 解密 .env.aes256 文件")
    print("3. 查看加密文件信息")
    print("4. 退出")
    print()

    choice = input("请输入选项 (1/2/3/4): ").strip()

    if choice == "1":
        # 加密操作
        if not os.path.exists('.env'):
            print("❌ 错误: .env 文件不存在")
            return

        print()
        print("使用 AES-256-GCM 加密 .env 文件")
        print("⚠️  注意：此加密方案比Fernet更强（256位密钥 vs 128位）")
        print()
        print("请设置加密密码（建议使用强密码，至少12位）:")
        password1 = getpass.getpass("密码: ")
        password2 = getpass.getpass("确认密码: ")

        if password1 != password2:
            print("❌ 两次密码不一致")
            return

        if len(password1) < 8:
            print("❌ 密码太短，至少需要8个字符")
            print("建议：使用12位以上的强密码，包含大小写字母、数字和符号")
            return

        # 评估密码强度
        strength = 0
        if len(password1) >= 12: strength += 1
        if any(c.isupper() for c in password1): strength += 1
        if any(c.islower() for c in password1): strength += 1
        if any(c.isdigit() for c in password1): strength += 1
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password1): strength += 1

        print()
        print(f"密码强度: {'⭐' * strength}/⭐⭐⭐⭐⭐")
        if strength < 4:
            proceed = input("密码强度较弱，是否继续？(y/n): ").strip().lower()
            if proceed != 'y':
                print("操作已取消")
                return

        # 加密文件
        print()
        print("正在加密...")
        encrypt_file_aes256('.env', '.env.aes256', password1)

        print()
        print("⚠️  重要提示:")
        print("1. 已生成加密文件: .env.aes256")
        print("2. 使用 AES-256-GCM 加密（军事级加密强度）")
        print("3. 请妥善保管密码，忘记密码将无法恢复")
        print("4. 建议删除原始 .env 文件:")

        delete = input("\n是否删除原始 .env 文件？(y/n): ").strip().lower()
        if delete == 'y':
            os.remove('.env')
            print("✅ 原始 .env 文件已删除")
        else:
            print("⚠️  原始 .env 文件仍然存在，请手动删除")

    elif choice == "2":
        # 解密操作
        if not os.path.exists('.env.aes256'):
            print("❌ 错误: .env.aes256 文件不存在")
            return

        if os.path.exists('.env'):
            print("⚠️  警告: .env 文件已存在")
            overwrite = input("是否覆盖？(y/n): ").strip().lower()
            if overwrite != 'y':
                print("操作已取消")
                return

        print()
        print("解密 .env.aes256 文件 (AES-256-GCM)")
        password = getpass.getpass("请输入密码: ")

        # 解密文件
        print()
        print("正在解密并验证...")
        success = decrypt_file_aes256('.env.aes256', '.env', password)

        if success:
            print()
            print("✅ 解密成功！文件完整性已验证")
            print("现在可以运行程序了")

    elif choice == "3":
        # 查看文件信息
        filename = input("\n请输入文件名 (默认: .env.aes256): ").strip()
        if not filename:
            filename = '.env.aes256'
        get_file_info(filename)

    elif choice == "4":
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
        import traceback
        traceback.print_exc()
