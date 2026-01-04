#!/bin/bash
# 飞书机器人启动脚本（WebSocket长连接 - 健壮版）
# 功能：自动重启、网络检测、日志管理

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================"
echo "启动飞书机器人（长连接模式 - 健壮版）"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[警告] 未找到Python虚拟环境，正在创建...${NC}"
    python3 -m venv venv

    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 创建虚拟环境失败${NC}"
        exit 1
    fi

    echo -e "${GREEN}[成功] 虚拟环境创建完成${NC}"

    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    echo "正在安装依赖..."
    pip install -r requirements.txt

    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 安装依赖失败${NC}"
        exit 1
    fi
else
    source venv/bin/activate
fi

# 2. 检查环境变量配置
if [ ! -f ".env" ]; then
    echo -e "${RED}[错误] 未找到 .env 配置文件${NC}"
    echo "请复制 .env.example 为 .env 并填写配置"
    exit 1
fi

# 3. 验证关键配置
echo "检查配置文件..."
if ! grep -q "FEISHU_APP_ID=cli_" .env; then
    echo -e "${YELLOW}[警告] FEISHU_APP_ID 可能未正确配置${NC}"
fi

if ! grep -q "DAILY_REPORT_CHAT_ID=oc_" .env; then
    echo -e "${YELLOW}[警告] DAILY_REPORT_CHAT_ID 未配置，将处理所有群组消息${NC}"
    echo "建议配置目标群组ID以避免干扰"
fi

# 4. 创建日志目录
mkdir -p logs

# 5. 网络连接检测
echo "检测网络连接..."
if command -v nc &> /dev/null; then
    # 检测是否能连接飞书服务器（443端口）
    nc -z -w 5 open.feishu.cn 443 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[成功] 网络连接正常${NC}"
    else
        echo -e "${YELLOW}[警告] 无法连接到飞书服务器，请检查网络${NC}"
        echo "可能原因：防火墙、代理、VPN等"
    fi
else
    echo "跳过网络检测（nc命令不可用）"
fi

# 6. 自动重启机制
MAX_RETRIES=10
RETRY_COUNT=0
RETRY_DELAY=5

echo "======================================"
echo "启动服务..."
echo "- 自动重启: 启用"
echo "- 最大重试次数: $MAX_RETRIES"
echo "- 重试延迟: ${RETRY_DELAY}秒"
echo "- 群组过滤: 已启用（仅处理配置的群组）"
echo "======================================"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动尝试 $((RETRY_COUNT + 1))/$MAX_RETRIES"

    # 启动服务
    python app_ws.py
    EXIT_CODE=$?

    # 检查退出码
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}[信息] 服务正常退出${NC}"
        break
    elif [ $EXIT_CODE -eq 130 ]; then
        # Ctrl+C (SIGINT)
        echo -e "${GREEN}[信息] 收到用户中断信号，退出${NC}"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))

        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}[警告] 服务异常退出 (退出码: $EXIT_CODE)${NC}"
            echo "将在 ${RETRY_DELAY} 秒后自动重启..."
            sleep $RETRY_DELAY
        else
            echo -e "${RED}[错误] 已达到最大重试次数，停止重启${NC}"
            echo ""
            echo "可能的解决方案："
            echo "1. 检查 .env 配置文件是否正确"
            echo "2. 检查网络连接（防火墙、代理、VPN）"
            echo "3. 查看日志文件: logs/bot.log"
            echo "4. 尝试切换网络环境"
            exit 1
        fi
    fi
done

echo ""
echo "======================================"
echo "服务已停止"
echo "======================================"
