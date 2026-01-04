@echo off
REM Decrypt .env and start service

chcp 65001 >nul
echo ======================================
echo Feishu Bot Service (With Encryption)
echo ======================================
echo.

REM Check if encrypted .env.7z exists
if not exist ".env.7z" (
    echo ERROR: .env.7z not found
    echo Please encrypt your .env file first using 7-Zip
    pause
    exit /b 1
)

REM Check if 7-Zip is installed
where 7z >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: 7-Zip not found
    echo Please install 7-Zip from https://www.7-zip.org/
    pause
    exit /b 1
)

REM Prompt for password and decrypt
echo Enter password to decrypt .env file:
7z x -p .env.7z -y -o.
if %errorlevel% neq 0 (
    echo ERROR: Failed to decrypt .env file
    echo Please check your password
    pause
    exit /b 1
)

echo.
echo .env file decrypted successfully
echo Starting service...
echo.

REM Start the service
python app_ws.py

REM After service stops, re-encrypt and delete plain .env
echo.
echo Service stopped. Cleaning up...
del .env
echo .env file removed

pause
