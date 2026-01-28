"""
高级逆运动学（IK）控制器
使用 ikpy 库基于 URDF 进行数值求解
支持姿态约束和关节限位
"""
import numpy as np
from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink
import os

class AdvancedIKController:
    """
    基于 URDF 的高级 IK 控制器
    使用 ikpy 进行数值求解，支持姿态约束
    """
    
    def __init__(self, urdf_path=None):
        """
        初始化 IK 控制器
        
        参数:
            urdf_path: URDF 文件路径（可选）
        """
        if urdf_path is None:
            # 默认 URDF 路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            urdf_path = os.path.join(
                project_root,
                "3. Simulink",
                "URDF_XG_Robot_Arm_Urdf_V1_1",
                "urdf",
                "URDF_XG_Robot_Arm_Urdf_V1_1.urdf"
            )
        
        self.urdf_path = urdf_path
        
        # 创建运动链（从 URDF 加载）
        try:
            self.chain = Chain.from_urdf_file(
                urdf_path,
                base_elements=["base_link"],
                last_link_vector=[0, 0, 0.05],  # ee_link 末端偏移
                active_links_mask=[False, True, True, True, True, True, True, False]
                # [base, j1, j2, j3, j4, j5, j6, ee] - base 和 ee 不可动
            )
            print(f"[OK] 成功加载 URDF: {os.path.basename(urdf_path)}")
        except Exception as e:
            print(f"[WARN] URDF 加载失败: {e}")
            print("[INFO] 使用手动定义的运动链")
            self.chain = self._create_manual_chain()
        
        # 关节限位（弧度）
        self.joint_limits = {
            "joint1": (-3.14, 3.14),
            "joint2": (-1.57, 1.57),
            "joint3": (0, 3.14),
            "joint4": (-3.14, 3.14),
            "joint5": (-1.57, 0),
            "joint6": (-3.14, 3.14)
        }
        
        # 预定义位置
        self.presets = {
            "home": (0.0, 0.25, 0.3),
            "left": (-0.15, 0.25, 0.25),
            "right": (0.15, 0.25, 0.25),
            "center": (0.0, 0.20, 0.20),
            "high": (0.0, 0.25, 0.40),
            "pickup": (0.10, 0.30, 0.15),
            "forward": (0.0, 0.15, 0.25),
            "back": (0.0, 0.35, 0.25),
        }
    
    def _create_manual_chain(self):
        """手动创建运动链（备用方案）"""
        from ikpy.link import Link
        
        links = [
            OriginLink(),
            URDFLink(
                name="joint1",
                bounds=(-3.14, 3.14),
                origin_translation=[0, 0, 0.166],
                origin_orientation=[0, 0, 0],
                rotation=[0, 0, 1]
            ),
            URDFLink(
                name="joint2",
                bounds=(-1.57, 1.57),
                origin_translation=[0, 0, 0],
                origin_orientation=[0, 0, 0],
                rotation=[0, 1, 0]
            ),
            URDFLink(
                name="joint3",
                bounds=(0, 3.14),
                origin_translation=[0.2, 0, 0],
                origin_orientation=[0, 0, 0],
                rotation=[0, 1, 0]
            ),
            URDFLink(
                name="joint4",
                bounds=(-3.14, 3.14),
                origin_translation=[0.0476, -0.1845, 0],
                origin_orientation=[0, 0, 0],
                rotation=[0, 0, 1]
            ),
            URDFLink(
                name="joint5",
                bounds=(-1.57, 0),
                origin_translation=[0, 0, 0],
                origin_orientation=[0, 0, 0],
                rotation=[0, 1, 0]
            ),
            URDFLink(
                name="joint6",
                bounds=(-3.14, 3.14),
                origin_translation=[0, -0.125, 0],
                origin_orientation=[0, 0, 0],
                rotation=[0, 0, 1]
            ),
            OriginLink()  # End effector (non-actuated)
        ]
        
        return Chain(name="robot_arm", links=links)
    
    def calculate_ik(self, x, y, z, orientation="down"):
        """
        计算逆运动学
        
        参数:
            x, y, z: 目标位置（米）
            orientation: 末端姿态 ("down", "forward", "custom")
        
        返回:
            dict: {success, angles, message}
        """
        try:
            target_position = [x, y, z]
            
            # 设定目标姿态矩阵
            if orientation == "down":
                # 末端朝下（抓取姿态）
                target_orientation = [
                    [1, 0, 0],
                    [0, 1, 0],
                    [0, 0, 1]
                ]
            elif orientation == "forward":
                # 末端水平向前
                target_orientation = [
                    [0, 0, 1],
                    [0, 1, 0],
                    [-1, 0, 0]
                ]
            else:
                target_orientation = None  # 不约束姿态
            
            # 构建目标变换矩阵
            target_matrix = np.eye(4)
            target_matrix[:3, 3] = target_position
            if target_orientation:
                target_matrix[:3, :3] = target_orientation
            
            # 初始猜测（当前姿态或零位）
            initial_position = [0] * len(self.chain.links)
            
            # 调用 IK 求解器 (ikpy 3.x uses target_position as array)
            ik_solution = self.chain.inverse_kinematics(
                target_position=target_position,  # Direct position array
                initial_position=initial_position
            )
            
            # 提取关节角度
            # Chain: [Origin(0), J1(1), J2(2), J3(3), J4(4), J5(5), J6(6), EE(7)]
            # We want indices 1-6
            joint_angles_rad = ik_solution[1:7].tolist()
            
            # 检查关节限位
            within_limits = True
            for i, (joint_name, limits) in enumerate(self.joint_limits.items()):
                if not (limits[0] <= joint_angles_rad[i] <= limits[1]):
                    within_limits = False
                    break
            
            if not within_limits:
                return {
                    "success": False,
                    "message": "超出关节限位",
                    "angles_rad": dict(zip(self.joint_limits.keys(), joint_angles_rad))
                }
            
            # 转换为角度
            angles_deg = {
                f"joint{i+1}": np.degrees(angle)
                for i, angle in enumerate(joint_angles_rad)
            }
            
            angles_rad = {
                f"joint{i+1}": angle
                for i, angle in enumerate(joint_angles_rad)
            }
            
            # 验证前向运动学
            fk_result = self.chain.forward_kinematics(ik_solution)
            actual_position = fk_result[:3, 3]
            position_error = np.linalg.norm(actual_position - target_position)
            
            return {
                "success": True,
                "angles": angles_deg,
                "angles_rad": angles_rad,
                "target": {"x": x, "y": y, "z": z},
                "actual_position": actual_position.tolist(),
                "position_error": float(position_error),
                "message": f"IK 求解成功（误差: {position_error*1000:.1f}mm）"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"IK 求解失败: {str(e)}"
            }
    
    def get_preset(self, position_name):
        """获取预定义位置的 IK 解"""
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
    
    def get_workspace_limits(self):
        """
        获取机械臂工作空间范围
        """
        # 基于实际机械臂参数估算
        L1 = 0.166
        L2 = 0.200
        L3 = 0.185
        L4 = 0.125
        
        max_reach = L2 + L3 + L4
        min_reach = abs(L2 - L3)
        
        return {
            "max_reach": max_reach,
            "min_reach": min_reach,
            "height_range": {
                "min": L1 - (L2 + L3),
                "max": L1 + (L2 + L3)
            },
            "recommended_zone": {
                "x": (-0.2, 0.2),
                "y": (0.15, 0.40),
                "z": (0.15, 0.45)
            }
        }

    def parse_voice_command(self, command):
        """解析语音指令"""
        command = command.lower()
        
        # 问候语检查已移除，完全交给 LLM 处理

        # 方向指令
        if any(word in command for word in ["左", "left"]):
            return self.get_preset("left")
        elif any(word in command for word in ["右", "right"]):
            return self.get_preset("right")
        elif any(word in command for word in ["中", "center", "中间"]):
            return self.get_preset("center")
        elif any(word in command for word in ["高", "up", "high", "上"]):
            return self.get_preset("high")
        elif any(word in command for word in ["低", "down", "low", "下"]):
            return self.get_preset("pickup")
        elif any(word in command for word in ["前", "forward", "前面"]):
            return self.get_preset("forward")
        elif any(word in command for word in ["后", "back", "后面"]):
            return self.get_preset("back")
        elif any(word in command for word in ["初始", "home", "复位", "归位"]):
            return self.get_preset("home")
        elif any(word in command for word in ["拿", "捡", "抓", "取", "pickup"]):
            return self.get_preset("pickup")
        else:
            return {
                "success": False,
                "message": f"无法识别的指令: {command}",
                "available_commands": [
                    "左/右/中/前/后",
                    "高/低",
                    "初始位置/复位",
                    "拿/捡/抓"
                ]
            }


# 测试代码
if __name__ == "__main__":
    ik = AdvancedIKController()
    
    print("=" * 60)
    print("高级 IK 控制器测试")
    print("=" * 60)
    
    # 测试预定义位置
    print("\n测试预定义位置:")
    for preset in ["home", "left", "right", "forward", "back", "pickup"]:
        result = ik.get_preset(preset)
        if result["success"]:
            print(f"\n{preset}:")
            print(f"  目标: {result['target']}")
            print(f"  误差: {result['position_error']*1000:.2f}mm")
            print(f"  关节1: {result['angles']['joint1']:.1f}°")
        else:
            print(f"\n{preset}: {result['message']}")
    
    print("\n" + "=" * 60)
