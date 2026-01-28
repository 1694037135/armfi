@echo off
chcp 65001 >nul
echo ========================================
echo 机械臂控制系统 - 停止所有服务
echo ========================================
echo.

REM 停止 Node.js (前端)
echo [1/3] 停止前端服务...
taskkill /F /IM node.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ 前端服务已停止
) else (
    echo - 前端服务未运行
)
echo.

REM 停止 Python (AI服务)
echo [2/3] 停止 AI 服务...
taskkill /F /IM python.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ AI 服务已停止
) else (
    echo - AI 服务未运行
)
echo.

REM 停止 Java (后端)
echo [3/3] 停止后端服务...
taskkill /F /IM java.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ 后端服务已停止
) else (
    echo - 后端服务未运行
)
echo.

echo ========================================
echo 所有服务已停止！
echo ========================================
echo.
pause
