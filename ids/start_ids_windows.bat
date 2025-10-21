@echo off
echo.
echo ========================================
echo   PANDORA IDS - NETWORK MONITOR
echo ========================================
echo.
echo [WARNING] This requires Administrator privileges
echo           to capture network packets
echo.
pause

REM Check for admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Please run as Administrator!
    pause
    exit /b 1
)

echo [OK] Running with admin privileges
echo.
echo [STARTING] IDS Engine...
cd %~dp0
python ids_engine.py

