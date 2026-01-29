"""
LLM 多模型路由系统
实现智能路由，根据任务类型调用不同的模型
"""
import logging
import httpx
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMRouter:
    """
    多模型路由管理器
    
    模型分工：
    - MODEL_FILTER: 快速意图分类（chat/work/vision）- Doubao-lite
    - MODEL_DECISION: 工作指令决策 - DeepSeek
    - MODEL_VISION: 视觉理解
    - MODEL_EMBEDDING: 向量检索/上下文理解
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("GEMINI_API_KEY")
        self.base_url = config.get("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        self.api_url = f"{self.base_url}/chat/completions"
        
        # 四个模型 ID
        self.model_filter = config.get("MODEL_FILTER")      # 意图分类
        self.model_decision = config.get("MODEL_DECISION")  # DeepSeek 决策
        self.model_vision = config.get("MODEL_VISION")      # 视觉理解
        self.model_embedding = config.get("MODEL_EMBEDDING") # 向量检索
        
        # 代理配置
        self.proxy_url = config.get("HTTP_PROXY")
        
        logger.info(f"🚀 LLM路由器初始化完成")
        logger.info(f"  - 意图分类: {self.model_filter or 'N/A'}")
        logger.info(f"  - 决策大脑: {self.model_decision or 'N/A'}")
        logger.info(f"  - 视觉理解: {self.model_vision or 'N/A'}")
        logger.info(f"  - 向量检索: {self.model_embedding or 'N/A'}")
    
    async def _call_llm(
        self, 
        model: str, 
        messages: list, 
        temperature: float = 0.7,
        timeout: float = 10.0
    ) -> Optional[str]:
        """
        调用 LLM API
        
        Args:
            model: 模型 ID
            messages: 消息列表
            temperature: 温度参数
            timeout: 超时时间（秒）
        
        Returns:
            LLM 响应内容，失败返回 None
        """
        if not model:
            logger.error("模型 ID 为空，无法调用")
            return None
            
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        # 配置代理
        timeout_obj = httpx.Timeout(timeout, connect=5.0)
        if self.proxy_url:
            client_args = {
                "mounts": {
                    "http://": httpx.HTTPTransport(proxy=self.proxy_url),
                    "https://": httpx.HTTPTransport(proxy=self.proxy_url)
                }
            }
        else:
            client_args = {"trust_env": False}
        
        try:
            async with httpx.AsyncClient(timeout=timeout_obj, **client_args) as client:
                resp = await client.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return content.strip()
                else:
                    logger.error(f"LLM API 错误: {resp.status_code} - {resp.text}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"LLM 调用超时 (model={model}, timeout={timeout}s)")
            return None
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None
    
    async def classify_intent(self, user_message: str) -> str:
        """
        【Step 1】意图分类
        
        使用轻量模型 (MODEL_FILTER) 快速判断用户意图
        
        Args:
            user_message: 用户输入
        
        Returns:
            意图类型: 'chat' | 'work' | 'vision'
        """
        # 关键词判断作为 fallback
        def keyword_classify(msg: str) -> str:
            work_keywords = ["移动", "复位", "转到", "关节", "控制", "拿", "捡", "抓", "挥手", "点头", "旋转"]
            vision_keywords = ["看", "识别", "检测", "摄像头", "视觉", "图像", "拍照"]
            
            result_intent = "chat"
            if any(kw in msg for kw in vision_keywords):
                result_intent = "vision"
            elif any(kw in msg for kw in work_keywords):
                result_intent = "work"
            
            logger.info(f"🔑 [Keyword] Classification: {result_intent}")
            return result_intent
        
        # [Fast Path] 优先使用关键词快速分类，避开高延迟 LLM
        # 如果关键词明确指示了 work 或 vision，直接返回，不再调用 LLM
        fast_intent = keyword_classify(user_message)
        if fast_intent in ["work", "vision"]:
            logger.info(f"⚡ [Fast Path] Intent detected: {fast_intent} (Skipping LLM)")
            return fast_intent
        
        if not self.model_filter:
            # 如果没有配置分类模型，使用关键词判断
            logger.warning("未配置 MODEL_FILTER，使用关键词判断")
            return keyword_classify(user_message)
        
        # 使用 LLM 分类
        classify_prompt = f"""请判断用户消息的意图类型，只返回一个词：chat、work 或 vision。

分类标准：
- chat: 普通聊天、问候、提问等
- work: 控制机械臂的指令（移动、复位、抓取等）
- vision: 需要视觉识别的任务（看、识别物体等）

用户消息: "{user_message}"

意图类型:"""
        
        messages = [{"role": "user", "content": classify_prompt}]
        
        logger.info(f"🔍 [Step 1] 意图分类中...")
        result = await self._call_llm(
            model=self.model_filter,
            messages=messages,
            temperature=0.3,  # 低温度，更确定性
            timeout=30.0  # 增加超时时间以适应慢速 API (实测 >13s)
        )
        
        logger.info(f"🔍 [Step 1] Classification Result: {result}")
        
        if result:
            intent = result.lower().strip()
            if intent in ["chat", "work", "vision"]:
                logger.info(f"✅ 意图分类: {intent}")
                return intent
            else:
                logger.warning(f"意图分类结果异常: {result}，使用关键词判断")
                return keyword_classify(user_message)
        else:
            # LLM 调用失败，使用关键词判断
            logger.warning("意图分类失败，使用关键词判断")
            return keyword_classify(user_message)
    
    async def handle_chat(self, user_message: str) -> Dict[str, Any]:
        """
        【聊天模式】快速响应
        
        对于简单聊天，可以使用预设回复或轻量模型
        """
        logger.info("💬 [Chat Mode] 处理聊天消息...")
        
        # 预设回复（快速响应）
        quick_responses = {
            "你好": "你好呀！我是机械臂助手Zero。有什么可以帮你的吗？",
            "介绍一下自己": "你好！我是Zero机械臂助手，一个由6个关节组成的智能机械臂。我可以执行各种精确的控制任务，比如移动到指定位置、调整关节角度、执行预设动作等。有什么需要我帮忙的吗？",
            "你能做什么": "我可以帮你控制机械臂！比如移动到指定位置、调整关节角度、执行预设动作（复位、向左、向右等），还可以执行挥手、点头等表演动作。告诉我你想让我做什么吧！",
            "谢谢": "不客气！随时为你服务！😊"
        }
        
        # 检查预设回复
        for key, response in quick_responses.items():
            if key in user_message:
                logger.info(f"✅ 使用预设回复")
                return {
                    "success": True,
                    "mode": "chat",
                    "response": response,
                    "fast": True  # 标记为快速响应
                }
        
        # 使用轻量模型（MODEL_FILTER）处理聊天
        chat_prompt = f"""你是机械臂助手Zero，请用友好的语气回复用户。保持简洁。

用户: {user_message}

回复:"""
        
        messages = [{"role": "user", "content": chat_prompt}]
        
        result = await self._call_llm(
            model=self.model_filter,  # 使用轻量模型
            messages=messages,
            temperature=0.8,
            timeout=60.0
        )
        
        if result:
            logger.info(f"✅ 聊天回复生成成功")
            return {
                "success": True,
                "mode": "chat",
                "response": result
            }
        else:
            # LLM 超时或失败，返回降级回复
            logger.warning("聊天 LLM 调用失败，使用降级回复")
            fallback_response = "我现在有点忙，请稍后再试。或者你可以告诉我具体的控制指令，比如'复位'、'向左移动'等。"
            return {
                "success": True,  # 改为 True，避免前端显示错误
                "mode": "chat",
                "response": fallback_response,
                "fallback": True  # 标记为降级响应
            }
    
    async def handle_work(
        self, 
        user_message: str, 
        skills_description: str,
        current_angles: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        【工作模式】使用 DeepSeek 处理工作指令
        
        Args:
            user_message: 用户指令
            skills_description: 技能描述文档
            current_angles: 当前关节角度
        
        Returns:
            包含 skill 和 args 的结果
        """
        logger.info("⚙️ [Work Mode] 使用 DeepSeek 处理工作指令...")

        # [Fast Path] 常见指令快速通道，避免 LLM 超时
        fast_commands = {
            "点头": {"skill": "perform_action", "args": {"action_name": "nod"}, "response": "好的，执行点头动作"},
            "nod": {"skill": "perform_action", "args": {"action_name": "nod"}, "response": "OK, nodding"},
            "挥手": {"skill": "perform_action", "args": {"action_name": "wave"}, "response": "好的，向大家挥手"},
            "wave": {"skill": "perform_action", "args": {"action_name": "wave"}, "response": "OK, waving"},
            "复位": {"skill": "apply_preset", "args": {"name": "home"}, "response": "正在复位机械臂"},
            "reset": {"skill": "apply_preset", "args": {"name": "home"}, "response": "Resetting robot"},
            "回零": {"skill": "apply_preset", "args": {"name": "home"}, "response": "正在回零"},
            "跳舞": {"skill": "perform_action", "args": {"action_name": "dance"}, "response": "Music! 开始跳舞！"},
            "转圈": {"skill": "perform_action", "args": {"action_name": "spin"}, "response": "开始旋转"},
        }

        for key, cmd in fast_commands.items():
            if key in user_message or (key.lower() in user_message.lower()):
                logger.info(f"⚡ [Fast Path] Work command detected: {key}")
                # 注入 current_angles 如果需要
                if current_angles and "args" in cmd:
                    cmd["args"]["current_angles"] = current_angles
                return {
                    "success": True,
                    "mode": "work",
                    **cmd
                }
        
        system_prompt = f"""你是机械臂助手Zero。
{skills_description}

## 任务:
请根据用户指令选择合适的工具(Skill)来控制机械臂。

## 响应格式 (JSON):
必须返回标准的 JSON 格式：
{{
    "mode": "work",
    "response": "给用户的回复",
    "skill": "要调用的函数名",
    "args": {{ "参数名": 值 }}
}}

## 示例:
- 用户: "基座转到90度"
  响应: {{"mode": "work", "response": "好的，正在调整基座", "skill": "control_joint", "args": {{"joint_index": 1, "angle": 90}}}}
- 用户: "复位"
  响应: {{"mode": "work", "response": "正在复位", "skill": "apply_preset", "args": {{"name": "home"}}}}

只返回 JSON，不要其他内容。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        result = await self._call_llm(
            model=self.model_decision,  # 使用 DeepSeek
            messages=messages,
            temperature=0.7,
            timeout=90.0  # 允许更长时间
        )
        
        if result:
            try:
                # 清理 JSON
                clean_result = result.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_result)
                
                logger.info(f"✅ 工作指令解析成功: {parsed.get('skill')}")
                
                # 注入当前角度
                if current_angles and "args" in parsed:
                    parsed["args"]["current_angles"] = current_angles
                
                return {
                    "success": True,
                    **parsed
                }
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {e}, 原始响应: {result}")
                return {
                    "success": False,
                    "error": "工作指令格式错误"
                }
        else:
            return {
                "success": False,
                "error": "工作指令处理失败"
            }
    
    async def handle_vision(
        self, 
        user_message: str, 
        image_data: Optional[str] = None,
        vision_context: str = ""
    ) -> Dict[str, Any]:
        """
        【视觉模式】使用 MODEL_VISION 处理视觉任务
        
        Args:
            user_message: 用户指令
            image_data: Base64 编码的图像数据（可选）
            vision_context: 视觉检测结果描述（如"检测到: 人, 杯子"）
        
        Returns:
            视觉理解结果
        """
        logger.info(f"👁️ [Vision Mode] 处理视觉任务... 上下文: {vision_context}")
        
        if not self.model_vision:
            # 如果没有专门的视觉模型，尝试使用决策模型
            model_to_use = self.model_decision
        else:
            model_to_use = self.model_vision
            
        # 构建 Prompt
        system_prompt = f"""你是机械臂助手Zero，拥有视觉能力。
当前视觉传感器检测到的物体: {vision_context if vision_context else "未检测到任何物体（或者是摄像头未连接）"}。

任务: 根据视觉信息回答用户问题。如果用户问"你在看什么"或"有什么"，请根据检测结果回答。
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        result = await self._call_llm(
            model=model_to_use,
            messages=messages,
            temperature=0.7,
            timeout=45.0
        )
        
        if result:
            return {
                "success": True,
                "mode": "vision",
                "response": result
            }
        else:
            return {
                "success": True, 
                "mode": "vision",
                "response": f"我看不太清... 但我检测到了: {vision_context}" if vision_context else "对不起，我的视觉传感器似乎没有连接好，我看不到画面。"
            }
    
    async def get_embedding(self, text: str) -> Optional[list]:
        """
        获取文本的向量表示（用于上下文检索）
        
        Args:
            text: 输入文本
        
        Returns:
            向量列表，失败返回 None
        """
        if not self.model_embedding:
            logger.warning("未配置 MODEL_EMBEDDING")
            return None
        
        # TODO: 实现 Embedding API 调用
        # 通常需要不同的 API endpoint
        logger.info("🔗 Embedding 功能待实现")
        return None
