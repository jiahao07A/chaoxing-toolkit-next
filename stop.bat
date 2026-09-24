@echo off
title Stop Tiku Server

echo ========================================
echo Stop Tiku Server
echo ========================================
echo.

set "TIKU_PORT=8002"

echo Finding process on port %TIKU_PORT%...

REM Find and kill process using the port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%TIKU_PORT%" ^| findstr "LISTENING"') do (
    echo Found process PID: %%a
    taskkill /F /PID %%a
    if %errorlevel% equ 0 (
        echo Server stopped successfully
    ) else (
        echo Failed to stop server
    )
)

echo.
echo Done!
pause
