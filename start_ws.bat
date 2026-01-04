@echo off
REM 飞书机器人邮件转发服务启动脚本（长连接模式）- Windows版本

REM 设置字符编码为UTF-8
chcp 65001 >nul

echo ======================================
echo 飞书机器人邮件转发服务（长连接模式）
echo ======================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Python，请先安装Python 3.9或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python版本:
python --version
echo.

REM 检查并创建虚拟环境
if not exist "venv" (
    echo 创建Python虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo 错误: 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo 虚拟环境创建成功
    echo.
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 错误: 激活虚拟环境失败
    pause
    exit /b 1
)
echo.

REM 检查是否需要安装依赖
if "%1"=="install" (
    echo 安装Python依赖...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo.
    echo 依赖安装完成
    pause
    exit /b 0
)

REM 检查依赖是否已安装
pip show Flask >nul 2>&1
if %errorlevel% neq 0 (
    echo 检测到依赖未安装，正在安装...
    pip install -r requirements.txt
    echo.
)

REM 检查.env文件是否存在
if not exist ".env" (
    echo 错误: .env 文件不存在
    echo 请先复制 .env.example 为 .env 并配置相关信息
    pause
    exit /b 1
)

REM 启动长连接服务
echo ======================================
echo 启动飞书机器人（长连接模式）
echo ======================================
echo.
echo 提示: 按 Ctrl+C 可停止服务
echo.

python app_ws.py

REM 服务停止后暂停，以便查看错误信息
if %errorlevel% neq 0 (
    echo.
    echo 服务异常退出，错误代码: %errorlevel%
    pause
)
