@echo off
echo ==============================================
echo Resume Creator - Fixed Launch Script
echo ==============================================

echo [INFO] Using global Python installation...
python --version

echo [INFO] Installing/Verifying dependencies...
python -m pip install -r requirements.txt
IF ERRORLEVEL 1 (
    echo [WARNING] Dependency installation had issues. Using existing...
)

echo [INFO] Starting Flask Application...
echo [INFO] App available at http://127.0.0.1:5000
python app.py

pause