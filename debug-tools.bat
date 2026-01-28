@echo off
REM 硬件调试工具启动器 - Windows 版本
REM 快速访问所有调试脚本

:menu
cls
echo ================================================================================
echo                      Zero 机械臂 - 硬件调试工具集
echo ================================================================================
echo.
echo 请选择要使用的工具:
echo.
echo   [1] 串口监视器 (Serial Monitor)
echo   [2] ArUco 标记生成器 (ArUco Marker Generator)
echo   [3] 摄像头标定助手 (Camera Calibration Helper)
echo   [4] 硬件测试套件 (Hardware Test Suite)
echo   [5] 列出所有串口设备
echo   [0] 退出
echo.
echo ================================================================================

set /p choice="请输入选项 [0-5]: "

if "%choice%"=="1" goto serial_monitor
if "%choice%"=="2" goto aruco_generator
if "%choice%"=="3" goto camera_calibration
if "%choice%"=="4" goto hardware_test
if "%choice%"=="5" goto list_ports
if "%choice%"=="0" goto end

echo 无效选项,请重新输入
pause
goto menu

:serial_monitor
cls
echo.
echo 启动串口监视器...
echo ================================================================================
echo.
set /p port="请输入串口号 (例如 COM3): "
set /p baudrate="请输入波特率 (默认 115200,直接回车使用默认): "

if "%baudrate%"=="" set baudrate=115200

python tools\serial_monitor.py --port %port% --baudrate %baudrate%
echo.
pause
goto menu

:aruco_generator
cls
echo.
echo ArUco 标记生成器
echo ================================================================================
echo.
echo 生成模式:
echo   [1] 单个标记
echo   [2] 打印表 (多个标记)
echo.
set /p mode="请选择模式 [1-2]: "

if "%mode%"=="1" goto single_marker
if "%mode%"=="2" goto marker_sheet

echo 无效选项
pause
goto menu

:single_marker
set /p marker_id="请输入标记 ID (0-49): "
set /p size="请输入标记尺寸 (像素,默认 200): "

if "%size%"=="" set size=200

python tools\generate_aruco_marker.py --id %marker_id% --size %size%
echo.
echo ✓ 标记已生成: aruco_marker_%marker_id%.png
pause
goto menu

:marker_sheet
echo.
echo 生成 A4 打印表 (包含 ID 0-11)...
python tools\generate_aruco_marker.py --sheet --ids 0 1 2 3 4 5 6 7 8 9 10 11
echo.
echo ✓ 标记表已生成: aruco_sheet_4x4_50.png
echo   请使用 A4 纸打印
pause
goto menu

:camera_calibration
cls
echo.
echo 摄像头标定助手
echo ================================================================================
echo.
set /p camera="请输入摄像头源 (0=默认摄像头, 或输入 IP Camera URL): "

if "%camera%"=="" set camera=0

python tools\camera_calibration_helper.py --camera %camera%
echo.
pause
goto menu

:hardware_test
cls
echo.
echo 硬件测试套件
echo ================================================================================
echo.
set /p port="请输入串口号 (例如 COM3): "

python tools\hardware_test_suite.py --port %port%
echo.
pause
goto menu

:list_ports
cls
echo.
echo 扫描可用串口...
echo ================================================================================
python tools\serial_monitor.py --list
echo.
pause
goto menu

:end
echo.
echo 感谢使用 Zero 机械臂调试工具!
timeout /t 2
exit
