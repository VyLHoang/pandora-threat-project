@echo off
chcp 65001 > nul
REM ============================================================================
REM Pandora - Test HTTP/HTTPS Listeners on Windows (Local)
REM ============================================================================

echo ========================================================================
echo    PANDORA - Test HTTP/HTTPS Listeners (Local)
echo ========================================================================
echo.

REM Get script directory
set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

echo [INFO] Project Directory: %CD%
echo.

REM Check if port_80.py and port_443.py exist
if not exist "custom-webserver\port_80.py" (
    echo [ERROR] File not found: custom-webserver\port_80.py
    pause
    exit /b 1
)

if not exist "custom-webserver\port_443.py" (
    echo [ERROR] File not found: custom-webserver\port_443.py
    pause
    exit /b 1
)

echo ========================================================================
echo    STARTING LISTENERS
echo ========================================================================
echo.
echo [INFO] Starting HTTP server on port 80...
echo [INFO] Starting HTTPS server on port 443...
echo.
echo NOTE: You need ADMIN RIGHTS to use port 80 and 443 on Windows!
echo       If you see "Permission denied", right-click this .bat and
echo       select "Run as Administrator"
echo.
echo ========================================================================
echo.

REM Start HTTP server (Port 80) in background
start "Pandora HTTP (80)" cmd /k "cd /d "%PROJECT_DIR%\custom-webserver" && python port_80.py"

REM Wait a bit
timeout /t 2 /nobreak > nul

REM Start HTTPS server (Port 443) in background
start "Pandora HTTPS (443)" cmd /k "cd /d "%PROJECT_DIR%\custom-webserver" && python port_443.py"

echo ========================================================================
echo    LISTENERS STARTED
echo ========================================================================
echo.
echo [OK] Two new windows opened:
echo      1. HTTP Server (Port 80)
echo      2. HTTPS Server (Port 443)
echo.
echo ========================================================================
echo    TEST ENDPOINTS
echo ========================================================================
echo.
echo From browser:
echo   • HTTP:  http://localhost
echo   • HTTPS: https://localhost  (accept self-signed cert)
echo.
echo From command line:
echo   • curl http://localhost
echo   • curl -k https://localhost
echo.
echo From PowerShell:
echo   • Invoke-WebRequest http://localhost
echo   • Invoke-WebRequest https://localhost -SkipCertificateCheck
echo.
echo ========================================================================
echo    LOGS
echo ========================================================================
echo.
echo Watch the TWO console windows for real-time logs!
echo All HTTP/HTTPS requests will be logged there.
echo.
echo ========================================================================
echo.
echo Press any key to open test page in browser...
pause > nul

REM Open browser
start http://localhost

echo.
echo ========================================================================
echo [INFO] Browser opened. You should be redirected to HTTPS automatically.
echo ========================================================================
echo.
echo To stop servers: Close the two console windows manually
echo.
pause

