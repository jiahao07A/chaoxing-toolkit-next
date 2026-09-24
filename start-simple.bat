@echo off
title Chaoxing Toolkit Launcher

echo ========================================
echo Chaoxing Toolkit - Startup Script
echo ========================================
echo.

REM Configuration
set "CHROME_PROFILE=Default"
set "TIKU_PORT=8002"

echo [1/3] Starting server...
cd /d "%~dp0tiku"

REM Check virtual environment
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Set port and start server in a new window (minimized)
set PORT=%TIKU_PORT%
echo Starting server on port %TIKU_PORT%...
start "Tiku Server" /MIN cmd /c "set PORT=%TIKU_PORT% && venv\Scripts\python.exe main.py"

REM Wait for server (using ping instead of timeout to avoid Ctrl+C issues)
echo Waiting for server to start...
ping 127.0.0.1 -n 8 >nul 2>&1

echo.
echo [2/3] Opening admin panel...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --profile-directory="%CHROME_PROFILE%" "http://localhost:%TIKU_PORT%/#/login?auto=1&user=admin&pass=admin"

REM Short delay
ping 127.0.0.1 -n 3 >nul 2>&1

echo.
echo [3/3] Opening Chaoxing...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --profile-directory="%CHROME_PROFILE%" "https://i.chaoxing.com/base?ws=1&t=1790138632014"

echo.
echo ========================================
echo Startup Complete!
echo ========================================
echo.
echo Service Information:
echo   Admin Panel: http://localhost:%TIKU_PORT%
echo   API Endpoint: http://localhost:%TIKU_PORT%/api/search
echo   Chrome Profile: %CHROME_PROFILE% (jiahao001)
echo.
echo Admin Login:
echo   Username: admin
echo   Password: admin
echo.
echo Tampermonkey Setup:
echo   Configure API URL: http://localhost:%TIKU_PORT%/api/search
echo.
echo Note: Server is running in a separate window (minimized)
echo       To stop server, run stop.bat
echo.
echo You can close this window now.
echo.
pause
