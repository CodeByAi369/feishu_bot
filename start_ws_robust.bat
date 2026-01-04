@echo off
REM 飞书机器人启动脚本（WebSocket长连接 - 健壮版 - Windows）
REM 功能：自动重启、配置检查、日志管理

chcp 65001 >nul
cd /d "%~dp0"

echo ======================================
echo 启动飞书机器人（长连接模式 - 健壮版）
echo ======================================

REM 1. 检查Python虚拟环境
if not exist "venv" (
    echo [警告] 未找到Python虚拟环境，正在创建...
    python -m venv venv

    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )

    echo [成功] 虚拟环境创建完成

    REM 激活虚拟环境并安装依赖
    call venv\Scripts\activate.bat
    echo 正在安装依赖...
    pip install -r requirements.txt

    if %errorlevel% neq 0 (
        echo [错误] 安装依赖失败
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

REM 2. 检查环境变量配置
if not exist ".env" (
    echo [错误] 未找到 .env 配置文件
    echo 请复制 .env.example 为 .env 并填写配置
    pause
    exit /b 1
)

REM 3. 验证关键配置
echo 检查配置文件...
findstr /C:"FEISHU_APP_ID=cli_" .env >nul
if %errorlevel% neq 0 (
    echo [警告] FEISHU_APP_ID 可能未正确配置
)

findstr /C:"DAILY_REPORT_CHAT_ID=oc_" .env >nul
if %errorlevel% neq 0 (
    echo [警告] DAILY_REPORT_CHAT_ID 未配置，将处理所有群组消息
    echo 建议配置目标群组ID以避免干扰
)

REM 4. 创建日志目录
if not exist "logs" mkdir logs

REM 5. 自动重启机制
set MAX_RETRIES=10
set RETRY_COUNT=0
set RETRY_DELAY=5

echo ======================================
echo 启动服务...
echo - 自动重启: 启用
echo - 最大重试次数: %MAX_RETRIES%
echo - 重试延迟: %RETRY_DELAY%秒
echo - 群组过滤: 已启用（仅处理配置的群组）
echo ======================================

:RETRY_LOOP
if %RETRY_COUNT% geq %MAX_RETRIES% goto MAX_RETRIES_REACHED

echo.
echo [%date% %time%] 启动尝试 %RETRY_COUNT%/%MAX_RETRIES%

REM 启动服务
python app_ws.py

REM 检查退出码
if %errorlevel% equ 0 (
    echo [信息] 服务正常退出
    goto END
) else (
    set /a RETRY_COUNT+=1

    if %RETRY_COUNT% lss %MAX_RETRIES% (
        echo [警告] 服务异常退出 ^(退出码: %errorlevel%^)
        echo 将在 %RETRY_DELAY% 秒后自动重启...
        timeout /t %RETRY_DELAY% /nobreak >nul
        goto RETRY_LOOP
    )
)

:MAX_RETRIES_REACHED
echo [错误] 已达到最大重试次数，停止重启
echo.
echo 可能的解决方案：
echo 1. 检查 .env 配置文件是否正确
echo 2. 检查网络连接（防火墙、代理、VPN）
echo 3. 查看日志文件: logs\bot.log
echo 4. 尝试切换网络环境
echo 5. 关闭VPN或代理服务器
pause
exit /b 1

:END
echo.
echo ======================================
echo 服务已停止
echo ======================================
pause
