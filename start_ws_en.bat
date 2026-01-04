@echo off
REM Feishu Bot Service Startup Script (WebSocket Mode) - Windows Version

REM Set UTF-8 encoding
chcp 65001 >nul

echo ======================================
echo Feishu Bot Service (WebSocket Mode)
echo ======================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not detected, please install Python 3.9 or higher
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python Version:
python --version
echo.

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
    echo.
)

REM Check if virtual environment was created successfully
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not properly created
    echo Trying to create again...
    rmdir /s /q venv 2>nul
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        echo Please check Python installation
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Cannot find venv\Scripts\activate.bat
    echo Please delete the venv folder and run this script again
    pause
    exit /b 1
)
echo Virtual environment activated successfully
echo.

REM Install dependencies if needed
if "%1"=="install" (
    echo Installing Python dependencies...
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

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found
    echo Please copy .env.example to .env and configure it
    pause
    exit /b 1
)

REM Start WebSocket service
echo ======================================
echo Starting Feishu Bot (WebSocket Mode)
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
