@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM 飞书机器人 - 一键安全部署和启动
REM ============================================================

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在
    echo.
    echo 正在创建虚拟环境...
    python -m venv venv
    
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        echo 请确保已安装 Python 3.7+
        pause
        exit /b 1
    )
    
    echo ✅ 虚拟环境创建成功
    echo.
    echo 正在安装依赖...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    
    if errorlevel 1 (
        echo [错误] 安装依赖失败
        pause
        exit /b 1
    )
    
    echo ✅ 依赖安装成功
    echo.
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 运行一键部署脚本
python setup_and_start.py

REM 如果程序退出，暂停以便查看信息
if errorlevel 1 (
    echo.
    pause
)
