#!/usr/bin/env python3
"""
关节限位检查测试脚本

测试 JointLimits 类的验证功能
"""

from serial_transport import JointLimits

def test_valid_angles():
    """测试正常角度（应该通过）"""
    print("=" * 60)
    print("测试1: 正常角度")
    print("=" * 60)
    
    test_cases = [
        ([0, 0, 0, 0, 0, 0], "全零位"),
        ([90, 45, -30, 90, 45, 90], "正常工作角度"),
        ([180, 90, 135, 180, 90, 180], "最大限位"),
        ([-180, -90, -135, -180, -90, -180], "最小限位"),
    ]
    
    for angles, description in test_cases:
        is_valid, msg = JointLimits.validate_angles(angles)
        status = "✅ 通过" if is_valid else "❌ 失败"
        print(f"{status} | {description}")
        print(f"  角度: {angles}")
        print(f"  结果: {msg}")
        print()

def test_invalid_angles():
    """测试超限角度（应该失败）"""
    print("=" * 60)
    print("测试2: 超限角度")
    print("=" * 60)
    
    test_cases = [
        ([200, 0, 0, 0, 0, 0], "Joint 1 超限"),
        ([0, 100, 0, 0, 0, 0], "Joint 2 超限"),
        ([0, 0, 150, 0, 0, 0], "Joint 3 超限"),
        ([0, 0, 0, 200, 0, 0], "Joint 4 超限"),
        ([0, 0, 0, 0, 100, 0], "Joint 5 超限"),
        ([0, 0, 0, 0, 0, 200], "Joint 6 超限"),
        ([0, -100, 0, 0, 0, 0], "Joint 2 负向超限"),
    ]
    
    for angles, description in test_cases:
        is_valid, msg = JointLimits.validate_angles(angles)
        status = "✅ 正确拒绝" if not is_valid else "❌ 错误通过"
        print(f"{status} | {description}")
        print(f"  角度: {angles}")
        print(f"  错误: {msg}")
        print()

def test_edge_cases():
    """测试边界情况"""
    print("=" * 60)
    print("测试3: 边界情况")
    print("=" * 60)
    
    test_cases = [
        ([180, 90, 135, 180, 90, 180], "所有关节最大值"),
        ([-180, -90, -135, -180, -90, -180], "所有关节最小值"),
        ([180.0, 90.0, 135.0, 180.0, 90.0, 180.0], "浮点数最大值"),
        ([0, 0, 0], "角度数量不足"),
        ([0, 0, 0, 0, 0, 0, 0], "角度数量过多"),
    ]
    
    for angles, description in test_cases:
        is_valid, msg = JointLimits.validate_angles(angles)
        status = "✅" if is_valid else "❌"
        print(f"{status} | {description}")
        print(f"  角度: {angles}")
        print(f"  结果: {msg}")
        print()

def test_limits_info():
    """显示限位信息"""
    print("=" * 60)
    print("关节限位信息")
    print("=" * 60)
    
    limits = JointLimits.get_limits()
    joint_names = [
        "Joint 1 (基座旋转)",
        "Joint 2 (大臂俯仰)",
        "Joint 3 (从臂)",
        "Joint 4 (手腕旋转)",
        "Joint 5 (手腕俯仰)",
        "Joint 6 (末端旋转)",
    ]
    
    for idx, (name, (min_angle, max_angle)) in enumerate(zip(joint_names, limits), 1):
        print(f"{name}")
        print(f"  范围: [{min_angle:>6.1f}°, {max_angle:>6.1f}°]")
        print(f"  跨度: {max_angle - min_angle:>6.1f}°")
        print()

if __name__ == "__main__":
    print("\n🧪 关节限位检查测试\n")
    
    # 显示限位信息
    test_limits_info()
    
    # 测试正常角度
    test_valid_angles()
    
    # 测试超限角度
    test_invalid_angles()
    
    # 测试边界情况
    test_edge_cases()
    
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
