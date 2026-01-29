"""
机械臂 Skills 系统
封装此模块供 LLM 调用，实现"函数调用"式控制
"""
import logging
import json
from advanced_ik import AdvancedIKController

logger = logging.getLogger(__name__)

class RobotSkills:
    def __init__(self, ik_controller=None):
        self.ik_controller = ik_controller or AdvancedIKController()
        logger.info("✅ RobotSkills 系统已初始化")

    def get_skill_descriptions(self):
        """返回供 LLM System Prompt 使用的技能描述"""
        return """
## 🔧 可用工具 (Tools):
你拥有以下 Python 函数来控制机械臂。请在 JSON 的 "skill" 字段中指定要调用的函数名，并在 "args" 中传入参数。

1. **control_joint(joint_index, angle, current_angles)**
   - 功能: 控制单个关节旋转
   - 参数:
     - joint_index (int): 关节序号 1-6
     - angle (float): 目标角度 (度)
     - current_angles (list): 当前所有关节角度 [j1, j2, j3, j4, j5, j6]，用于保持其他关节不动
   - 示例: "基座转到90度" -> {"skill": "control_joint", "args": {"joint_index": 1, "angle": 90, "current_angles": [...]}}

2. **control_multiple_joints(target_angles_dict, current_angles)**
   - 功能: 同时控制多个关节
   - 参数:
     - target_angles_dict (dict): 目标关节角度字典，键为关节序号(1-6)，值为角度。例如 {"1": 90, "2": 30}
     - current_angles (list): 当前所有关节角度
   - 示例: "基座转到90度，大臂30度" -> {"skill": "control_multiple_joints", "args": {"target_angles_dict": {"1": 90, "2": 30}, "current_angles": [...]}}

3. **move_to(x, y, z)**
   - 功能: IK控制，将末端移动到指定坐标
   - 参数: x, y, z (float) 单位米
   - 示例: "移动到坐标 0.2, 0.2, 0.2" -> {"skill": "move_to", "args": {"x": 0.2, "y": 0.2, "z": 0.2}}

4. **apply_preset(name)**
   - 功能: 移动到预设位置
   - 参数: name (str) -> "home"(复位), "left", "right", "center", "high", "pickup", "forward"
   - 示例: "复位" -> {"skill": "apply_preset", "args": {"name": "home"}}

5. **perform_action(action_name)**
   - 功能: 执行复杂动作序列
   - 参数: action_name (str) -> "wave"(挥手), "nod"(点头), "spin"(转圈), "dance"(跳舞)
   - 示例: "挥手" -> {"skill": "perform_action", "args": {"action_name": "wave"}}
"""

    def execute(self, skill_name, **kwargs):
        """
        统一执行入口
        :param skill_name: 函数名
        :param kwargs: 参数字典
        :return: {success, response, angles?, sequence?, action?}
        """
        if not skill_name:
            return {"success": False, "error": "No skill name provided"}
            
        method = getattr(self, skill_name, None)
        if not method:
            return {"success": False, "error": f"Unknown skill: {skill_name}"}
            
        try:
            logger.info(f"🛠️ 执行技能: {skill_name} params={kwargs}")
            return method(**kwargs)
        except Exception as e:
            logger.error(f"❌ 技能执行失败: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 具体技能实现 ====================

    def control_joint(self, joint_index, angle, current_angles=None, **kwargs):
        """控制单个关节"""
        try:
            joint_idx = int(joint_index) - 1 # 1-based -> 0-based
            target_angle = float(angle)
            
            # 使用传入的当前角度，否则默认全0
            current = current_angles or [0, 0, 0, 0, 0, 0]
            if len(current) < 6:
                current = [0] * 6
                
            new_angles = list(current)
            
            if 0 <= joint_idx < 6:
                new_angles[joint_idx] = target_angle
                
                return {
                    "success": True,
                    "mode": "work",
                    "action": "control_joint",
                    "response": f"好的，正在调整关节{joint_index}到{target_angle}度",
                    "angles": {f"joint{i+1}": a for i, a in enumerate(new_angles)}
                }
            else:
                return {"success": False, "error": f"无效关节索引: {joint_index}"}
        except Exception as e:
            return {"success": False, "error": f"关节控制失败: {str(e)}"}

    def control_multiple_joints(self, target_angles_dict, current_angles=None, **kwargs):
        """同时控制多个关节"""
        try:
            # 使用传入的当前角度，否则默认全0
            current = current_angles or [0, 0, 0, 0, 0, 0]
            if len(current) < 6:
                current = [0] * 6
                
            new_angles = list(current)
            
            updated_joints = []
            
            for index_str, angle in target_angles_dict.items():
                try:
                    joint_idx = int(index_str) - 1 # 1-based -> 0-based
                    target_angle = float(angle)
                    
                    if 0 <= joint_idx < 6:
                        new_angles[joint_idx] = target_angle
                        updated_joints.append(f"关节{index_str}={target_angle}度")
                except ValueError:
                    continue
            
            if not updated_joints:
                return {"success": False, "error": "没有有效的关节目标"}

            return {
                "success": True,
                "mode": "work",
                "action": "control_multiple_joints",
                "response": f"好的，正在调整: {', '.join(updated_joints)}",
                "angles": {f"joint{i+1}": a for i, a in enumerate(new_angles)}
            }
        except Exception as e:
            return {"success": False, "error": f"多关节控制失败: {str(e)}"}

    def move_to(self, x, y, z, current_angles=None, **kwargs):
        """移动到坐标"""
        ik_result = self.ik_controller.calculate_ik(x, y, z)
        if ik_result["success"]:
            return {
                "success": True,
                "mode": "work",
                "action": "move_to",
                "response": "正在移动到目标位置",
                "angles": ik_result["angles"],
                "target": [x, y, z]
            }
        else:
            return {
                "success": False, 
                "mode": "chat",
                "response": f"无法移动到目标位置: {ik_result['message']}"
            }

    def apply_preset(self, name, current_angles=None, **kwargs):
        """应用预设位置"""
        ik_result = self.ik_controller.get_preset(name)
        if ik_result["success"]:
            return {
                "success": True, 
                "mode": "work", 
                "action": name,
                "response": f"正在移动到{name}位置",
                "angles": ik_result["angles"]
            }
        else:
            return {
                "success": False, 
                "mode": "chat",
                "response": f"未知位置: {name}"
            }

    def perform_action(self, action_name, current_angles=None, **kwargs):
        """执行动作序列"""
        # 动作序列其实是在前端定义的，后端只需要返回 action name
        # 前端收到 action 会去查 actionLibrary
        return {
            "success": True,
            "mode": "chat", # 动作序列由前端调度，后端不直接发angles
            "action": action_name,
            "response": f"开始{action_name}",
            "sequence": None # 可以扩展为后端返回 keyframes
        }
