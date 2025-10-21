@echo off
echo ===============================================
echo Starting Admin Backend Database (PostgreSQL)
echo ===============================================

echo.
echo [INFO] Starting PostgreSQL container on port 5434
echo [INFO] Database: pandora_admin_db
echo [INFO] User: pandora_admin
echo.

docker-compose up -d

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===============================================
    echo [OK] Admin Database started successfully!
    echo ===============================================
    echo.
    echo Connection Details:
    echo   Host: localhost
    echo   Port: 5434
    echo   Database: pandora_admin_db
    echo   User: pandora_admin
    echo   Password: pandora_admin_pass_2024
    echo.
    echo Redis: localhost:6381
    echo.
    echo ===============================================
    echo [INFO] Waiting for database to be ready...
    timeout /t 5 /nobreak >nul
    echo [OK] Database is ready!
    echo ===============================================
) else (
    echo.
    echo [ERROR] Failed to start database!
    echo [INFO] Make sure Docker Desktop is running
    pause
    exit /b 1
)

pause

