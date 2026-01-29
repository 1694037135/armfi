@echo off
chcp 65001 >nul
echo ========================================
echo 机械臂控制系统 - 环境安装与更新
echo ========================================
echo.

REM 1. 检查 Python
echo [1/3] 检查 Python 环境...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)
python --version
echo.

REM 2. 升级 pip (避免依赖冲突)
echo [2/4] 升级 pip 到最新版本...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.

REM 3. 安装 AI 依赖 (这是你之前黑屏的主要原因!!!)
echo [3/4] 安装/更新 AI 服务依赖...
echo 正在使用清华源加速下载...
cd /d "%~dp0ai-service"
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 依赖安装失败！
    echo.
    echo 可能的原因:
    echo 1. 网络连接问题
    echo 2. Python 版本不兼容 (需要 Python 3.10+)
    echo 3. 缺少 C++ 编译器 (某些包需要)
    echo.
    echo 请尝试:
    echo 1. 检查网络连接
    echo 2. 运行: python --version (确认版本)
    echo 3. 查看上方的详细错误信息
    echo.
    pause
    exit /b 1
) else (
    echo ✓ AI 服务依赖安装成功
)
echo.

REM 4. 安装前端依赖
echo [4/4] 对于前端依赖...
echo 如果之前能启动前端，这步可以跳过。
set /p INSTALL_FRONTEND="是否重新安装前端依赖? (y/n, 默认n): "
if /i "%INSTALL_FRONTEND%"=="y" (
    echo 正在安装前端依赖...
    cd /d "%~dp0frontend"
    call npm install --registry=https://registry.npmmirror.com
    echo ✓ 前端依赖安装完成
)

echo.
echo ========================================
echo ✅ 所有环境准备就绪！
echo ========================================
echo.
echo 现在，你可以运行 "启动-配合IDEA开发.bat" 了。
echo.
pause
