@echo off
echo ========================================
echo 正在启动机械臂控制系统后端...
echo ========================================

cd /d %~dp0

REM 检查是否有Maven
where mvn >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到Maven，请在IDEA中运行
    echo.
    echo 请按照以下步骤操作：
    echo 1. 在IDEA中打开 backend 文件夹
    echo 2. 找到 RobotControlApplication.java
    echo 3. 右键点击 -^> Run
    echo.
    pause
    exit /b 1
)

REM 运行Maven
call mvn spring-boot:run

pause
