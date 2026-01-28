"""
简单逆运动学（IK）控制器
使用几何方法计算关节角度，无需深度学习训练
立即可用！
"""
import math
import numpy as np

class SimpleIKController:
    """
    6自由度机械臂逆运动学控制器
    使用几何方法求解，适合实时控制
    """
    
    def __init__(self):
        # 机械臂参数（单位：米）
        self.L1 = 0.166  # 底座到关节1的高度
        self.L2 = 0.200  # 关节2到关节3的长度
        self.L3 = 0.185  # 关节3到关节4的长度
        self.L4 = 0.125  # 关节4到末端的长度
        
        # 预定义位置（修正坐标系方向）
        # 坐标系定义：
        # X轴：左(-) / 右(+)
        # Y轴：前(-) / 后(+)  ← 修正：Y负方向为"前"（向前伸展）
        # Z轴：下(-) / 上(+)
        self.presets = {
            "home": (0.0, 0.25, 0.3),       # 初始位置（中间）
            "left": (-0.15, 0.25, 0.25),    # 左侧
            "right": (0.15, 0.25, 0.25),    # 右侧
            "center": (0.0, 0.20, 0.20),    # 中心低位
            "high": (0.0, 0.25, 0.40),      # 高位（抬高）
            "pickup": (0.10, 0.30, 0.15),   # 拾取位置（右后低）
            "forward": (0.0, 0.15, 0.25),   # 前方（Y负方向，向前伸展）
            "back": (0.0, 0.35, 0.25),      # 后方（Y正方向，向后收缩）
        }
    
    def calculate_ik(self, x, y, z):
        """
        计算到达目标位置的关节角度
        
        参数:
            x, y, z: 目标位置（米）
        
        返回:
            dict: {"success": bool, "angles": {...}, "message": str}
        """
        try:
            # 关节1：底座旋转（绕Z轴）
            # 修正：atan2(x, y) 而不是 atan2(x, -y)
            # 坐标系：Y轴正方向为"前"，X轴正方向为"右"
            theta1_rad = math.atan2(x, y)
            theta1_deg = math.degrees(theta1_rad)
            
            # 计算在XY平面的投影距离
            r = math.sqrt(x**2 + y**2)
            
            # 调整目标高度（减去底座高度）
            target_height = z - self.L1
            target_reach = r - self.L4 * 0.5  # 简化：假设末端水平
            
            # 检查是否在工作范围内
            max_reach = self.L2 + self.L3
            min_reach = abs(self.L2 - self.L3)
            actual_reach = math.sqrt(target_reach**2 + target_height**2)
            
            if actual_reach > max_reach:
                return {
                    "success": False,
                    "message": f"目标位置太远（{actual_reach:.3f}m > {max_reach:.3f}m）",
                    "max_reach": max_reach
                }
            
            if actual_reach < min_reach:
                return {
                    "success": False,
                    "message": f"目标位置太近（{actual_reach:.3f}m < {min_reach:.3f}m）",
                    "min_reach": min_reach
                }
            
            # 关节3：使用余弦定理
            cos_angle3 = (actual_reach**2 - self.L2**2 - self.L3**2) / (2 * self.L2 * self.L3)
            cos_angle3 = max(-1.0, min(1.0, cos_angle3))  # 限制在[-1, 1]
            
            theta3_rad = math.acos(cos_angle3)
            theta3_deg = math.degrees(theta3_rad)
            
            # 关节2（大臂俯仰）
            # 修正：向前移动时应该是正角度（向上抬起）
            alpha = math.atan2(target_height, target_reach)
            beta = math.atan2(self.L3 * math.sin(theta3_rad), 
                             self.L2 + self.L3 * math.cos(theta3_rad))
            theta2_rad = -(alpha - beta)  # 添加负号修正方向
            theta2_deg = math.degrees(theta2_rad)
            
            # 关节4、5、6：简化为保持末端水平
            theta4_deg = 0.0  # 简化
            theta5_deg = -(theta2_deg + theta3_deg)  # 保持末端水平
            theta6_deg = 0.0  # 简化
            
            angles = {
                "joint1": theta1_deg,
                "joint2": theta2_deg,
                "joint3": theta3_deg,
                "joint4": theta4_deg,
                "joint5": theta5_deg,
                "joint6": theta6_deg
            }
            
            return {
                "success": True,
                "angles": angles,
                "angles_rad": {
                    "joint1": theta1_rad,
                    "joint2": theta2_rad,
                    "joint3": theta3_rad,
                    "joint4": 0.0,
                    "joint5": math.radians(theta5_deg),
                    "joint6": 0.0
                },
                "target": {"x": x, "y": y, "z": z},
                "message": "目标位置可达"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"计算失败: {str(e)}"
            }
    
    def get_preset(self, position_name):
        """
        获取预定义位置的关节角度
        
        参数:
            position_name: 位置名称（home, left, right, center, high, pickup等）
        
        返回:
            dict: IK计算结果
        """
        if position_name not in self.presets:
            return {
                "success": False,
                "message": f"未知位置: {position_name}",
                "available": list(self.presets.keys())
            }
        
        x, y, z = self.presets[position_name]
        result = self.calculate_ik(x, y, z)
        result["preset"] = position_name
        return result
    
    def parse_voice_command(self, command):
        """
        解析语音指令，返回目标位置
        
        参数:
            command: 语音指令文本
        
        返回:
            dict: IK计算结果
        """
        command_lower = command.lower()
        
        # 问候语和闲聊（返回友好提示）
        greetings = ["你好", "您好", "hi", "hello", "嗨", "哈喽"]
        if any(word in command_lower for word in greetings):
            return {
                "success": False,
                "message": "你好！我是机械臂控制系统。请说出控制指令，例如：向前移动、去左边、回到初始位置",
                "is_greeting": True,
                "available_commands": [
                    "方向：向前/向后/向左/向右/向上/向下",
                    "位置：去左边/去右边/去中间/去高处",
                    "复位：回到初始位置/复位/归位",
                    "抓取：拿/捡/抓/取"
                ]
            }
        
        # 方向指令（带"移动"关键词）
        if "移动" in command or "动" in command:
            if any(word in command_lower for word in ["前", "forward"]):
                return self.get_preset("forward")
            elif any(word in command_lower for word in ["后", "back"]):
                return self.get_preset("back")
            elif any(word in command_lower for word in ["左", "left"]):
                return self.get_preset("left")
            elif any(word in command_lower for word in ["右", "right"]):
                return self.get_preset("right")
            elif any(word in command_lower for word in ["上", "up", "高"]):
                return self.get_preset("high")
            elif any(word in command_lower for word in ["下", "down", "低"]):
                return self.get_preset("pickup")
        
        # 位置指令（带"去"关键词）
        if "去" in command:
            if any(word in command_lower for word in ["左", "left"]):
                return self.get_preset("left")
            elif any(word in command_lower for word in ["右", "right"]):
                return self.get_preset("right")
            elif any(word in command_lower for word in ["中", "center", "中间"]):
                return self.get_preset("center")
            elif any(word in command_lower for word in ["高", "up", "high", "上"]):
                return self.get_preset("high")
            elif any(word in command_lower for word in ["前", "forward", "前面"]):
                return self.get_preset("forward")
            elif any(word in command_lower for word in ["后", "back", "后面"]):
                return self.get_preset("back")
        
        # 简单方向词（无"移动"或"去"）
        if any(word in command_lower for word in ["左", "left"]) and len(command) < 5:
            return self.get_preset("left")
        elif any(word in command_lower for word in ["右", "right"]) and len(command) < 5:
            return self.get_preset("right")
        elif any(word in command_lower for word in ["前", "forward"]) and len(command) < 5:
            return self.get_preset("forward")
        elif any(word in command_lower for word in ["后", "back"]) and len(command) < 5:
            return self.get_preset("back")
        elif any(word in command_lower for word in ["上", "up", "高"]) and len(command) < 5:
            return self.get_preset("high")
        elif any(word in command_lower for word in ["下", "down", "低"]) and len(command) < 5:
            return self.get_preset("pickup")
        
        # 复位指令
        if any(word in command_lower for word in ["初始", "home", "复位", "归位", "原点", "零点", "回到"]):
            return self.get_preset("home")
        
        # 抓取指令
        if any(word in command_lower for word in ["拿", "捡", "抓", "取", "pickup", "抓取"]):
            return self.get_preset("pickup")
        
        # 无法识别
        return {
            "success": False,
            "message": f"无法识别的指令: {command}",
            "available_commands": [
                "方向：向前移动/向后移动/向左移动/向右移动/向上移动/向下移动",
                "位置：去左边/去右边/去中间/去高处",
                "复位：回到初始位置/复位/归位",
                "抓取：拿/捡/抓/取"
            ]
        }
    
    def get_workspace_limits(self):
        """
        获取机械臂工作空间范围
        
        返回:
            dict: 工作空间参数
        """
        max_reach = self.L2 + self.L3 + self.L4
        min_reach = abs(self.L2 - self.L3)
        
        return {
            "max_reach": max_reach,
            "min_reach": min_reach,
            "height_range": {
                "min": self.L1 - (self.L2 + self.L3),
                "max": self.L1 + (self.L2 + self.L3)
            },
            "recommended_zone": {
                "x": (-0.2, 0.2),      # 左(-) / 右(+)
                "y": (0.15, 0.40),     # 前(小) / 后(大) ← Y负方向为"前"
                "z": (0.15, 0.45)      # 下(小) / 上(大)
            }
        }


# 测试代码
if __name__ == "__main__":
    ik = SimpleIKController()
    
    print("=" * 60)
    print("简单逆运动学控制器测试")
    print("=" * 60)
    
    # 测试预定义位置
    print("\n测试预定义位置:")
    for preset in ["home", "left", "right", "pickup"]:
        result = ik.get_preset(preset)
        if result["success"]:
            print(f"\n{preset}:")
            print(f"  目标: {result['target']}")
            print(f"  关节角度: {result['angles']}")
        else:
            print(f"\n{preset}: {result['message']}")
    
    # 测试语音指令
    print("\n" + "=" * 60)
    print("测试语音指令:")
    commands = ["去左边", "抓取物体", "回到初始位置", "移动到高处"]
    for cmd in commands:
        result = ik.parse_voice_command(cmd)
        print(f"\n指令: '{cmd}'")
        if result["success"]:
            print(f"  → {result.get('preset', '自定义位置')}")
            print(f"  关节1: {result['angles']['joint1']:.1f}°")
        else:
            print(f"  → {result['message']}")
    
    # 显示工作空间
    print("\n" + "=" * 60)
    print("工作空间范围:")
    workspace = ik.get_workspace_limits()
    print(f"  最大伸展: {workspace['max_reach']:.3f}m")
    print(f"  最小伸展: {workspace['min_reach']:.3f}m")
    print(f"  推荐区域:")
    print(f"    X: {workspace['recommended_zone']['x']}")
    print(f"    Y: {workspace['recommended_zone']['y']}")
    print(f"    Z: {workspace['recommended_zone']['z']}")
    print("=" * 60)
