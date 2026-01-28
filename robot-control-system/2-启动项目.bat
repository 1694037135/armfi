@echo off
chcp 65001 >nul
echo ========================================
echo 机械臂控制系统 - 一键启动
echo ========================================
echo.

cd /d "%~dp0"

REM 启动前端
echo [1/3] 启动前端服务...
start "前端服务" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 2 >nul
echo ✓ 前端服务已启动
echo.

REM 启动 AI 服务
echo [2/3] 启动 AI 服务...
start "AI服务" cmd /k "cd /d "%~dp0ai-service" && python main.py"
timeout /t 2 >nul
echo ✓ AI 服务已启动
echo.

REM 提示后端启动
echo [3/3] 后端服务...
echo.
echo ⚠️  请在 IDEA 中手动启动后端：
echo    1. 打开 backend 文件夹
echo    2. 运行 RobotControlApplication.java
echo.
echo    或者使用 Maven 命令：
echo    cd backend
echo    mvn spring-boot:run
echo.

REM 等待服务启动
echo 等待服务启动中...
timeout /t 8 >nul

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
