@echo off
REM ========================================================================
REM Pandora Webserver Startup Script (Windows)
REM ========================================================================

cd /d "%~dp0"

echo ========================================
echo Pandora Custom Webserver Startup
echo ========================================

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt

REM Check if frontend is built
if not exist "..\frontend\dist" (
    echo [WARNING] Frontend not built!
    echo [INFO] Building frontend...
    cd ..\frontend
    call npm install
    call npm run build
    cd ..\custom-webserver
)

REM Start webserver
echo [INFO] Starting FastAPI webserver on port 8443...
python webserver_fastapi.py

pause

