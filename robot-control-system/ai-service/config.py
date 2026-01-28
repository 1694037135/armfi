import os
import json

def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "config.json")
    cfg_file = _read_json(json_path)
    def _get(name, default=None):
        v = os.environ.get(name)
        if v is None:
            v = cfg_file.get(name, default)
        return v
    max_retries = _get("MAX_RETRIES", 3)
    try:
        max_retries = int(max_retries)
    except:
        max_retries = 3
    proxy = _get("HTTP_PROXY")
    if proxy == "":
        proxy = None

    return {
        "GEMINI_API_KEY": _get("GEMINI_API_KEY", "").strip(),
        "GEMINI_MODEL": _get("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        "LLM_BASE_URL": _get("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").strip(),
        # 多阶段路由模型
        "MODEL_FILTER": _get("MODEL_FILTER", ""),      # Step1: 意图分类 (Doubao-lite)
        "MODEL_VISION": _get("MODEL_VISION", ""),      # Step2: 视觉理解
        "MODEL_EMBEDDING": _get("MODEL_EMBEDDING", ""), # Step3: 向量检索
        "MODEL_DECISION": _get("MODEL_DECISION", ""),  # Step4: 决策大脑 (DeepSeek)
        "APPBUILDER_TOKEN": _get("APPBUILDER_TOKEN"),
        "HTTP_PROXY": proxy,
        "MAX_RETRIES": max_retries,
        "IP_CAMERA_URL": _get("IP_CAMERA_URL", "http://192.168.1.100:8080"),  # 手机IP Camera地址
        # 串口通信配置
        "SERIAL_ENABLED": _get("SERIAL_ENABLED", False),
        "SERIAL_PORT": _get("SERIAL_PORT", "COM3"),
        "SERIAL_BAUDRATE": _get("SERIAL_BAUDRATE", 115200),
        "SERIAL_TIMEOUT": _get("SERIAL_TIMEOUT", 0.5),
        "SERIAL_HANDSHAKE": _get("SERIAL_HANDSHAKE", "remote_enable"),
        "SERIAL_NEWLINE": _get("SERIAL_NEWLINE", "\n"),
    }

def build_gemini_generate_url(model, api_key):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

