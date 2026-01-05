#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键安全部署和启动脚本
自动检查加密状态，引导完成加密，然后启动机器人
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

def encrypt_env_file(password: str):
    """加密 .env 文件"""
    if not os.path.exists('.env'):
        print("❌ 错误: .env 文件不存在")
        return False

    # 生成随机盐值
    salt = os.urandom(16)
    
    # 派生密钥
    cipher = derive_key(password, salt)
    
    # 读取原文件
    with open('.env', 'rb') as f:
        data = f.read()
    
    # 加密数据
    encrypted = cipher.encrypt(data)
    
    # 保存：盐值 + 加密数据
    with open('.env.encrypted', 'wb') as f:
        f.write(salt + encrypted)
    
    print("✅ .env 文件已加密为 .env.encrypted")
    return True

def load_encrypted_env(encrypted_file: str, password: str):
    """从加密文件加载环境变量到内存"""
    try:
        # 读取加密文件
        with open(encrypted_file, 'rb') as f:
            data = f.read()
        
        # 提取盐值和加密数据
        salt = data[:16]
        encrypted = data[16:]
        
        # 派生密钥
        cipher = derive_key(password, salt)
        
        # 解密数据
        decrypted = cipher.decrypt(encrypted)
        
        # 解析环境变量并加载到内存
        env_lines = decrypted.decode('utf-8').splitlines()
        count = 0
        
        for line in env_lines:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            
            # 解析 KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # 去除引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # 设置环境变量
                os.environ[key] = value
                count += 1
        
        return count
    except Exception as e:
        print(f"❌ 解密失败: {str(e)}")
        return 0

def print_banner():
    """打印横幅"""
    print()
    print("=" * 70)
    print("🚀 飞书机器人 - 一键安全部署和启动")
    print("=" * 70)
    print()

def main():
    print_banner()
    
    # 步骤1: 检查加密状态
    env_exists = os.path.exists('.env')
    encrypted_exists = os.path.exists('.env.encrypted')
    
    password = None
    
    # 情况1: 两个文件都不存在
    if not env_exists and not encrypted_exists:
        print("❌ 错误: 未找到配置文件")
        print()
        print("请先创建 .env 文件并配置以下内容：")
        print("  - FEISHU_APP_ID")
        print("  - FEISHU_APP_SECRET")
        print("  - 其他必要配置...")
        print()
        sys.exit(1)
    
    # 情况2: 只有 .env，需要加密
    if env_exists and not encrypted_exists:
        print("📋 检测到未加密的 .env 文件")
        print()
        print("为了保护您的敏感信息，需要先加密配置文件")
        print()
        
        # 提示设置密码
        while True:
            print("请设置加密密码（建议12位以上，包含大小写字母、数字、符号）：")
            password1 = getpass.getpass("密码: ")
            
            if len(password1) < 6:
                print("❌ 密码长度至少6位，建议12位以上")
                print()
                continue
            
            password2 = getpass.getpass("确认密码: ")
            
            if password1 != password2:
                print("❌ 两次密码不一致，请重新输入")
                print()
                continue
            
            password = password1
            break
        
        print()
        print("正在加密 .env 文件...")
        
        if not encrypt_env_file(password):
            print("❌ 加密失败")
            sys.exit(1)
        
        # 询问是否删除原始文件
        print()
        print("⚠️  加密完成！为了安全，建议删除原始 .env 文件")
        choice = input("是否删除原始 .env 文件? (y/n): ").strip().lower()
        
        if choice == 'y':
            os.remove('.env')
            print("✅ 原始 .env 文件已删除")
        else:
            print("⚠️  原始 .env 文件仍然存在，建议手动删除")
        
        print()
        print("=" * 70)
        print()
    
    # 情况3: 只有 .env.encrypted
    elif not env_exists and encrypted_exists:
        print("✅ 检测到已加密的配置文件")
        print()
    
    # 情况4: 两个文件都存在
    else:
        print("⚠️  检测到 .env 和 .env.encrypted 同时存在")
        print()
        print("为了安全，将使用加密文件并删除明文 .env 文件")
        
        choice = input("是否继续? (y/n): ").strip().lower()
        if choice != 'y':
            print("操作已取消")
            sys.exit(0)
        
        os.remove('.env')
        print("✅ 明文 .env 文件已删除")
        print()
    
    # 步骤2: 启动机器人（使用内存解密）
    print("=" * 70)
    print("🔐 启动机器人（安全模式 - 内存解密）")
    print("=" * 70)
    print()
    print("安全说明：")
    print("  ✅ 配置将在内存中解密")
    print("  ✅ 不会生成 .env 文件")
    print("  ✅ 其他人无法查看您的配置")
    print()
    
    # 如果还没有密码（即已经加密的情况），请求输入
    if password is None:
        password = getpass.getpass("请输入解密密码: ")
    
    print()
    print("正在加载配置...")
    
    # 加载加密配置到内存
    count = load_encrypted_env('.env.encrypted', password)
    
    if count == 0:
        print("❌ 配置加载失败")
        print("可能原因：")
        print("  1. 密码错误")
        print("  2. .env.encrypted 文件损坏")
        sys.exit(1)
    
    print(f"✅ 成功加载 {count} 个环境变量到内存")
    print("✅ 配置已安全加载，未生成任何文件")
    print("=" * 70)
    print()
    
    # 确保 .env 文件不存在
    if os.path.exists('.env'):
        os.remove('.env')
    
    # 标记：使用内存中的环境变量
    os.environ['USE_MEMORY_ENV'] = 'true'
    
    # 启动主程序
    print("启动飞书机器人...")
    print("=" * 70)
    print()
    
    try:
        import runpy
        runpy.run_path('app_ws.py', run_name='__main__')
    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("程序已停止")
        print("=" * 70)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ 程序异常: {str(e)}")
        print("=" * 70)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
