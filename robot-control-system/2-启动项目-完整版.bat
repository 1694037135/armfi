@echo off
chcp 65001 >nul
echo ========================================
echo 机械臂控制系统 - 一键启动（完整版）
echo ========================================
echo.
echo 此脚本会启动所有服务（需要安装 Maven）
echo 如果没有 Maven，请使用 "2-启动项目.bat"
echo.

cd /d "%~dp0"

REM 检查 Maven
where mvn >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 未找到 Maven
    echo.
    echo 请选择：
    echo 1. 安装 Maven 后重新运行此脚本
    echo 2. 使用 "2-启动项目.bat" 并在 IDEA 中启动后端
    echo.
    pause
    exit /b 1
)

REM 启动后端
echo [1/3] 启动后端服务...
start "后端服务" cmd /k "cd /d "%~dp0backend" && mvn spring-boot:run"
timeout /t 3 >nul
echo ✓ 后端服务已启动
echo.

REM 启动前端
echo [2/3] 启动前端服务...
start "前端服务" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 2 >nul
echo ✓ 前端服务已启动
echo.

REM 启动 AI 服务
echo [3/3] 启动 AI 服务...
start "AI服务" cmd /k "cd /d "%~dp0ai-service" && python main.py"
timeout /t 2 >nul
echo ✓ AI 服务已启动
echo.

REM 等待服务启动
echo 等待服务启动中...
timeout /t 10 >nul

REM 打开浏览器
echo 正在打开浏览器...
start http://localhost:3000

echo.
echo ========================================
echo 所有服务已启动！
echo ========================================
echo.
echo 前端地址: http://localhost:3000
echo 后端地址: http://localhost:8080
echo AI服务:   http://localhost:5000
echo.
echo 按任意键关闭此窗口（服务会继续运行）
echo 要停止服务，请关闭对应的命令行窗口
echo.
pause
