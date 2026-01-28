@echo off
chcp 65001 >nul
REM ==============================================================
REM Zero 机械臂控制系统 - Docker 快速部署脚本 (Windows)
REM ==============================================================

echo 🚀 开始部署 Zero 机械臂控制系统...
echo.

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到 Docker，请先安装 Docker Desktop
    pause
    exit /b 1
)

REM 检查 Docker Compose 是否可用
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    docker compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ 错误: 未检测到 Docker Compose
        pause
        exit /b 1
    )
)

REM 进入脚本所在目录
cd /d "%~dp0"

echo.
echo 📋 请选择部署方式:
echo   1) 使用预构建镜像（推荐，快速）
echo   2) 本地构建镜像（完整，较慢）
echo.
set /p choice="请输入选项 [1/2]: "

if "%choice%"=="1" (
    echo.
    echo 📦 拉取预构建镜像...
    docker-compose pull
    if %errorlevel% neq 0 (
        echo ⚠️  拉取镜像失败，将切换到本地构建模式
        set choice=2
    )
)

if "%choice%"=="2" (
    echo.
    echo 🔨 开始本地构建镜像（这可能需要几分钟）...
    docker-compose build
    if %errorlevel% neq 0 (
        echo ❌ 构建失败
        pause
        exit /b 1
    )
)

REM 启动服务
echo.
echo 🚀 启动所有服务...
docker-compose up -d

REM 等待服务启动
echo.
echo ⏳ 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
echo.
echo 📊 服务状态:
docker-compose ps

echo.
echo ✅ 部署完成！
echo.
echo 📍 访问地址:
echo   - 前端界面: http://localhost
echo   - 后端 API: http://localhost:8080
echo   - AI 服务: http://localhost:8000
echo.
echo 📝 常用命令:
echo   - 查看日志: docker-compose logs -f
echo   - 停止服务: docker-compose down
echo   - 重启服务: docker-compose restart
echo.
echo 🎉 祝使用愉快！
echo.
pause
