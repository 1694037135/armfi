@echo off
chcp 65001 >nul
echo ========================================
echo 机械臂控制系统 - Docker启动
echo ========================================
echo.

REM 检查 Docker 是否存在
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Docker 命令
    echo 请确保已安装 Docker Desktop 并添加到环境变量中。
    echo 下载地址: https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo [1/2] 拉取最新镜像...
docker-compose pull
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 镜像拉取失败，尝试直接启动...
)

echo.
echo [2/2] 启动服务...
docker-compose up -d

echo.
echo ========================================
echo 服务已在后台启动！
echo ========================================
echo.
echo 前端地址: http://localhost
echo 后端地址: http://localhost:8080
echo AI服务:   http://localhost:8000
echo.
echo 常用命令:
echo - 查看日志: docker-compose logs -f
echo - 停止服务: docker-compose down
echo.
pause
