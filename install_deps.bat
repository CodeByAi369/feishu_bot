@echo off
chcp 65001 >nul
echo ==========================================
echo Install Python Dependencies
echo ==========================================
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Virtual environment found, activating...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found, installing globally...
)

echo.
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ==========================================
echo Verifying cryptography installation...
echo ==========================================
pip show cryptography

echo.
echo ==========================================
echo Testing encryption modules...
echo ==========================================
python test_encryption.py

echo.
echo ==========================================
echo Installation complete!
echo ==========================================
pause
