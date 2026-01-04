#!/bin/bash

# 飞书机器人邮件转发服务启动脚本

# 设置工作目录
cd "$(dirname "$0")"

# 检查Python版本
echo "Python版本:"
python3 --version

# 检查并创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "错误: 创建虚拟环境失败"
        exit 1
    fi
    echo "虚拟环境创建成功"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖（首次运行或更新后）
if [ "$1" == "install" ]; then
    echo "安装Python依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "依赖安装完成"
    exit 0
fi

# 检查依赖是否已安装
if ! pip show Flask > /dev/null 2>&1; then
    echo "检测到依赖未安装，正在安装..."
    pip install -r requirements.txt
fi

# 加载环境变量
if [ -f .env ]; then
    echo "加载环境变量..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "错误: .env 文件不存在，请先复制 .env.example 并配置"
    exit 1
fi

# 启动服务
echo "启动飞书机器人邮件转发服务..."
python app.py
