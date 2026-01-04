@echo off
REM Feishu Bot Service with .env Encryption
REM Automatically decrypt .env and start service

chcp 65001 >nul

echo ======================================
echo Feishu Bot Service (Encrypted Mode)
echo ======================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

REM Check if encrypted file exists
if not exist ".env.encrypted" (
    echo ERROR: .env.encrypted not found
    echo Please run: python encrypt_env.py
    pause
    exit /b 1
)

REM Check if .env already exists
if exist ".env" (
    echo WARNING: .env file already exists
    echo Using existing .env file
    goto :start_service
)

REM Decrypt .env file
echo Decrypting .env file...
python -c "import sys; sys.path.insert(0, '.'); from encrypt_env import decrypt_file; import getpass; password = getpass.getpass('Enter password: '); decrypt_file('.env.encrypted', '.env', password)"

if %errorlevel% neq 0 (
    echo ERROR: Decryption failed
    pause
    exit /b 1
)

:start_service
echo.
echo Starting service...
echo.

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Start service
python app_ws.py

REM Cleanup: Delete decrypted .env file after service stops
echo.
echo Service stopped. Cleaning up...
if exist ".env" (
    del .env
    echo .env file removed for security
)

echo.
pause
