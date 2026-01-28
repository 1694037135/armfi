@echo off
chcp 65001 >nul
echo ========================================
echo 🚀 E盘机械臂控制系统 - 快速启动
echo ========================================
echo.
echo 项目位置: E:\zero-robotic-arm\robot-control-system
echo.
echo 此脚本会启动:
echo   1. 后端服务 (Java Spring Boot)
echo   2. 前端服务 (Vue 3)
echo   3. AI服务 (Python FastAPI)
echo.
echo ========================================
echo.

REM 检查E盘项目是否存在
if not exist "E:\zero-robotic-arm\robot-control-system" (
    echo ❌ 错误: E盘项目不存在！
    echo.
    echo 请确认项目已经复制到E盘
    pause
    exit /b 1
)

echo ✅ E盘项目存在
echo.

REM 切换到E盘项目目录
cd /d "E:\zero-robotic-arm\robot-control-system"

echo 当前目录: %CD%
echo.

REM 检查 Maven
where mvn >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 未找到 Maven
    echo.
    echo 请选择：
    echo 1. 安装 Maven 后重新运行此脚本
    echo 2. 手动在 IDEA 中启动后端
    echo.
    pause
    exit /b 1
)

echo ========================================
echo 准备启动所有服务...
echo ========================================
echo.
echo 提示:
echo   - 后端: http://localhost:8080
echo   - 前端: http://localhost:3000
echo   - AI服务: http://localhost:5000
echo.
echo 按任意键开始启动，或关闭窗口取消...
pause >nul

echo.

REM 启动后端
echo [1/3] 启动后端服务...
start "后端服务 (E盘)" cmd /k "cd /d "E:\zero-robotic-arm\robot-control-system\backend" && mvn spring-boot:run"
timeout /t 3 >nul
echo ✓ 后端服务已启动
echo.

REM 启动前端
echo [2/3] 启动前端服务...
start "前端服务 (E盘)" cmd /k "cd /d "E:\zero-robotic-arm\robot-control-system\frontend" && npm run dev"
timeout /t 2 >nul
echo ✓ 前端服务已启动
echo.

REM 启动 AI 服务
echo [3/3] 启动 AI 服务...
start "AI服务 (E盘)" cmd /k "cd /d "E:\zero-robotic-arm\robot-control-system\ai-service" && python main.py"
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
