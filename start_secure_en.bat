@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo Feishu Bot - Secure Start (Memory Decryption)
echo ============================================================
echo.

REM Check virtual environment
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found
    echo Please run: start_ws.bat install
    pause
    exit /b 1
)

REM Check encrypted file
if not exist ".env.encrypted" (
    echo [ERROR] .env.encrypted file not found
    echo.
    echo Please follow these steps:
    echo 1. Make sure .env file is configured
    echo 2. Run encrypt_env.py to encrypt .env
    echo 3. Then run this script
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Secure Mode:
echo - Configuration will be decrypted in memory
echo - No .env file will be generated
echo - Others cannot view your configuration
echo ============================================================
echo.

REM Run secure start script
python start_secure.py

REM Pause if error occurred
if errorlevel 1 (
    echo.
    echo [ERROR] Program exited abnormally
    pause
)

endlocal
