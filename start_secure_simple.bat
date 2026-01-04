@echo off
REM Simple secure start - no Chinese characters

if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found
    echo Run: python -m venv venv
    echo Then: venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist ".env.encrypted" (
    echo ERROR: .env.encrypted not found
    echo Run: python encrypt_env.py first
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python start_secure.py

if errorlevel 1 pause

