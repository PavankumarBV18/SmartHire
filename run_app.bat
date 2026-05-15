@echo off
echo ==============================================
echo ATS Checker - One-Click Setup and Run
echo ==============================================

cd /d "%~dp0"

echo [INFO] Setting up Python path...
set "PATH=C:\Users\Nandu M\anaconda3;C:\Users\Nandu M\anaconda3\Scripts;%PATH%"

IF NOT EXIST "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to create venv. Please ensure Python is installed.
        echo Found python at:
        where python
        pause
        exit /b 1
    )
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Installing/Updating dependencies...
pip install -r requirements.txt
IF ERRORLEVEL 1 (
    echo [WARNING] Dependency installation had some issues. attempting to run anyway...
)

echo [INFO] checking environment variables...
IF NOT EXIST ".env" (
    echo [WARNING] .env file not found! Creating default...
    echo SECRET_KEY=dev_key_123 > .env
    echo # Add your API keys below >> .env
    echo GEMINI_API_KEY= >> .env
    echo GROQ_API_KEY= >> .env
    echo [IMPORTANT] Please update .env with your API Keys!
)

echo [INFO] Starting Flask Application...
echo [INFO] App will be available at http://127.0.0.1:5000
python app.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Application crashed or failed to start.
    pause
) else (
    pause
)