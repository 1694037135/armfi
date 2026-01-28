#!/usr/bin/env python3
"""
串口通信测试工具
用于调试和验证机械臂串口连接
"""
import time
import json
from serial_transport import SerialTransport

def main():
    print("=" * 60)
    print("      Zero 机械臂串口测试工具")
    print("=" * 60)
    print()
    
    # 配置参数（根据实际修改）
    PORT = "COM3"  # Windows
    # PORT = "/dev/ttyUSB0"  # Linux
    BAUDRATE = 115200
    
    print(f"配置:")
    print(f"  串口: {PORT}")
    print(f"  波特率: {BAUDRATE}")
    print()
    
    # 初始化
    try:
        transport = SerialTransport(
            port=PORT,
            baudrate=BAUDRATE,
            enabled=True,
            timeout=1.0
        )
        print("✅ 串口连接成功\n")
    except Exception as e:
        print(f"❌ 串口连接失败: {e}")
        return
    
    # 测试 1: 连续读取角度
    print("-" * 60)
    print("测试 1: 读取当前角度（5次）")
    print("-" * 60)
    
    for i in range(5):
        status = transport.read_status()
        
        print(f"\n[读取 {i+1}]")
        print(f"  角度(度):  {[round(a, 1) for a in status['angles_deg']]}")
        print(f"  角度(弧度): {[round(a, 3) for a in status['angles_rad']]}")
        print(f"  错误码:    {status['error_code']}")
        print(f"  模拟模式:  {'是' if status['serial_mock'] else '否 (真实硬件)'}")
        
        time.sleep(1)
    
    # 测试 2: 发送控制指令
    print("\n" + "-" * 60)
    print("测试 2: 发送控制指令")
    print("-" * 60)
    
    test_angles_deg = [0, 30, 45, 60, 0, 90]
    test_angles_rad = [deg * 3.14159 / 180 for deg in test_angles_deg]
    
    print(f"\n发送目标角度: {test_angles_deg}°")
    
    success = transport.send_command(test_angles_rad)
    
    if success:
        print("✅ 指令发送成功")
        
        # 等待移动
        print("\n等待 3 秒，让机械臂移动...")
        time.sleep(3)
        
        # 读取确认
        print("\n读取当前位置:")
        status = transport.read_status()
        print(f"  当前角度: {[round(a, 1) for a in status['angles_deg']]}°")
        
        # 计算误差
        errors = [abs(status['angles_deg'][i] - test_angles_deg[i]) for i in range(6)]
        print(f"  误差: {[round(e, 1) for e in errors]}°")
        
        if max(errors) < 5:
            print("✅ 角度控制精度良好（误差 < 5°）")
        else:
            print("⚠️ 角度误差较大，需要校准")
    else:
        print("❌ 指令发送失败")
    
    # 测试 3: 性能测试
    print("\n" + "-" * 60)
    print("测试 3: 性能测试（读取延迟）")
    print("-" * 60)
    
    latencies = []
    for i in range(10):
        start = time.time()
        transport.read_status()
        latency = (time.time() - start) * 1000  # 转换为毫秒
        latencies.append(latency)
        print(f"  [{i+1}] 延迟: {latency:.1f} ms")
    
    avg_latency = sum(latencies) / len(latencies)
    print(f"\n平均延迟: {avg_latency:.1f} ms")
    
    if avg_latency < 50:
        print("✅ 延迟优秀（< 50ms）")
    elif avg_latency < 100:
        print("✅ 延迟良好（< 100ms）")
    else:
        print("⚠️ 延迟较高，建议优化")
    
    # 清理
    print("\n" + "=" * 60)
    transport.close()
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
