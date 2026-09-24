@echo off
chcp 65001 >nul
echo ========================================
echo 超星学习通自动化系统启动脚本
echo ========================================
echo.

REM 设置变量
set "CHROME_PROFILE=Profile 4"
set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "TIKU_PORT=8002"
set "TIKU_DIR=%~dp0tiku"
set "CHAOXING_URL=https://i.chaoxing.com/base?ws=1&t=1790138632014"
set "TIKU_URL=http://localhost:%TIKU_PORT%"

REM 检查 Chrome 是否存在
if not exist "%CHROME_PATH%" (
    echo [错误] 未找到 Chrome 浏览器: %CHROME_PATH%
    echo 请修改脚本中的 CHROME_PATH 变量
    pause
    exit /b 1
)

REM 检查题库目录是否存在
if not exist "%TIKU_DIR%" (
    echo [错误] 未找到题库目录: %TIKU_DIR%
    pause
    exit /b 1
)

echo [1/3] 启动题库服务器...
cd /d "%TIKU_DIR%"

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\python.exe" (
    echo [错误] 虚拟环境未安装，请先运行部署脚本
    pause
    exit /b 1
)

REM 启动题库服务器（后台运行）
set PORT=%TIKU_PORT%
start /B "" "%TIKU_DIR%\venv\Scripts\python.exe" main.py
echo 题库服务器启动中... (端口: %TIKU_PORT%)
echo 等待服务器就绪...
timeout /t 5 /nobreak >nul

REM 检查服务器是否启动成功
echo 检查服务器状态...
curl -s http://localhost:%TIKU_PORT%/api/stats >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 服务器可能未完全启动，继续等待...
    timeout /t 3 /nobreak >nul
)

echo.
echo [2/3] 打开题库管理界面...
start "" "%CHROME_PATH%" --profile-directory="%CHROME_PROFILE%" "%TIKU_URL%"
timeout /t 2 /nobreak >nul

echo.
echo [3/3] 打开学习通界面...
start "" "%CHROME_PATH%" --profile-directory="%CHROME_PROFILE%" "%CHAOXING_URL%"

echo.
echo ========================================
echo 启动完成！
echo ========================================
echo.
echo 服务信息:
echo - 题库服务器: %TIKU_URL%
echo - 学习通界面: %CHAOXING_URL%
echo - Chrome 配置: %CHROME_PROFILE%
echo.
echo 使用说明:
echo 1. 题库管理界面已自动打开 (默认账号: admin/admin)
echo 2. 学习通界面已自动打开
echo 3. 确保已在 Tampermonkey 中安装用户脚本
echo 4. 在脚本设置中配置题库地址: %TIKU_URL%/api/search
echo.
echo 按任意键关闭服务器并退出...
pause >nul

REM 关闭服务器
echo.
echo 正在关闭题库服务器...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%TIKU_PORT%" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo 服务器已关闭
