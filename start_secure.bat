@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo 飞书机器人 - 安全启动模式（内存解密）
echo ============================================================
echo.

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在
    echo 请先运行: start_ws.bat install
    pause
    exit /b 1
)

REM 检查加密文件
if not exist ".env.encrypted" (
    echo [错误] 找不到 .env.encrypted 文件
    echo.
    echo 请先运行以下步骤：
    echo 1. 确保 .env 文件已配置
    echo 2. 运行 encrypt_env.py 加密 .env
    echo 3. 再运行此脚本
    echo.
    pause
    exit /b 1
)

REM 激活虚拟环境并运行安全启动脚本
echo 激活虚拟环境...
call venv\Scripts\activate.bat

echo.
echo 安全模式说明：
echo - 配置将在内存中解密
echo - 不会生成 .env 文件
echo - 其他人无法查看配置内容
echo ============================================================
echo.

REM 运行安全启动脚本
python start_secure.py

REM 如果程序退出，暂停以便查看错误信息
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)

endlocal
