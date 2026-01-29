"""
AI服务主程序
提供YOLO8物体检测、语音识别、大模型对话等功能
"""
from fastapi import FastAPI, File, UploadFile, Form, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Set, Sequence
import uvicorn
import cv2
import numpy as np
YOLO = None
import logging
import base64
import json
import asyncio
import httpx
import edge_tts
import pyttsx3
import io
import os
import time
import wave
import math
from config import load_config, build_gemini_generate_url
from serial_transport import SerialConfig, SerialTransport, JointLimits
print("✅✅✅ CODE VERSION CHECK: 2026-01-29 15:25 ✅✅✅")
from llm_router import LLMRouter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="机械臂AI服务")
CONFIG = load_config()
LLM_ENABLED = bool(CONFIG.get("GEMINI_API_KEY"))

# ASR 全局变量
asr_client = None
ASR_ENABLED = False

def init_asr():
    """初始化语音识别服务"""
    global asr_client, ASR_ENABLED
    token = CONFIG.get("APPBUILDER_TOKEN")
    if token:
        try:
            import appbuilder
            os.environ["APPBUILDER_TOKEN"] = token
            asr_client = appbuilder.ASR()
            ASR_ENABLED = True
            logger.info(f"✅ 百度 AppBuilder ASR 初始化成功 (Token: {token[:6]}...)")
        except ImportError:
            logger.error("❌ 未安装 appbuilder-sdk，语音识别不可用")
        except Exception as e:
            logger.error(f"❌ ASR 初始化失败: {e}")
    else:
        logger.warning("⚠️ 未配置 APPBUILDER_TOKEN，语音识别将使用 Mock 模式")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入 IK 控制器
from advanced_ik import AdvancedIKController
from skills import RobotSkills

# 初始化本地 TTS 引擎（Windows SAPI5）
local_tts_engine = None
ik_controller = None
skills = None
llm_router = None  # LLM 路由器
serial_transport: SerialTransport | None = None

# 实体机械臂状态回读（串口）
telemetry_state: Dict[str, object] = {
    "angles_deg": [None] * 6,
    "angles_rad": [None] * 6,
    "error_code": None,
    "raw": None,
    "timestamp": None,
    "serial_mock": True,
    "mode": "simulation",
}
telemetry_clients: Set[WebSocket] = set()
telemetry_task: asyncio.Task | None = None
telemetry_lock = asyncio.Lock()

# 控制模式: "simulation" (仅 3D 模型) 或 "physical" (同时发送串口指令)
control_mode: str = "simulation"


def _snapshot_telemetry() -> Dict[str, object]:
    return {
        "angles_deg": list(telemetry_state.get("angles_deg") or [None] * 6),
        "angles_rad": list(telemetry_state.get("angles_rad") or [None] * 6),
        "error_code": telemetry_state.get("error_code"),
        "raw": telemetry_state.get("raw"),
        "timestamp": telemetry_state.get("timestamp"),
        "serial_mock": telemetry_state.get("serial_mock", True),
        "mode": telemetry_state.get("mode", control_mode),
    }


def _parse_serial_line(line: str) -> Optional[Dict[str, object]]:
    payload: Dict[str, object] | None = None
    text = (line or "").strip()
    if not text:
        logger.debug("Telemetry parse skipped: empty line")
        return None

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            angles: Optional[List[float]] = None
            if "angles_deg" in obj:
                angles = obj.get("angles_deg")
            elif "angles" in obj:
                angles = obj.get("angles")
            elif "angles_rad" in obj:
                try:
                    angles = [float(a) * 180 / math.pi if a is not None else None for a in obj.get("angles_rad", [])]
                except Exception:
                    angles = None

            if angles is not None:
                payload = {
                    "angles_deg": angles,
                    "error_code": obj.get("error_code", obj.get("error")),
                }
    except json.JSONDecodeError as exc:
        logger.debug("Telemetry parse JSON decode failed: %s", exc)
        payload = None

    if payload is None:
        parts = [p.strip() for p in text.split(',') if p.strip() != ""]
        if len(parts) >= 6:
            angles: List[Optional[float]] = []
            for idx in range(6):
                try:
                    angles.append(float(parts[idx]))
                except (ValueError, TypeError):
                    angles.append(None)
            error_value: Optional[object] = None
            if len(parts) > 6:
                extra = parts[6]
                try:
                    error_value = int(extra)
                except ValueError:
                    error_value = extra
            payload = {
                "angles_deg": angles,
                "error_code": error_value,
            }
        else:
            logger.debug("Telemetry parse fallback rejected: insufficient fields (%d)", len(parts))

    if payload is None:
        logger.debug("Telemetry parse failed: %s", text)
        return None

    angles_deg = payload.get("angles_deg")
    if not isinstance(angles_deg, Iterable):
        logger.debug("Telemetry parse invalid angles structure: %r", angles_deg)
        return None

    normalized: List[Optional[float]] = []
    for idx, value in enumerate(angles_deg):
        if idx >= 6:
            break
        if value is None:
            normalized.append(None)
            continue
        try:
            normalized.append(float(value))
        except (TypeError, ValueError):
            normalized.append(None)
    while len(normalized) < 6:
        normalized.append(None)

    payload["angles_deg"] = normalized
    return payload


async def _broadcast_telemetry(payload: Dict[str, object]) -> None:
    if not telemetry_clients:
        return
    stale: List[WebSocket] = []
    for client in list(telemetry_clients):
        try:
            await client.send_json({"type": "telemetry", "data": payload})
        except Exception as exc:
            logger.warning("Telemetry client send failed: %s", exc)
            stale.append(client)
    for client in stale:
        telemetry_clients.discard(client)


async def _apply_telemetry_update(
    angles_deg: Sequence[Optional[float]],
    *,
    error_code: Optional[object] = None,
    raw: Optional[str] = None,
    serial_mock: bool = True,
) -> None:
    angles_list = []
    angles_rad = []
    for angle in angles_deg:
        if angle is None:
            angles_list.append(None)
            angles_rad.append(None)
        else:
            try:
                numeric = float(angle)
            except (TypeError, ValueError):
                numeric = None
            if numeric is None:
                angles_list.append(None)
                angles_rad.append(None)
            else:
                angles_list.append(round(numeric, 2))
                angles_rad.append(numeric * math.pi / 180)

    timestamp = time.time()

    async with telemetry_lock:
        telemetry_state["angles_deg"] = angles_list
        telemetry_state["angles_rad"] = angles_rad
        telemetry_state["error_code"] = error_code
        telemetry_state["raw"] = raw
        telemetry_state["timestamp"] = timestamp
        telemetry_state["serial_mock"] = serial_mock
        telemetry_state["mode"] = control_mode
        payload = _snapshot_telemetry()

    await _broadcast_telemetry(payload)


async def telemetry_loop() -> None:
    phase = 0.0
    logger.info("Telemetry loop started")
    try:
        while True:
            await asyncio.sleep(0.1)  # Reduced to 100ms for better responsiveness
            current_transport = serial_transport
            try:
                if current_transport and not current_transport.mock_mode:
                    # 使用新的 read_status() 方法
                    status = current_transport.read_status()
                    if status:
                        await _apply_telemetry_update(
                            status['angles_deg'],
                            error_code=status.get('error_code', 0),
                            raw=None,
                            serial_mock=False,
                        )
                else:
                    # Mock 模式：生成模拟数据
                    phase += 0.1
                    angles = [round(math.sin(phase + idx * 0.5) * 25, 2) for idx in range(6)]
                    await _apply_telemetry_update(
                        angles,
                        error_code=0,
                        raw="mock",
                        serial_mock=True,
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Telemetry loop error: %s", exc)
    except asyncio.CancelledError:
        logger.info("Telemetry loop cancelled")
    finally:
        logger.info("Telemetry loop stopped")


def init_services():
    """初始化所有服务"""
    global ik_controller, skills, serial_transport, llm_router
    try:
        ik_controller = AdvancedIKController()
        logger.info("[OK] Advanced IK Controller initialized")
        
        skills = RobotSkills(ik_controller)
        logger.info("[OK] Robot Skills System initialized")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize Core Services: {e}")
    
    # 初始化 LLM 路由器
    if LLM_ENABLED:
        try:
            llm_router = LLMRouter(CONFIG)
            logger.info("[OK] LLM Router initialized")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize LLM Router: {e}")
            import traceback
            traceback.print_exc()
            llm_router = None
    else:
        logger.warning("LLM Router not initialized: LLM_ENABLED=False")
        llm_router = None
    
    init_local_tts()
    init_asr()

    # 初始化串口传输层
    try:
        serial_cfg = SerialConfig.from_mapping(CONFIG)
        serial_transport = SerialTransport(serial_cfg, logger=logger)
        if serial_transport.mock_mode:
            logger.info("Serial transport running in mock mode")
        else:
            logger.info("Serial transport initialized on %s", serial_cfg.port)
    except Exception as exc:
        logger.error("Failed to initialize serial transport: %s", exc)
        serial_transport = None

def init_local_tts():
    """初始化本地 TTS 引擎"""
    global local_tts_engine
    try:
        local_tts_engine = pyttsx3.init()
        
        # 配置语音参数
        voices = local_tts_engine.getProperty('voices')
        
        # 尝试找中文语音
        chinese_voice = None
        for voice in voices:
            if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                chinese_voice = voice.id
                logger.info(f"找到中文语音: {voice.name}")
                break
        
        if chinese_voice:
            local_tts_engine.setProperty('voice', chinese_voice)
        
        # 设置语速和音量
        local_tts_engine.setProperty('rate', 180)  # 语速（默认200）
        local_tts_engine.setProperty('volume', 1.0)  # 音量（0.0-1.0）
        
        logger.info("✅ 本地 TTS 引擎初始化成功")
        return True
    except Exception as e:
        logger.error(f"❌ 本地 TTS 初始化失败: {e}")
        return False

yolo_model = None
DETECTION_ENABLED = False
try:
    from ultralytics import YOLO as _YOLO
    YOLO = _YOLO
    logger.info("正在加载YOLO8模型...")
    yolo_model = YOLO('yolov8n.pt')
    DETECTION_ENABLED = True
    logger.info("YOLO8模型加载完成")
except Exception as e:
    logger.error(f"YOLO/torch 初始化失败，检测功能将禁用: {e}")

calibration_points = []
calibration_matrix = None
CALIB_MATRIX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_matrix.json")
CALIB_POINTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_points.json")

def _validate_point(d):
    try:
        u = float(d.get("u"))
        v = float(d.get("v"))
        x = float(d.get("x"))
        y = float(d.get("y"))
        z = float(d.get("z"))
    except:
        return False, None
    if not (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
        return False, None
    return True, {"u": u, "v": v, "x": x, "y": y, "z": z}

def _compute_affine(points):
    import numpy as np
    U = np.array([[p["u"], p["v"], 1.0] for p in points], dtype=np.float64)
    X = np.array([p["x"] for p in points], dtype=np.float64)
    Y = np.array([p["y"] for p in points], dtype=np.float64)
    Z = np.array([p["z"] for p in points], dtype=np.float64)
    ax, _, _, _ = np.linalg.lstsq(U, X, rcond=None)
    ay, _, _, _ = np.linalg.lstsq(U, Y, rcond=None)
    az, _, _, _ = np.linalg.lstsq(U, Z, rcond=None)
    M = np.vstack([ax, ay, az]).tolist()
    U_pred = U
    Xp = U_pred @ ax
    Yp = U_pred @ ay
    Zp = U_pred @ az
    rmse_x = float(np.sqrt(np.mean((Xp - X) ** 2)))
    rmse_y = float(np.sqrt(np.mean((Yp - Y) ** 2)))
    rmse_z = float(np.sqrt(np.mean((Zp - Z) ** 2)))
    rmse = float(np.sqrt(np.mean((Xp - X) ** 2 + (Yp - Y) ** 2 + (Zp - Z) ** 2)))
    return {
        "matrix": M,
        "rmse": {"x": rmse_x, "y": rmse_y, "z": rmse_z, "overall": rmse}
    }

def _apply_matrix(M, u, v):
    ax, ay, az = M
    x = ax[0] * u + ax[1] * v + ax[2]
    y = ay[0] * u + ay[1] * v + ay[2]
    z = az[0] * u + az[1] * v + az[2]
    return {"x": float(x), "y": float(y), "z": float(z)}

@app.post("/api/calibration/add")
async def calibration_add(request: Request):
    try:
        data = await request.json()
        ok, point = _validate_point(data)
        if not ok:
            return {"success": False, "error": "参数无效"}
        calibration_points.append(point)
        try:
            with open(CALIB_POINTS_PATH, "w", encoding="utf-8") as f:
                json.dump({"points": calibration_points}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存标定点失败: {e}")
        return {"success": True, "count": len(calibration_points), "last": point}
    except Exception as e:
        logger.error(f"标定点添加失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/calibration/calculate")
async def calibration_calculate():
    try:
        if len(calibration_points) < 4:
            return {"success": False, "error": "标定点不足，至少需要4个"}
        result = _compute_affine(calibration_points)
        global calibration_matrix
        calibration_matrix = result["matrix"]
        payload = {
            "matrix": calibration_matrix,
            "rmse": result["rmse"],
            "timestamp": int(time.time()),
            "count": len(calibration_points)
        }
        try:
            with open(CALIB_MATRIX_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存标定矩阵失败: {e}")
        return {"success": True, **payload}
    except Exception as e:
        logger.error(f"标定计算失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/calibration/clear")
async def calibration_clear():
    try:
        calibration_points.clear()
        global calibration_matrix
        calibration_matrix = None
        try:
            if os.path.exists(CALIB_POINTS_PATH):
                os.remove(CALIB_POINTS_PATH)
        except:
            pass
        try:
            if os.path.exists(CALIB_MATRIX_PATH):
                os.remove(CALIB_MATRIX_PATH)
        except:
            pass
        return {"success": True}
    except Exception as e:
        logger.error(f"标定清空失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/calibration/apply")
async def calibration_apply(request: Request):
    try:
        data = await request.json()
        u = float(data.get("u"))
        v = float(data.get("v"))
        if calibration_matrix is None:
            try:
                if os.path.exists(CALIB_MATRIX_PATH):
                    with open(CALIB_MATRIX_PATH, "r", encoding="utf-8") as f:
                        obj = json.load(f)
                        if "matrix" in obj:
                            m = obj["matrix"]
                            if isinstance(m, list) and len(m) == 3 and all(isinstance(row, list) and len(row) == 3 for row in m):
                                calibration_matrix = m
            except Exception as e:
                logger.warning(f"加载标定矩阵失败: {e}")
        if calibration_matrix is None:
            return {"success": False, "error": "未计算标定矩阵"}
        pos = _apply_matrix(calibration_matrix, u, v)
        return {"success": True, "position": pos}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================
# ArUco 自动标定 API
# ============================================================

@app.post("/api/calibration/auto_detect")
async def calibration_auto_detect(file: UploadFile = File(...)):
    """从图片中检测 ArUco 码中心点"""
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"success": False, "error": "图片解码失败"}
            
        # 初始化 ArUco 检测
        # 使用 4x4_50 字典作为默认配置
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        
        corners, ids, rejected = detector.detectMarkers(img)
        
        if ids is None or len(ids) == 0:
            return {"success": False, "error": "未检测到 ArUco 标记"}
            
        # 取第一个识别到的标记中心
        marker_corners = corners[0][0] # [[x1,y1], [x2,y2], ...]
        center_x = float(np.mean(marker_corners[:, 0]))
        center_y = float(np.mean(marker_corners[:, 1]))
        
        h, w = img.shape[:2]
        u, v = center_x / w, center_y / h
        
        logger.info(f"ArUco 自动检测成功: ID={ids[0][0]}, uv=({u:.3f}, {v:.3f})")
        
        return {
            "success": True, 
            "id": int(ids[0][0]),
            "u": u, 
            "v": v,
            "x_px": center_x,
            "y_px": center_y
        }
    except Exception as e:
        logger.error(f"ArUco 检测错误: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/calibration/aruco_marker")
async def get_aruco_marker():
    """生成并返回 ArUco 标记图片供用户下载打印"""
    try:
        # 生成 ID 为 0 的 4x4 标记
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker_img = cv2.aruco.generateImageMarker(aruco_dict, 0, 400)
        
        _, buffer = cv2.imencode('.png', marker_img)
        return StreamingResponse(io.BytesIO(buffer), media_type="image/png")
    except Exception as e:
        return {"success": False, "error": str(e)}

class MockCamera:
    """模拟摄像头，生成测试画面"""
    def __init__(self):
        self.width = 640
        self.height = 480
        self.frame_count = 0
        logger.warning("未检测到真实摄像头，使用模拟信号源")

    def read(self):
        # 生成一个移动的色块
        img = np.zeros((self.height, self.width, 3), np.uint8)
        self.frame_count += 1
        
        # 绘制背景
        img[:] = (20, 20, 20)
        
        # 移动的小球
        x = int(self.width / 2 + 100 * np.sin(self.frame_count * 0.1))
        y = int(self.height / 2 + 100 * np.cos(self.frame_count * 0.1))
        
        # 画一个球 (模拟 'sports ball' 或类似物体)
        cv2.circle(img, (x, y), 30, (0, 0, 255), -1) 
        cv2.putText(img, "MOCK CAMERA", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return True, img

    def release(self):
        pass

def get_camera_source():
    """尝试获取可用摄像头"""
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                cap.release()
                logger.info(f"发现可用摄像头: Index {i}")
                return i
            cap.release()
    return None


@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "running",
        "service": "机械臂AI服务",
        "version": "1.0.0"
    }
@app.get("/api/system/status")
async def system_status():
    return {
        "llm_enabled": LLM_ENABLED,
        "gemini_model": CONFIG.get("GEMINI_MODEL"),
        "proxy_configured": bool(CONFIG.get("HTTP_PROXY")),
        "detection_enabled": bool(DETECTION_ENABLED),
        "serial_enabled": bool(CONFIG.get("SERIAL_ENABLED")),
        "serial_mock": serial_transport.mock_mode if serial_transport else True,
    }


@app.get("/api/serial/ports")
async def serial_ports():
    ports = SerialTransport.available_ports()
    return {"ports": ports}


class SerialCommand(BaseModel):
    command: str


@app.post("/api/serial/send")
async def serial_send(cmd: SerialCommand):
    if not serial_transport:
        return {"success": False, "error": "serial transport not initialized"}
    ok = serial_transport.send_command(cmd.command)
    return {"success": ok, "mock": serial_transport.mock_mode}


# ============================================================
# 吸泵/夹爪控制 API
# ============================================================

class PumpControlRequest(BaseModel):
    state: bool  # True=开启, False=关闭


@app.post("/api/pump/control")
async def pump_control(request: PumpControlRequest):
    """
    控制吸泵/夹爪开关
    
    Args:
        state: True=开启吸泵, False=关闭吸泵
    
    Returns:
        成功状态和当前模式信息
    """
    if not serial_transport:
        return {
            "success": False, 
            "error": "serial transport not initialized",
            "mock": True
        }
    
    # 定义吸泵控制指令（根据实际硬件协议调整）
    # 示例协议: "pump_on" / "pump_off"
    command = "pump_on" if request.state else "pump_off"
    
    # 发送指令
    ok = serial_transport.send_command(command)
    
    logger.info(f"吸泵控制: {'开启' if request.state else '关闭'} (mock={serial_transport.mock_mode})")
    
    return {
        "success": ok,
        "state": request.state,
        "command": command,
        "mock": serial_transport.mock_mode,
        "control_mode": control_mode
    }


@app.get("/api/pump/status")
async def pump_status():
    """
    获取吸泵状态
    
    Returns:
        吸泵可用性和当前模式
    """
    return {
        "available": serial_transport is not None,
        "mock": serial_transport.mock_mode if serial_transport else True,
        "control_mode": control_mode,
        "serial_connected": serial_transport is not None and not serial_transport.mock_mode
    }


# ============================================================
# 控制模式管理 API
# ============================================================

class ControlModeRequest(BaseModel):
    mode: str  # "simulation" 或 "physical"


@app.get("/api/control/mode")
async def get_control_mode():
    """获取当前控制模式"""
    return {
        "mode": control_mode,
        "serial_available": serial_transport is not None and not serial_transport.mock_mode
    }


@app.post("/api/control/mode")
async def set_control_mode(request: ControlModeRequest):
    """设置控制模式"""
    global control_mode
    if request.mode not in ("simulation", "physical"):
        return {"success": False, "error": "Invalid mode. Must be 'simulation' or 'physical'"}
    control_mode = request.mode
    logger.info(f"控制模式切换为: {control_mode}")
    return {"success": True, "mode": control_mode}


@app.get("/api/control/hardware_status")
async def get_hardware_status():
    """获取硬件连接状态"""
    return {
        "control_mode": control_mode,
        "serial_enabled": bool(CONFIG.get("SERIAL_ENABLED")),
        "serial_connected": serial_transport is not None and not serial_transport.mock_mode,
        "serial_port": CONFIG.get("SERIAL_PORT"),
        "serial_mock": serial_transport.mock_mode if serial_transport else True,
        "available_ports": SerialTransport.available_ports() if serial_transport else []
    }


def dispatch_angles(angles_deg: list, source: str = "unknown") -> dict:
    """
    统一的角度指令分发器
    - simulation 模式: 仅记录日志
    - physical 模式: 同时发送到串口
    
    Args:
        angles_deg: 6个关节角度（度数）
        source: 指令来源标识
    
    Returns:
        dict: 包含分发结果的字典
    """
    # 验证关节限位
    is_valid, error_msg = JointLimits.validate_angles(angles_deg)
    if not is_valid:
        logger.error(f"[DISPATCH] {source}: 关节限位验证失败 - {error_msg}")
        return {
            "mode": control_mode,
            "source": source,
            "angles": angles_deg,
            "serial_sent": False,
            "serial_mock": True,
            "error": error_msg,
            "validation_failed": True
        }
    
    result = {
        "mode": control_mode,
        "source": source,
        "angles": angles_deg,
        "serial_sent": False,
        "serial_mock": True,
        "validation_failed": False
    }
    
    if control_mode == "physical" and serial_transport:
        ok = serial_transport.send_joint_angles(angles_deg, validate_limits=True)
        result["serial_sent"] = ok
        result["serial_mock"] = serial_transport.mock_mode
        if ok:
            logger.info(f"[DISPATCH] {source}: 串口指令已发送 (mock={serial_transport.mock_mode})")
        else:
            logger.warning(f"[DISPATCH] {source}: 串口指令发送失败")
    else:
        logger.debug(f"[DISPATCH] {source}: 模拟模式，跳过串口发送")
    
    return result


class DispatchAnglesRequest(BaseModel):
    angles: List[float]  # 6个关节角度（度数）
    source: str = "api"


@app.post("/api/control/dispatch")
async def api_dispatch_angles(request: DispatchAnglesRequest):
    """统一指令分发接口 - 根据当前模式路由指令"""
    if len(request.angles) != 6:
        return {"success": False, "error": "angles must contain exactly 6 values"}
    result = dispatch_angles(request.angles, request.source)
    return {"success": True, **result}



@app.on_event("startup")
async def on_startup():
    global telemetry_task
    init_services()
    if not telemetry_task:
        telemetry_task = asyncio.create_task(telemetry_loop())


@app.on_event("shutdown")
async def on_shutdown():
    global telemetry_task
    if telemetry_task:
        telemetry_task.cancel()
        try:
            await telemetry_task
        except Exception:
            pass
        telemetry_task = None
    if serial_transport:
        serial_transport.close()

IP_CAMERA_BASE = CONFIG.get("IP_CAMERA_URL", "http://192.168.1.100:8080")

def generate_frames():
    """视频流生成器 -带重试和多路尝试"""
    # 尝试不同的 URL 后缀
    paths = ["/video", "/", "/videostream.cgi", "/live"]
    cap = None
    is_local = False
    
    # 检查是否配置为本地摄像头 (如 "0" 或 "1")
    if str(IP_CAMERA_BASE).isdigit():
        logger.info(f"使用本地摄像头: Index {IP_CAMERA_BASE}")
        cap = cv2.VideoCapture(int(IP_CAMERA_BASE))
        is_local = True
    else:
        # 尝试 IP 摄像头连接
        for path in paths:
            url = f"{IP_CAMERA_BASE}{path}"
            logger.info(f"尝试连接摄像头: {url}")
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                logger.info(f"成功连接摄像头: {url}")
                break
            cap.release()
    
    # 如果连接失败，尝试本地摄像头 (Fallback)
    if not cap or not cap.isOpened():
        logger.warning(f"无法连接配置的摄像头，尝试本地摄像头(Index 0)...")
        cap = cv2.VideoCapture(0)
        is_local = True
    
    if not cap or not cap.isOpened():
        # 如果都失败了，生成测试画面（红底+时间）
        logger.error("无法打开任何摄像头")
        while True:
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:] = (20, 20, 80) # Dark Red background
            
            # Draw X
            cv2.line(img, (0,0), (640,480), (0,0,255), 5)
            cv2.line(img, (640,0), (0,480), (0,0,255), 5)
            
            cv2.putText(img, "CAMERA DISCONNECTED", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(img, f"Check: {IP_CAMERA_BASE}", (100, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
            
            # Show time
            t_str = time.strftime("%H:%M:%S")
            cv2.putText(img, t_str, (500, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            ret, buffer = cv2.imencode('.jpg', img)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1.0) # Slow update for error screen

    # 正常流循环
    while True:
        success, frame = cap.read()
        if not success:
            logger.warning("读取视频帧失败，尝试重连...")
            cap.release()
            time.sleep(2)
            
            if is_local:
                # 本地摄像头重连
                cap = cv2.VideoCapture(0)
            else:
                # IP 摄像头重连
                cap = cv2.VideoCapture(f"{IP_CAMERA_BASE}/video")
                if not cap.isOpened():
                     cap = cv2.VideoCapture(f"{IP_CAMERA_BASE}/")
                # 如果 IP 摄像头多次失败，可以考虑切换到本地，但这里暂保持尝试配置的源
            continue
            
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.get("/api/video_feed")
async def video_feed():
    """视频流代理接口"""
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/detect")
async def detect_objects(file: UploadFile = File(...)):
    """
    物体检测接口
    接收图片，返回检测到的物体及其位置
    """
    try:
        if not DETECTION_ENABLED or yolo_model is None:
            return {
                "success": False,
                "error": "检测功能不可用：YOLO/torch 未正确安装"
            }
        # 读取图片
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # YOLO检测
        results = yolo_model(img)
        
        # 解析结果
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                class_name = result.names[cls]
                
                detections.append({
                    "class": class_name,
                    "confidence": conf,
                    "bbox": {
                        "x1": x1, "y1": y1,
                        "x2": x2, "y2": y2,
                        "center_x": (x1 + x2) / 2,
                        "center_y": (y1 + y2) / 2
                    }
                })
        
        logger.info(f"检测到 {len(detections)} 个物体")
        return {
            "success": True,
            "count": len(detections),
            "detections": detections
        }
        
    except Exception as e:
        logger.error(f"检测失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/voice/recognize")
async def recognize_voice(audio: UploadFile = File(...)):
    """
    语音识别接口
    集成百度 AppBuilder ASR + Google Speech Fallback
    """
    try:
        # 读取音频文件
        contents = await audio.read()
        logger.info(f"收到语音文件，大小: {len(contents)} bytes")
        
        text = ""
        
        # 1. 尝试百度 AppBuilder
        if ASR_ENABLED and asr_client:
            try:
                # 解析 WAV 参数
                rate = 16000
                frames = contents
                try:
                    with io.BytesIO(contents) as audio_file:
                        with wave.open(audio_file, 'rb') as wav_file:
                            rate = wav_file.getframerate()
                            frames = wav_file.readframes(wav_file.getnframes())
                except:
                    pass
                
                import appbuilder
                content_data = {"audio_format": "wav", "raw_audio": frames, "rate": rate}
                message = appbuilder.Message(content_data)
                
                resp = asr_client.run(message)
                if resp and resp.content and 'result' in resp.content:
                    text = resp.content['result'][0]
                    logger.info(f"Baidu ASR: {text}")
            except Exception as e:
                logger.error(f"Baidu ASR Failed: {e}")

        # 2. Fallback: Google Speech Recognition (if Baidu failed or disabled)
        if not text:
            try:
                import speech_recognition as sr
                import tempfile
                
                # 需要保存为临时文件供 sr 使用
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(contents)
                    tmp_path = tmp.name
                
                try:
                    r = sr.Recognizer()
                    with sr.AudioFile(tmp_path) as source:
                        audio_data = r.record(source)
                        text = r.recognize_google(audio_data, language='zh-CN')
                        logger.info(f"Google ASR: {text}")
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                        
            except ImportError:
                logger.warning("speech_recognition module not found")
            except Exception as e:
                logger.warning(f"Google ASR Failed: {e}")

        # 3. Final Result
        if text:
            return {
                "success": True,
                "text": text,
                "message": "识别成功"
            }
        else:
            return {
                "success": True, # Keep true to avoid frontend error
                "text": "语音识别失败 (Mock)",
                "message": "所有ASR服务均不可用"
            }

    except Exception as e:
        logger.error(f"语音识别接口异常: {e}")
        return {
            "success": False,
            "text": "",
            "message": str(e)
        }


class ChatRequest(BaseModel):
    message: str
    current_pos: Optional[Dict[str, float]] = None
    current_angles: Optional[List[float]] = None  # [Joint1, ..., Joint6] in degrees

class TTSRequest(BaseModel):
    message: str
    voice: str = "zh-CN-XiaoxiaoNeural"  # 默认女声（温柔）
    engine: str = "local"  # 新增：引擎选择 "local" 或 "edge"

@app.post("/api/tts/speak")
async def text_to_speech(request: TTSRequest):
    """
    TTS 语音合成接口 - 支持本地和云端
    
    engine="local": Windows 本地 TTS（零延迟，音质一般）
    engine="edge": Edge TTS（高音质，有延迟）
    """
    try:
        text = request.message
        engine = request.engine
        
        # 本地 TTS（推荐，零延迟）
        if engine == "local":
            logger.info(f"[本地TTS] 播报: {text[:50]}...")
            
            # 使用 Windows PowerShell 的 TTS（更可靠）
            import subprocess
            import tempfile
            import os
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav', mode='w')
            temp_path = temp_file.name
            temp_file.close()
            
            try:
                # 使用 PowerShell 生成语音
                ps_script = f'''
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
$synth.Volume = 100
$synth.SetOutputToWaveFile("{temp_path}")
$synth.Speak("{text}")
$synth.Dispose()
'''
                
                # 执行 PowerShell 脚本
                result = subprocess.run(
                    ['powershell', '-Command', ps_script],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    logger.error(f"[本地TTS] PowerShell 错误: {result.stderr}")
                    return {"success": False, "error": "TTS 生成失败"}
                
                # 读取生成的音频文件
                if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                    logger.error(f"[本地TTS] 音频文件生成失败")
                    return {"success": False, "error": "音频文件为空"}
                
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                # 删除临时文件
                os.unlink(temp_path)
                
                logger.info(f"[本地TTS] ✅ 生成成功，大小: {len(audio_data)} bytes")
                
                return StreamingResponse(
                    io.BytesIO(audio_data),
                    media_type="audio/wav",
                    headers={
                        "Content-Disposition": "inline; filename=speech.wav",
                        "Cache-Control": "no-cache"
                    }
                )
                
            except subprocess.TimeoutExpired:
                logger.error("[本地TTS] 生成超时")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return {"success": False, "error": "TTS 生成超时"}
            except Exception as e:
                logger.error(f"[本地TTS] 错误: {e}")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e
        
        # Edge TTS（云端，高音质）
        elif engine == "edge":
            voice = request.voice
            logger.info(f"[Edge TTS] 请求: {text[:50]}... (voice: {voice})")
            start_time = asyncio.get_event_loop().time()
            
            # 流式生成器
            async def audio_stream():
                """流式生成音频数据"""
                communicate = edge_tts.Communicate(text, voice)
                first_chunk = True
                
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        if first_chunk:
                            elapsed = asyncio.get_event_loop().time() - start_time
                            logger.info(f"[Edge TTS] 首字节延迟: {elapsed:.3f}s")
                            first_chunk = False
                        yield chunk["data"]
            
            return StreamingResponse(
                audio_stream(),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=speech.mp3",
                    "Cache-Control": "no-cache",
                    "Accept-Ranges": "bytes"
                }
            )
        
        else:
            return {"success": False, "error": f"未知引擎: {engine}"}
        
    except Exception as e:
        logger.error(f"[TTS] Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ============================================================
# IK 逆运动学接口
# ============================================================

class IKRequest(BaseModel):
    x: float
    y: float
    z: float

class IKPresetRequest(BaseModel):
    preset: str

@app.post("/api/ik/calculate")
async def calculate_ik(request: IKRequest):
    """
    IK计算接口 - 根据3D坐标计算关节角度
    """
    try:
        if ik_controller is None:
            return {"success": False, "error": "IK控制器未初始化"}
        
        result = ik_controller.calculate_ik(request.x, request.y, request.z)
        logger.info(f"IK计算: ({request.x}, {request.y}, {request.z}) → {result.get('success')}")
        return result
    except Exception as e:
        logger.error(f"IK计算失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/ik/preset")
async def get_ik_preset(request: IKPresetRequest):
    """
    IK预设位置接口 - 获取预定义位置的关节角度
    """
    try:
        if ik_controller is None:
            return {"success": False, "error": "IK控制器未初始化"}
        
        result = ik_controller.get_preset(request.preset)
        logger.info(f"IK预设: {request.preset} → {result.get('success')}")
        return result
    except Exception as e:
        logger.error(f"IK预设失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/ik/voice")
async def ik_voice_command(request: Request):
    """
    IK语音指令接口 - 解析语音指令并返回关节角度
    """
    try:
        data = await request.json()
        command = data.get("command", "")
        
        if ik_controller is None:
            return {"success": False, "error": "IK控制器未初始化"}
        
        result = ik_controller.parse_voice_command(command)
        logger.info(f"IK语音: '{command}' → {result.get('success')}")
        return result
    except Exception as e:
        logger.error(f"IK语音失败: {e}")
        return {"success": False, "error": str(e)}

# ============================================================

# ============================================================
# WebSocket 实时通信端点
# ============================================================

@app.websocket("/ws/mujoco")
async def websocket_mujoco(websocket: WebSocket):
    """WebSocket端点 - 保持连接用于未来实时控制"""
    await websocket.accept()
    logger.info("✅ WebSocket客户端已连接")
    
    try:
        # 1. 发送连接成功消息（包含当前控制模式）
        await websocket.send_json({
            "type": "connected",
            "message": "后端已连接",
            "control_mode": control_mode
        })
        
        # 2. 主循环
        while True:
            # 等待接收JSON消息
            data = await websocket.receive_json()
            
            # 处理指令
            action = data.get("action")
            if action == "ping":
                await websocket.send_json({"type": "pong"})
            elif action == "start":
                logger.info("WS: 收到Start指令")
            elif action == "move_to_angles":
                # 处理关节角度指令
                angles = data.get("angles", [])
                if len(angles) == 6:
                    # 弧度转角度
                    import math
                    angles_deg = [a * 180 / math.pi for a in angles]
                    result = dispatch_angles(angles_deg, "websocket")
                    await websocket.send_json({
                        "type": "dispatch_result",
                        **result
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "angles must contain exactly 6 values"
                    })
            elif action == "set_target":
                # 处理笛卡尔目标位置（需要 IK 计算）
                target = data.get("target", [])
                if len(target) == 3 and ik_controller:
                    x, y, z = target
                    ik_result = ik_controller.calculate_ik(x, y, z)
                    if ik_result.get("success"):
                        angles_deg = [
                            ik_result["angles"].get("joint1", 0),
                            ik_result["angles"].get("joint2", 0),
                            ik_result["angles"].get("joint3", 0),
                            ik_result["angles"].get("joint4", 0),
                            ik_result["angles"].get("joint5", 0),
                            ik_result["angles"].get("joint6", 0),
                        ]
                        result = dispatch_angles(angles_deg, "websocket_ik")
                        await websocket.send_json({
                            "type": "dispatch_result",
                            "ik_success": True,
                            **result
                        })
                    else:
                        await websocket.send_json({
                            "type": "ik_error",
                            "message": ik_result.get("error", "IK calculation failed")
                        })
            elif action == "get_mode":
                # 返回当前控制模式
                await websocket.send_json({
                    "type": "mode_info",
                    "mode": control_mode,
                    "serial_available": serial_transport is not None and not serial_transport.mock_mode
                })
            
            # 这里的sleep不是必须的，但可以防止紧密循环占用
            # await asyncio.sleep(0.01) 
                
    except WebSocketDisconnect:
        logger.info("WebSocket客户端主动断开")
    except Exception as e:
        # 捕获所有其他错误并打印，防止静默失败
        logger.error(f"❌ WebSocket异常: {e}")
        import traceback
        traceback.print_exc()


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    telemetry_clients.add(websocket)
    logger.info("Telemetry client connected (%d total)", len(telemetry_clients))

    try:
        await websocket.send_json({"type": "telemetry_snapshot", "data": _snapshot_telemetry()})
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                logger.debug("Telemetry client message error: %s", exc)
                continue

            action = message.get("action") if isinstance(message, dict) else None
            if action == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("Telemetry client disconnected")
    finally:
        telemetry_clients.discard(websocket)
        logger.debug("Telemetry clients remaining: %d", len(telemetry_clients))


# ============================================================
# LLM 对话接口
# ============================================================

@app.post("/api/llm/chat")
async def chat_with_llm(request: ChatRequest):
    """
    智能对话接口 - 多模型路由系统
    
    流程：
    1. MODEL_FILTER (Doubao-lite) - 快速意图分类
    2. 根据意图路由:
       - chat → 轻量模型或预设回复（快速）
       - work → MODEL_DECISION (DeepSeek) 处理
       - vision → MODEL_VISION 视觉理解
    """
    try:
        user_text = request.message
        if not user_text:
            return {"success": False, "error": "Empty message"}
            
        logger.info(f"收到用户消息: {user_text}")

        if not LLM_ENABLED or not llm_router:
            return {"success": False, "error": "LLM已禁用：未配置 API Key 或路由器未初始化"}
        
        # ========== Step 1: 意图分类 ==========
        intent = await llm_router.classify_intent(user_text)
        logger.info(f"📊 意图分类结果: {intent}")
        
        # ========== Step 2: 根据意图路由 ==========
        if intent == "chat":
            # 聊天模式 - 使用轻量模型或预设回复
            result = await llm_router.handle_chat(user_text)
            return result
            
        elif intent == "work":
            # 工作模式 - 使用 DeepSeek 处理
            skills_desc = skills.get_skill_descriptions()
            result = await llm_router.handle_work(
                user_message=user_text,
                skills_description=skills_desc,
                current_angles=request.current_angles
            )
            
            # 如果成功返回了 skill，执行技能
            if result.get("success") and result.get("skill"):
                skill_name = result["skill"]
                args = result.get("args", {})
                
                # 调用 RobotSkills 执行技能
                skill_result = skills.execute(skill_name, **args)
                
                # 合并 LLM 的回复和技能执行结果
                if "response" in result and "response" not in skill_result:
                    skill_result["response"] = result["response"]
                    
                return skill_result
            
            return result
            
        elif intent == "vision":
            # 视觉模式 - 使用视觉模型
            vision_context = ""
            
            # 如果启用了检测功能且 YOLO 模型已加载
            if DETECTION_ENABLED and yolo_model:
                try:
                    # 尝试从 IP Camera 获取图像
                    ip_camera_url = CONFIG.get("IP_CAMERA_URL")
                    if ip_camera_url:
                        logger.info(f"正在读取摄像头: {ip_camera_url.split('@')[-1]}") # 隐藏密码
                        # 智能判断: 如果是数字则作为本地摄像头索引
                        if str(ip_camera_url).isdigit():
                            cap = cv2.VideoCapture(int(ip_camera_url))
                        else:
                            cap = cv2.VideoCapture(ip_camera_url)
                            
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret:
                                # YOLO 检测
                                results = yolo_model(frame, verbose=False, conf=0.3)
                                
                                # 提取检测到的物体
                                detected_objects = []
                                for result in results:
                                    for box in result.boxes:
                                        cls = int(box.cls[0])
                                        class_name = result.names[cls]
                                        detected_objects.append(class_name)
                                
                                if detected_objects:
                                    # 统计物体数量
                                    from collections import Counter
                                    counts = Counter(detected_objects)
                                    desc_list = [f"{count}个{name}" for name, count in counts.items()]
                                    vision_context = ", ".join(desc_list)
                                    logger.info(f"视觉检测结果: {vision_context}")
                                else:
                                    vision_context = "画面清晰，但未识别到已知物体"
                            else:
                                vision_context = "无法读取摄像头画面"
                            cap.release()
                        else:
                            vision_context = "无法连接到摄像头，请检查网络"
                    else:
                        vision_context = "系统中未配置 IP Camera 地址"
                except Exception as e:
                    logger.error(f"视觉处理异常: {e}")
                    vision_context = f"视觉系统出错: {str(e)}"
            else:
                vision_context = "YOLO模型未加载，无法识别物体"

            result = await llm_router.handle_vision(user_text, vision_context=vision_context)
            return result
            
        else:
            # 未知意图，默认聊天
            result = await llm_router.handle_chat(user_text)
            return result

    except Exception as e:
        logger.error(f"LLM Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ========== TD3 模型全局加载 ==========
td3_model = None
td3_vec_normalize = None

def load_td3_model():
    """
    在服务启动时加载 TD3 模型 (延迟加载以避免启动失败)
    """
    global td3_model, td3_vec_normalize
    
    # 使用绝对路径 (ai-service -> robot-control-system -> zero-robotic-arm)
    import os
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # ai-service
    ROBOT_CONTROL = os.path.dirname(CURRENT_DIR)  # robot-control-system
    PROJECT_ROOT = os.path.dirname(ROBOT_CONTROL)  # zero-robotic-arm
    
    MODEL_PATH = os.path.join(PROJECT_ROOT, "5. Deep_LR", "logs", "best_model", "best_model")
    NORMALIZE_PATH = os.path.join(PROJECT_ROOT, "5. Deep_LR", "logs", "best_model", "vec_normalize.pkl")
    
    logger.info(f"模型路径: {MODEL_PATH}")
    
    try:
        from stable_baselines3 import TD3
        from stable_baselines3.common.vec_env import VecNormalize
        import pickle
        
        logger.info("正在加载 TD3 模型...")
        
        # 加载模型 (不需要环境，仅用于推理)
        td3_model = TD3.load(MODEL_PATH, device="cpu")
        logger.info("TD3 模型加载成功")
        
        # 尝试加载归一化参数
        try:
            with open(NORMALIZE_PATH, 'rb') as f:
                td3_vec_normalize = pickle.load(f)
            logger.info("VecNormalize 参数加载成功")
        except Exception as e:
            logger.warning(f"VecNormalize 加载失败: {e}, 将使用原始观测值")
            td3_vec_normalize = None
            
        return True
    except Exception as e:
        logger.error(f"TD3 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


class TD3PredictRequest(BaseModel):
    """TD3 推理请求"""
    target_pos: list  # 目标位置 [x, y, z]
    joint_angles: list  # 当前关节角度 [6]
    joint_velocities: list = [0, 0, 0, 0, 0, 0]  # 当前关节速度 [6]
    ee_pos: list = [0, 0, 0]  # 当前末端位置 [3]
    ee_vel: list = [0, 0, 0]  # 当前末端速度 [3]
    prev_torque: list = [0, 0, 0, 0, 0, 0]  # 上一时刻扭矩 [6]


@app.post("/api/td3/predict")
async def td3_predict(request: TD3PredictRequest):
    """
    TD3模型推理接口
    输入当前状态，输出关节控制动作（扭矩）
    
    观测空间 (24维):
    - relative_pos (3): 目标位置 - 末端位置
    - joint_angles (6): 当前关节角度
    - joint_velocities (6): 当前关节速度
    - prev_torque (6): 上一时刻扭矩
    - ee_vel (3): 末端速度
    """
    global td3_model, td3_vec_normalize
    
    # 延迟加载模型
    if td3_model is None:
        success = load_td3_model()
        if not success:
            return {
                "success": False,
                "error": "TD3 模型加载失败，请检查模型文件"
            }
    
    try:
        import numpy as np
        
        # 构建观测向量 (24维)
        target_pos = np.array(request.target_pos)
        ee_pos = np.array(request.ee_pos)
        relative_pos = target_pos - ee_pos
        
        observation = np.concatenate([
            relative_pos,                           # 3
            np.array(request.joint_angles),         # 6
            np.array(request.joint_velocities),     # 6
            np.array(request.prev_torque),          # 6
            np.array(request.ee_vel)                # 3
        ]).astype(np.float32)
        
        # 如果有归一化参数，应用归一化
        if td3_vec_normalize is not None:
            try:
                obs_mean = td3_vec_normalize.obs_rms.mean
                obs_var = td3_vec_normalize.obs_rms.var
                observation = (observation - obs_mean) / np.sqrt(obs_var + 1e-8)
                observation = np.clip(observation, -10, 10)
            except:
                pass  # 归一化失败则使用原始值
        
        # 推理
        action, _ = td3_model.predict(observation.reshape(1, -1), deterministic=True)
        action = action.flatten().tolist()
        
        return {
            "success": True,
            "action": action,  # 6维扭矩
            "observation_shape": len(observation)
        }
        
    except Exception as e:
        logger.error(f"TD3 推理失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }




@app.websocket("/ws/camera")
async def websocket_endpoint(websocket: WebSocket):
    """
    实时视觉处理接口 (Sim2Real模式)
    接收客户端发送的 Base64 图片 -> YOLO 检测 -> 返回检测结果
    """
    await websocket.accept()
    logger.info("WebSocket 连接建立 (客户端视觉源)")
    
    try:
        while True:
            # 1. 接收客户端发送的数据 (JSON format: {"image": "base64..."})
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                
                # 检查是否包含图像数据
                if "image" not in data:
                    continue
                    
                image_data = data["image"]
                
                # 2. 解码图片
                # Remove header if present (e.g., "data:image/jpeg;base64,")
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                    
                image_bytes = base64.b64decode(image_data)
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    logger.warning("无法解码图像数据")
                    continue

                # 3. YOLO 检测
                results = yolo_model(frame, verbose=False, conf=0.3)
                
                # 4. 提取检测结果
                detections = []
                for result in results:
                    for box in result.boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        class_name = result.names[cls]
                        detections.append({
                            "class": class_name,
                            "confidence": conf,
                            "bbox": box.xyxy[0].tolist()
                        })
                
                if len(detections) > 0:
                    logger.info(f"检测到: {[d['class'] for d in detections]}")

                # 5. 发送回客户端
                await websocket.send_json({
                    "detections": detections,
                    "processed_ts": data.get("ts", 0)
                })
                
            except json.JSONDecodeError:
                logger.error("无效的 JSON 数据")
            except Exception as e:
                logger.error(f"处理帧失败: {str(e)}")
            
    except WebSocketDisconnect:
        logger.info("WebSocket 连接断开")
    except Exception as e:
        logger.error(f"WebSocket 异常: {str(e)}")


# ========== MuJoCo 后端控制器 ==========

class MuJoCoController:
    """
    MuJoCo 仿真控制器，运行 TD3 策略
    用于后端物理仿真，将关节角度通过 WebSocket 发送给前端
    """
    
    def __init__(self):
        import os
        import sys
        
        # 添加 Deep_LR 路径
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        ROBOT_CONTROL = os.path.dirname(CURRENT_DIR)
        PROJECT_ROOT = os.path.dirname(ROBOT_CONTROL)
        DEEP_LR_PATH = os.path.join(PROJECT_ROOT, "5. Deep_LR")
        
        if DEEP_LR_PATH not in sys.path:
            sys.path.insert(0, DEEP_LR_PATH)
        
        # 切换工作目录以加载 MuJoCo XML
        original_cwd = os.getcwd()
        os.chdir(DEEP_LR_PATH)
        
        try:
            from robot_arm_env import RobotArmEnv
            from stable_baselines3 import TD3
            
            # 创建无渲染模式的环境
            self.env = RobotArmEnv(render_mode=None)
            logger.info("MuJoCo 环境初始化成功")
            
            # 加载 TD3 模型
            MODEL_PATH = os.path.join(DEEP_LR_PATH, "logs", "best_model", "best_model")
            self.td3_model = TD3.load(MODEL_PATH, device="cpu")
            logger.info("TD3 模型加载成功")
            
            self.target_pos = np.array([0.1, -0.25, 0.3])
            self.is_running = False
            self.step_count = 0
            
        finally:
            os.chdir(original_cwd)
    
    def set_target(self, x, y, z):
        """设置目标位置"""
        self.target_pos = np.array([x, y, z])
        self.env.target_pos = self.target_pos
        self.step_count = 0
        logger.info(f"设置目标位置: ({x}, {y}, {z})")
    
    def reset(self):
        """重置环境"""
        self.env.reset()
        self.step_count = 0
    
    def step(self):
        """
        执行一步仿真
        返回: (关节角度列表, 是否完成, 末端位置)
        """
        import mujoco
        
        # 获取观测
        obs = self.env._get_state()
        
        # TD3 推理
        action, _ = self.td3_model.predict(obs.reshape(1, -1), deterministic=True)
        action = action.flatten()
        
        # 执行动作
        _, reward, done, truncated, _ = self.env.step(action)
        self.step_count += 1
        
        # 最大步数限制
        MAX_STEPS = 500
        
        # 获取关节角度 (弧度)
        joint_angles_rad = self.env.data.qpos[:6].tolist()
        
        # 获取末端位置
        ee_site_id = mujoco.mj_name2id(self.env.model, mujoco.mjtObj.mjOBJ_SITE, "ee_site")
        ee_pos = self.env.data.site_xpos[ee_site_id].tolist()
        distance = float(np.linalg.norm(np.array(ee_pos) - self.target_pos))
        
        # 判断是否完成 (达到目标、超时、或步数限制)
        is_done = done or truncated or self.step_count >= MAX_STEPS
        
        return {
            "angles_rad": joint_angles_rad,
            "angles_deg": [a * 180 / 3.14159 for a in joint_angles_rad],
            "ee_pos": ee_pos,
            "target_pos": self.target_pos.tolist(),
            "distance": distance,
            "step": self.step_count,
            "done": is_done,
            "reason": "success" if done else ("max_steps" if self.step_count >= MAX_STEPS else "running")
        }


# 全局 MuJoCo 控制器实例 (延迟初始化)
mujoco_controller = None


@app.websocket("/ws/mujoco")
async def mujoco_control_ws(websocket: WebSocket):
    """
    MuJoCo 实时控制 WebSocket
    
    客户端发送:
    - {"action": "set_target", "target": [x, y, z]}  设置目标
    - {"action": "start"}  开始控制
    - {"action": "stop"}   停止控制
    - {"action": "reset"}  重置环境
    
    服务端推送:
    - {"type": "joint_update", "angles_deg": [...], "ee_pos": [...], ...}
    """
    global mujoco_controller
    
    await websocket.accept()
    logger.info("MuJoCo WebSocket 连接建立")
    
    # 发送连接确认
    await websocket.send_json({"type": "connected"})
    
    # 延迟初始化控制器
    use_mock = False
    mock_target = [0.1, -0.25, 0.3]
    if mujoco_controller is None:
        try:
            mujoco_controller = MuJoCoController()
            logger.info("MuJoCo 控制器初始化成功")
        except Exception as e:
            logger.error(f"MuJoCo 控制器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            logger.warning("使用模拟模式代替真实 MuJoCo 控制器")
            use_mock = True
            await websocket.send_json({"type": "warning", "message": f"MuJoCo 初始化失败，使用模拟模式: {str(e)}"})
    
    is_running = False
    
    try:
        while True:
            # 使用超时接收，以便可以在运行时继续推送
            try:
                raw_data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.03 if is_running else None  # 运行时 30ms 超时
                )
                data = json.loads(raw_data)
                
                action = data.get("action", "")
                
                if action == "set_target":
                    target = data.get("target", [0.1, -0.25, 0.3])
                    if use_mock or mujoco_controller is None:
                        mock_target = target
                        setattr(mujoco_control_ws, '_mock_step', 0)
                    else:
                        mujoco_controller.set_target(*target)
                        mujoco_controller.reset()
                    await websocket.send_json({"type": "target_set", "target": target})
                    
                elif action == "start":
                    is_running = True
                    logger.info("MuJoCo 控制启动")
                    await websocket.send_json({"type": "started"})
                    
                elif action == "stop":
                    is_running = False
                    logger.info("MuJoCo 控制停止")
                    await websocket.send_json({"type": "stopped"})
                    
                elif action == "reset":
                    if use_mock or mujoco_controller is None:
                        setattr(mujoco_control_ws, '_mock_step', 0)
                    else:
                        mujoco_controller.reset()
                    await websocket.send_json({"type": "reset"})
                    
            except asyncio.TimeoutError:
                pass  # 超时继续执行仿真步骤
            
            # 运行仿真
            if is_running:
                try:
                    if use_mock:
                        # 模拟模式：生成假的关节角度
                        import math
                        mock_step_count = getattr(mujoco_control_ws, '_mock_step', 0) + 1
                        mujoco_control_ws._mock_step = mock_step_count
                        
                        # 模拟正弦波运动
                        t = mock_step_count * 0.05
                        result = {
                            "type": "joint_update",
                            "angles_deg": [
                                math.sin(t) * 30,  # 关节1
                                math.sin(t * 0.8) * 45,  # 关节2
                                math.cos(t * 0.6) * 30,  # 关节3
                                math.sin(t * 0.4) * 20,  # 关节4
                                math.cos(t * 0.3) * 25,  # 关节5
                                math.sin(t * 0.2) * 15   # 关节6
                            ],
                            "angles_rad": [0, 0, 0, 0, 0, 0],
                            "ee_pos": [0, 0, 0],
                            "target_pos": mock_target,
                            "distance": 0.1,
                            "step": mock_step_count,
                            "done": mock_step_count >= 500,
                            "reason": "mock"
                        }
                        await websocket.send_json(result)
                        
                        if mock_step_count >= 500:
                            is_running = False
                            await websocket.send_json({
                                "type": "completed",
                                "steps": mock_step_count,
                                "final_distance": 0.1
                            })
                        
                        await asyncio.sleep(0.03)  # ~30 FPS
                    else:
                        result = mujoco_controller.step()
                        result["type"] = "joint_update"
                        await websocket.send_json(result)
                        
                        # 检查是否完成
                        if result["done"]:
                            is_running = False
                            await websocket.send_json({
                                "type": "completed",
                                "steps": result["step"],
                                "final_distance": result["distance"]
                            })
                            logger.info(f"目标达成! 步数: {result['step']}, 距离: {result['distance']:.4f}")
                        
                except Exception as e:
                    logger.error(f"仿真步骤失败: {e}")
                    is_running = False
                    await websocket.send_json({"type": "error", "message": str(e)})
                    
    except WebSocketDisconnect:
        logger.info("MuJoCo WebSocket 连接断开")
    except Exception as e:
        logger.error(f"MuJoCo WebSocket 异常: {e}")


# ========== 简单逆运动学控制器 ==========
from simple_ik import SimpleIKController

# 全局 IK 控制器实例
ik_controller = SimpleIKController()

class IKRequest(BaseModel):
    x: float
    y: float
    z: float

class IKPresetRequest(BaseModel):
    preset: str

class IKVoiceRequest(BaseModel):
    command: str

@app.post("/api/ik/calculate")
async def calculate_ik(request: IKRequest):
    """
    逆运动学计算接口
    输入目标位置(x, y, z)，输出关节角度
    """
    result = ik_controller.calculate_ik(request.x, request.y, request.z)
    return result

@app.post("/api/ik/preset")
async def get_preset_position(request: IKPresetRequest):
    """
    获取预定义位置
    可用位置: home, left, right, center, high, pickup, forward, back
    """
    result = ik_controller.get_preset(request.preset)
    return result

@app.post("/api/ik/voice")
async def parse_voice_command(request: IKVoiceRequest):
    """
    语音指令解析
    将自然语言转换为关节角度
    """
    result = ik_controller.parse_voice_command(request.command)
    return result

@app.get("/api/ik/workspace")
async def get_workspace():
    """
    获取机械臂工作空间范围
    """
    result = ik_controller.get_workspace_limits()
    return result

@app.get("/api/ik/presets")
async def list_presets():
    """
    列出所有预定义位置
    """
    return {
        "success": True,
        "presets": list(ik_controller.presets.keys()),
        "positions": ik_controller.presets
    }


@app.post("/api/llm/generate_action")
async def generate_action_sequence(request: Request):
    """
    使用 Gemini LLM 生成机械臂动作序列
    
    请求体示例:
    {
        "command": "跳个太空舞"
    }
    
    返回示例:
    {
        "success": true,
        "name": "太空舞",
        "keyframes": [
            {"angles": [0, -30, 30, 0, 0, 0], "duration": 500},
            {"angles": [30, -30, 30, 30, 0, 30], "duration": 400},
            ...
        ]
    }
    """
    try:
        data = await request.json()
        user_command = data.get("command", "")
        
        if not user_command:
            return {"success": False, "error": "缺少 command 参数"}
        
        logger.info(f"[LLM] 收到动作生成请求: {user_command}")
        
        # 构建 Prompt
        prompt = f"""你是一个机械臂动作编排专家。请根据用户的指令生成一个完整的动作序列。

用户指令: "{user_command}"

机械臂参数:
- 6个关节 (joint1-joint6)
- 关节1: 基座旋转 (范围: -180° ~ 180°)
- 关节2: 大臂俯仰 (范围: -90° ~ 90°)
- 关节3: 小臂 (范围: 0° ~ 180°)
- 关节4: 腕部旋转 (范围: -180° ~ 180°)
- 关节5: 腕部俯仰 (范围: -90° ~ 90°)
- 关节6: 末端旋转 (范围: -180° ~ 180°)

请生成一个JSON格式的动作序列，包含:
1. name: 动作名称(简短中文，如"太空舞"、"挥手")
2. keyframes: 关键帧列表，每个关键帧包含:
   - angles: 6个关节的角度值(度数，数组格式)
   - duration: 该关键帧的持续时间(毫秒)
   - gripper (可选): true(开)/false(关)

要求:
- 动作要流畅、有创意
- 关键帧数量: 4-8个
- 总时长: 2-5秒
- 最后一帧应该归位到 [0,0,0,0,0,0]
- **只返回JSON，不要任何额外文字**

示例输出格式:
{{
  "name": "挥手",
  "keyframes": [
    {{"angles": [0, -30, 45, 0, -15, 0], "duration": 1000}},
    {{"angles": [15, -30, 45, 0, -15, 30], "duration": 500}},
    {{"angles": [0, 0, 0, 0, 0, 0], "duration": 1000}}
  ]
}}

现在请为用户指令"{user_command}"生成动作序列:"""

        if not LLM_ENABLED:
            return {"success": False, "error": "LLM已禁用：未配置 GEMINI_API_KEY"}
        GEMINI_API_KEY = CONFIG.get("GEMINI_API_KEY")
        GEMINI_MODEL = CONFIG.get("GEMINI_MODEL")
        API_URL = build_gemini_generate_url(GEMINI_MODEL, GEMINI_API_KEY)
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
        }
        
        async with httpx.AsyncClient(proxy=CONFIG.get("HTTP_PROXY")) as client:
            resp = await client.post(API_URL, json=payload, timeout=30.0)
            
            if resp.status_code == 200:
                resp_data = resp.json()
                content = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                logger.info(f"[LLM] Gemini 响应: {content}")
                
                # 清理 JSON (移除markdown代码块标记)
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                # 解析 JSON
                action_sequence = json.loads(content)
                
                return {
                    "success": True,
                    "name": action_sequence.get("name", "未命名动作"),
                    "keyframes": action_sequence.get("keyframes", []),
                    "raw": content
                }
            else:
                logger.error(f"[LLM] Gemini API 错误: {resp.status_code} - {resp.text}")
                return {"success": False, "error": f"Gemini API 错误: {resp.status_code}"}
                
    except json.JSONDecodeError as e:
        logger.error(f"[LLM] JSON 解析失败: {e}")
        return {"success": False, "error": "LLM返回格式错误", "raw": content}
    except Exception as e:
        logger.error(f"[LLM] 动作生成失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}





if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("机械臂AI服务启动中...")
    logger.info("访问地址: http://localhost:5000")
    logger.info("API文档: http://localhost:5000/docs")
    logger.info("=" * 50)
    
    # 初始化服务（TTS + IK）
    init_services()
    if LLM_ENABLED:
        logger.info("LLM已启用")
        logger.info(f"Gemini模型: {CONFIG.get('GEMINI_MODEL')}")
    else:
        logger.warning("LLM未启用：未配置 GEMINI_API_KEY")
    if CONFIG.get("HTTP_PROXY"):
        logger.info("HTTP代理已配置")
    else:
        logger.info("HTTP代理未配置")
    
    uvicorn.run(app, host="0.0.0.0", port=5000)
