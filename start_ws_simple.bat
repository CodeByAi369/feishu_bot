@echo off
REM Feishu Bot Service - Simple Version (No Virtual Environment)
REM Use this if you have permission issues with venv

REM Set UTF-8 encoding
chcp 65001 >nul

echo ======================================
echo Feishu Bot Service (Simple Mode)
echo No Virtual Environment
echo ======================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not detected
    echo Please install Python 3.9 or higher
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python Version:
python --version
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found
    echo Please copy .env.example to .env and configure it
    pause
    exit /b 1
)

REM Install/Update dependencies if needed
if "%1"=="install" (
    echo Installing Python dependencies globally...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo.
    echo Dependencies installed successfully
    pause
    exit /b 0
)

REM Check if dependencies are installed
pip show Flask >nul 2>&1
if %errorlevel% neq 0 (
    echo Dependencies not installed, installing now...
    pip install -r requirements.txt
    echo.
)

REM Start service
echo ======================================
echo Starting Feishu Bot
echo ======================================
echo.
echo TIP: Press Ctrl+C to stop the service
echo.

python app_ws.py

REM Pause if service exits with error
if %errorlevel% neq 0 (
    echo.
    echo Service exited with error code: %errorlevel%
    pause
)
