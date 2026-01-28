@echo off
chcp 65001 >nul
echo ========================================
echo 机械臂控制系统 - 环境配置
echo ========================================
echo.

REM 检查 Node.js
echo [1/3] 检查 Node.js...
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Node.js
    echo 请先安装 Node.js 18+: https://nodejs.org/
    pause
    exit /b 1
)
node -v
echo ✓ Node.js 已安装
echo.

REM 检查 Python
echo [2/3] 检查 Python...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Python
    echo 请先安装 Python 3.11: https://www.python.org/
    pause
    exit /b 1
)
python --version
echo ✓ Python 已安装
echo.

REM 安装前端依赖
echo [3/3] 安装依赖...
echo.
echo → 安装前端依赖 (npm install)...
cd /d "%~dp0frontend"
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 前端依赖安装失败
    pause
    exit /b 1
)
echo ✓ 前端依赖安装完成
echo.

REM 安装 AI 服务依赖
echo → 安装 AI 服务依赖 (pip install)...
cd /d "%~dp0ai-service"
python -m pip install fastapi uvicorn python-multipart ultralytics opencv-python
if %ERRORLEVEL% NEQ 0 (
    echo [错误] AI 服务依赖安装失败
    pause
    exit /b 1
)
echo ✓ AI 服务依赖安装完成
echo.

echo ========================================
echo 环境配置完成！
echo ========================================
echo.
echo 后端依赖由 IDEA 自动管理，无需手动安装
echo.
echo 下一步：双击 "2-启动项目.bat" 启动所有服务
echo.
pause
