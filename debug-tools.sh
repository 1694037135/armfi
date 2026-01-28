#!/bin/bash
# 硬件调试工具启动器 - Linux/MacOS 版本
# 快速访问所有调试脚本

show_menu() {
    clear
    echo "================================================================================"
    echo "                     Zero 机械臂 - 硬件调试工具集"
    echo "================================================================================"
    echo ""
    echo "请选择要使用的工具:"
    echo ""
    echo "  [1] 串口监视器 (Serial Monitor)"
    echo "  [2] ArUco 标记生成器 (ArUco Marker Generator)"
    echo "  [3] 摄像头标定助手 (Camera Calibration Helper)"
    echo "  [4] 硬件测试套件 (Hardware Test Suite)"
    echo "  [5] 列出所有串口设备"
    echo "  [0] 退出"
    echo ""
    echo "================================================================================"
}

serial_monitor() {
    clear
    echo ""
    echo "启动串口监视器..."
    echo "================================================================================"
    echo ""
    read -p "请输入串口号 (例如 /dev/ttyUSB0): " port
    read -p "请输入波特率 (默认 115200,直接回车使用默认): " baudrate
    
    baudrate=${baudrate:-115200}
    
    python3 tools/serial_monitor.py --port "$port" --baudrate "$baudrate"
    echo ""
    read -p "按回车返回菜单..."
}

aruco_generator() {
    clear
    echo ""
    echo "ArUco 标记生成器"
    echo "================================================================================"
    echo ""
    echo "生成模式:"
    echo "  [1] 单个标记"
    echo "  [2] 打印表 (多个标记)"
    echo ""
    read -p "请选择模式 [1-2]: " mode
    
    if [ "$mode" == "1" ]; then
        read -p "请输入标记 ID (0-49): " marker_id
        read -p "请输入标记尺寸 (像素,默认 200): " size
        size=${size:-200}
        
        python3 tools/generate_aruco_marker.py --id "$marker_id" --size "$size"
        echo ""
        echo "✓ 标记已生成: aruco_marker_${marker_id}.png"
    elif [ "$mode" == "2" ]; then
        echo ""
        echo "生成 A4 打印表 (包含 ID 0-11)..."
        python3 tools/generate_aruco_marker.py --sheet --ids 0 1 2 3 4 5 6 7 8 9 10 11
        echo ""
        echo "✓ 标记表已生成: aruco_sheet_4x4_50.png"
        echo "  请使用 A4 纸打印"
    else
        echo "无效选项"
    fi
    
    read -p "按回车返回菜单..."
}

camera_calibration() {
    clear
    echo ""
    echo "摄像头标定助手"
    echo "================================================================================"
    echo ""
    read -p "请输入摄像头源 (0=默认摄像头, 或输入 IP Camera URL): " camera
    camera=${camera:-0}
    
    python3 tools/camera_calibration_helper.py --camera "$camera"
    echo ""
    read -p "按回车返回菜单..."
}

hardware_test() {
    clear
    echo ""
    echo "硬件测试套件"
    echo "================================================================================"
    echo ""
    read -p "请输入串口号 (例如 /dev/ttyUSB0): " port
    
    python3 tools/hardware_test_suite.py --port "$port"
    echo ""
    read -p "按回车返回菜单..."
}

list_ports() {
    clear
    echo ""
    echo "扫描可用串口..."
    echo "================================================================================"
    python3 tools/serial_monitor.py --list
    echo ""
    read -p "按回车返回菜单..."
}

# 主循环
while true; do
    show_menu
    read -p "请输入选项 [0-5]: " choice
    
    case $choice in
        1) serial_monitor ;;
        2) aruco_generator ;;
        3) camera_calibration ;;
        4) hardware_test ;;
        5) list_ports ;;
        0) 
            echo ""
            echo "感谢使用 Zero 机械臂调试工具!"
            sleep 1
            exit 0
            ;;
        *)
            echo "无效选项,请重新输入"
            sleep 1
            ;;
    esac
done
