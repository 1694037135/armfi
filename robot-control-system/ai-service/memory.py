"""
🧠 对话记忆管理系统
3层架构：RAM(当前) + JSON(历史) + Vector(语义检索)
"""
import json
import os
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================
MEMORY_DIR = "E:/zero-robotic-arm/robot-control-system/ai-service"
HISTORY_FILE = os.path.join(MEMORY_DIR, "chat_history.json")
MAX_RAM_MESSAGES = 20  # RAM中保留最近20条
MAX_HISTORY_MESSAGES = 200  # JSON中保留最近200条
SUMMARY_THRESHOLD = 10  # 每10条消息触发一次总结

# ============================================================
# 内存存储 (当前会话)
# ============================================================
class ConversationMemory:
    """双层记忆系统"""
    
    def __init__(self):
        self.ram_messages: List[Dict] = []  # 当前会话 (完整)
        self.summary: str = ""  # AI总结的历史精华
        self.message_count = 0
        self._load_history()
    
    def _load_history(self):
        """启动时加载历史记录"""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.summary = data.get("summary", "")
                    # 加载最近几条到RAM
                    history = data.get("messages", [])[-5:]
                    self.ram_messages = history
                    logger.info(f"✅ 加载历史记忆: {len(history)}条, 总结: {len(self.summary)}字")
        except Exception as e:
            logger.warning(f"加载历史记忆失败: {e}")
    
    def add_message(self, role: str, content: str):
        """添加消息到记忆"""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.ram_messages.append(msg)
        self.message_count += 1
        
        # 限制RAM大小
        if len(self.ram_messages) > MAX_RAM_MESSAGES:
            self.ram_messages = self.ram_messages[-MAX_RAM_MESSAGES:]
        
        # 异步保存到文件
        self._save_to_file(msg)
    
    def _save_to_file(self, new_msg: Dict):
        """保存到JSON文件"""
        try:
            # 读取现有历史
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    history = data.get("messages", [])
            
            # 追加新消息
            history.append(new_msg)
            
            # 限制大小
            if len(history) > MAX_HISTORY_MESSAGES:
                history = history[-MAX_HISTORY_MESSAGES:]
            
            # 保存
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "summary": self.summary,
                    "messages": history,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存历史失败: {e}")
    
    def get_context_for_llm(self) -> List[Dict]:
        """获取给LLM的上下文（包含总结+最近消息）"""
        context = []
        
        # 1. 如果有历史总结，作为系统消息注入
        if self.summary:
            context.append({
                "role": "system",
                "content": f"[历史对话总结]: {self.summary}"
            })
        
        # 2. 添加最近的对话
        for msg in self.ram_messages[-10:]:  # 最近10条
            context.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return context
    
    def needs_summary(self) -> bool:
        """是否需要触发总结"""
        return self.message_count >= SUMMARY_THRESHOLD and self.message_count % SUMMARY_THRESHOLD == 0
    
    def update_summary(self, new_summary: str):
        """更新总结"""
        self.summary = new_summary
        logger.info(f"📝 更新记忆总结: {new_summary[:50]}...")
        
        # 保存总结到文件
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"messages": []}
            
            data["summary"] = new_summary
            data["summary_updated_at"] = datetime.now().isoformat()
            
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存总结失败: {e}")
    
    def get_recent_for_summary(self) -> str:
        """获取最近对话用于生成总结"""
        recent = self.ram_messages[-15:]  # 最近15条
        lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "Zero"
            lines.append(f"{role}: {msg['content'][:100]}")
        return "\n".join(lines)
    
    def clear_ram(self):
        """清空RAM（保留总结）"""
        self.ram_messages = []
        self.message_count = 0


# 全局单例
memory = ConversationMemory()


def get_memory() -> ConversationMemory:
    """获取记忆管理器"""
    return memory


# ============================================================
# 总结生成提示词
# ============================================================
SUMMARY_PROMPT = """你是记忆压缩助手。请将以下对话精炼成一句话总结，保留关键信息：
- 用户的偏好和习惯
- 重要的任务或目标
- 机械臂执行过的动作

对话内容:
{conversation}

旧总结(如有): {old_summary}

请输出新的总结（一句话，不超过100字）:"""
