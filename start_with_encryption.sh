#!/bin/bash

echo "=========================================="
echo "启动加密版飞书机器人服务"
echo "=========================================="
echo ""

# 检查是否存在加密文件
if [ ! -f ".env.encrypted" ] && [ ! -f ".env.aes256" ]; then
    echo "❌ 错误: 未找到加密文件（.env.encrypted 或 .env.aes256）"
    echo "请先运行 python3 encrypt_env.py 加密 .env 文件"
    exit 1
fi

# 检查是否已有解密的.env文件
if [ -f ".env" ]; then
    echo "⚠️  .env 文件已存在"
    read -p "是否覆盖？(y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "使用现有 .env 文件启动..."
        ./start_ws.sh
        exit 0
    fi
fi

# 解密文件
echo "请输入解密密码:"

if [ -f ".env.aes256" ]; then
    echo "使用 AES-256-GCM 解密..."
    python3 -c "
from encrypt_env_aes256 import decrypt_file_aes256
import getpass

password = getpass.getpass()
success = decrypt_file_aes256('.env.aes256', '.env', password)

if not success:
    exit(1)
"
else
    echo "使用 Fernet 解密..."
    python3 -c "
from encrypt_env import decrypt_file
import getpass

password = getpass.getpass()
success = decrypt_file('.env.encrypted', '.env', password)

if not success:
    exit(1)
"
fi

if [ $? -ne 0 ]; then
    echo "❌ 解密失败"
    exit 1
fi

echo ""
echo "✅ 解密成功！"
echo ""

# 启动服务
echo "启动飞书机器人服务..."
./start_ws.sh

# 服务停止后，询问是否删除.env文件
echo ""
echo "=========================================="
echo "服务已停止"
echo "=========================================="
read -p "是否删除解密的 .env 文件以保护安全？(y/n): " cleanup
if [ "$cleanup" = "y" ]; then
    rm -f .env
    echo "✅ .env 文件已删除"
else
    echo "⚠️  .env 文件仍然存在，请注意安全"
fi
