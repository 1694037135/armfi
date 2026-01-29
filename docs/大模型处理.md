# LLM 多模型路由系统

## 📋 概述

为了提升响应速度和降低成本，AI 服务采用了**多模型智能路由**架构，根据任务类型调用不同的 LLM 模型。

## 🏗️ 架构设计

```
用户输入
    ↓
【Step 1】MODEL_FILTER (Doubao-lite)
    ↓
   意图分类 (chat/work/vision)
    ├─→ chat   → 预设回复 或 轻量模型 (Doubao-lite)  ⚡ 快速
    ├─→ work   → MODEL_DECISION (DeepSeek)            🧠 智能
    └─→ vision → MODEL_VISION (视觉理解)              👁️ 视觉
```

## 🎯 模型分工

| 模型 | 用途 | 特点 | 配置字段 |
|------|------|------|----------|
| **MODEL_FILTER** | 意图分类 | 快速、成本低 | `MODEL_FILTER` |
| **MODEL_DECISION** | 工作决策 | 智能、推理强 | `MODEL_DECISION` |
| **MODEL_VISION** | 视觉理解 | 多模态 | `MODEL_VISION` |
| **MODEL_EMBEDDING** | 向量检索 | 上下文理解 | `MODEL_EMBEDDING` |

## ⚡ 性能提升

| 场景 | 之前 | 现在 | 提升 |
|------|------|------|------|
| 简单聊天 | ~2-3s | ~50ms | **60倍** |
| 工作指令 | ~2-3s | ~1-2s | **2倍** |

## 🔧 配置

在 `config.json` 中配置各个模型：

```json
{
  "GEMINI_API_KEY": "your-api-key",
  "LLM_BASE_URL": "https://ark.cn-beijing.volces.com/api/v3",
  "MODEL_FILTER": "ep-20260117224712-pqd89",      
  "MODEL_VISION": "ep-20260117224211-5kpj8",      
  "MODEL_EMBEDDING": "ep-20260117224959-bhtrx",   
  "MODEL_DECISION": "ep-m-20260117185846-7hksj"   
}
```

## 📊 路由逻辑

### 1. 意图分类（Step 1）

使用 `MODEL_FILTER` 快速判断用户意图：

- **chat**: 普通聊天、问候、提问
- **work**: 控制机械臂的指令（移动、复位、抓取等）
- **vision**: 需要视觉识别的任务（看、识别物体等）

### 2. 分类处理（Step 2）

#### Chat 模式（快速响应）

1. **优先使用预设回复**（~10ms）
   - "你好" → 预设回复
   - "介绍一下自己" → 预设回复
   
2. **使用轻量模型** `MODEL_FILTER`（~200ms）
   - 其他聊天内容

#### Work 模式（智能决策）

使用 `MODEL_DECISION` (DeepSeek) 处理：
- 解析用户指令
- 选择合适的 Skill
- 生成参数

#### Vision 模式（视觉理解）

使用 `MODEL_VISION`：
- 结合 IP Camera
- YOLO 物体检测
- 场景理解

## 🚀 使用示例

### Python 代码

```python
from llm_router import LLMRouter

# 初始化路由器
router = LLMRouter(config)

# 意图分类
intent = await router.classify_intent("介绍一下自己")  # → "chat"

# 聊天处理
result = await router.handle_chat("你好")
# → {"success": True, "mode": "chat", "response": "你好呀！...", "fast": True}

# 工作处理
result = await router.handle_work("复位", skills_description)
# → {"success": True, "mode": "work", "skill": "apply_preset", ...}
```

### API 调用

```bash
curl -X POST http://localhost:5000/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "介绍一下自己"}'
```

## 🔄 扩展计划

### 当前已实现

- ✅ 意图分类路由
- ✅ Chat 模式（预设回复 + 轻量模型）
- ✅ Work 模式（DeepSeek 决策）

### 待实现

- ⏳ Vision 模式（IP Camera 集成）
- ⏳ Embedding 模式（对话历史检索）
- ⏳ 多轮对话上下文管理
- ⏳ 用户偏好学习

## 📝 注意事项

1. **网络依赖**: 需要稳定的网络连接访问 LLM API
2. **降级策略**: 如果 `MODEL_FILTER` 未配置，会使用关键词匹配
3. **缓存机制**: 预设回复无需调用 LLM，极速响应
4. **错误处理**: 如果某个模型调用失败，会返回友好的错误信息

## 🐛 调试

查看路由日志：

```bash
# 启动服务后，查看日志
INFO: 🔍 [Step 1] 意图分类中...
INFO: ✅ 意图分类: chat
INFO: 💬 [Chat Mode] 处理聊天消息...
INFO: ✅ 使用预设回复
```

## 📚 相关文件

- `llm_router.py` - 路由器核心实现
- `main.py` - `/api/llm/chat` 接口
- `config.json` - 模型配置
- `skills.py` - 技能系统

---

**最后更新**: 2026-01-29
