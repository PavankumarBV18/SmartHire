@echo off
echo ==============================================
echo SmartHire - Resume Creator ^& ATS Checker
echo ==============================================

cd /d "%~dp0"

IF NOT EXIST "venv" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv venv
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to create venv. Is Python installed?
        pause
        exit /b 1
    )
)

echo [INFO] Activating virtual environment...
call .\venv\Scripts\activate.bat

echo [INFO] Installing/Updating dependencies...
pip install -r requirements.txt

echo [INFO] Starting Flask Application...
python app.py

pause
