@echo off
REM Generate self-signed SSL certificate for development

echo Generating self-signed SSL certificate...
echo.

openssl req -x509 -nodes -days 365 -newkey rsa:2048 ^
  -keyout ssl\selfsigned.key ^
  -out ssl\selfsigned.crt ^
  -subj "/C=VN/ST=HCM/L=HCM/O=Pandora/CN=localhost"

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] SSL certificate generated successfully!
    echo   Certificate: ssl\selfsigned.crt
    echo   Key: ssl\selfsigned.key
) else (
    echo.
    echo [ERROR] Failed to generate SSL certificate
    echo Please ensure OpenSSL is installed and in PATH
)

