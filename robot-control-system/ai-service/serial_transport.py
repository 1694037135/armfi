"""Serial communication utilities for the robot arm control stack.

This module provides a thin abstraction around the pyserial API so the rest of
our services can talk to the physical controller board (or a software mock)
without needing to know transport details.  The goal is to keep all serial
handling, framing, and connection lifecycle concerns in one place.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

try:  # pragma: no cover - dependency is optional during early development
    import serial  # type: ignore
    from serial import SerialException  # type: ignore
    from serial.tools import list_ports  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully in runtime logic
    serial = None  # type: ignore
    SerialException = Exception  # type: ignore
    list_ports = None  # type: ignore


def _bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class SerialConfig:
    """Runtime configuration for the serial transport layer."""

    port: str = "COM3"
    baudrate: int = 115200
    timeout: float = 0.5
    enabled: bool = False
    handshake_command: Optional[str] = "remote_enable"
    newline: str = "\n"

    @classmethod
    def from_mapping(cls, data: dict) -> "SerialConfig":
        return cls(
            port=data.get("SERIAL_PORT", cls.port),
            baudrate=int(data.get("SERIAL_BAUDRATE", cls.baudrate) or cls.baudrate),
            timeout=float(data.get("SERIAL_TIMEOUT", cls.timeout) or cls.timeout),
            enabled=_bool(data.get("SERIAL_ENABLED", cls.enabled), cls.enabled),
            handshake_command=data.get("SERIAL_HANDSHAKE", cls.handshake_command),
            newline=data.get("SERIAL_NEWLINE", cls.newline),
        )


# ------------------------------------------------------------------
# Safety Limits and Validation
# ------------------------------------------------------------------

@dataclass(frozen=True)
class JointLimits:
    """Physical joint angle limits in degrees.
    
    These are hardware safety limits that should never be exceeded.
    Adjust based on actual robot specifications.
    """
    JOINT_1: tuple = (-180.0, 180.0)   # Base rotation
    JOINT_2: tuple = (-90.0, 90.0)     # Shoulder pitch
    JOINT_3: tuple = (-135.0, 135.0)   # Elbow
    JOINT_4: tuple = (-180.0, 180.0)   # Wrist rotation
    JOINT_5: tuple = (-90.0, 90.0)     # Wrist pitch
    JOINT_6: tuple = (-180.0, 180.0)   # End effector rotation
    
    @classmethod
    def get_limits(cls) -> List[tuple]:
        """Get all joint limits as a list."""
        return [
            cls.JOINT_1,
            cls.JOINT_2,
            cls.JOINT_3,
            cls.JOINT_4,
            cls.JOINT_5,
            cls.JOINT_6,
        ]
    
    @classmethod
    def validate_angles(cls, angles_deg: Sequence[float]) -> tuple[bool, str]:
        """Validate joint angles against physical limits.
        
        Args:
            angles_deg: Joint angles in degrees (6 values)
            
        Returns:
            (is_valid, error_message)
        """
        if len(angles_deg) != 6:
            return False, f"Expected 6 joint angles, got {len(angles_deg)}"
        
        limits = cls.get_limits()
        for idx, (angle, (min_angle, max_angle)) in enumerate(zip(angles_deg, limits), 1):
            if angle is None:
                continue
            if not (min_angle <= angle <= max_angle):
                return False, f"Joint {idx} angle {angle:.2f}° exceeds limits [{min_angle}, {max_angle}]"
        
        return True, "OK"


class SerialTransport:
    """High-level serial helper with optional mock mode."""

    def __init__(
        self,
        config: SerialConfig,
        logger: Optional[logging.Logger] = None,
        auto_connect: bool = True,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._serial: Optional[serial.Serial] = None  # type: ignore[attr-defined]
        self._lock = threading.Lock()
        self._mock_mode = not config.enabled or serial is None
        if serial is None and config.enabled:
            self.logger.warning("pyserial 未安装，串口将回退到模拟模式")
        if self._mock_mode:
            self.logger.info(
                "串口传输处于模拟模式 (enabled=%s, pyserial=%s)",
                config.enabled,
                serial is not None,
            )
        if auto_connect and not self._mock_mode:
            self.connect()

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Open the serial port if needed."""
        if self._mock_mode:
            return False
        with self._lock:
            if self._serial and self._serial.is_open:
                return True
            try:
                self._serial = serial.Serial(  # type: ignore[attr-defined]
                    port=self.config.port,
                    baudrate=self.config.baudrate,
                    timeout=self.config.timeout,
                )
                self.logger.info(
                    "串口 %s 打开成功 (baud=%s)",
                    self.config.port,
                    self.config.baudrate,
                )
                if self.config.handshake_command:
                    # 发送握手命令，但不递归调用 send_command。
                    self._write_line(self.config.handshake_command)
                return True
            except SerialException as exc:  # type: ignore[misc]
                self.logger.error("串口打开失败: %s", exc)
                self._serial = None
                return False

    def close(self) -> None:
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    if self.config.handshake_command:
                        self._write_line("remote_disable")
                finally:
                    self._serial.close()
                    self.logger.info("串口已关闭")
            self._serial = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def mock_mode(self) -> bool:
        return self._mock_mode

    def send_command(self, command: str) -> bool:
        """Send a raw command string to the controller."""
        command = command.rstrip("\r\n") + self.config.newline
        if self._mock_mode:
            self.logger.debug("[MOCK] -> %s", command.strip())
            return True
        if not self.connect():
            return False
        with self._lock:
            return self._write_line(command)

    def send_joint_angles(
        self,
        angles_deg: Sequence[Optional[float]],
        mode: str = "abs",
        delay: float = 0.01,
        validate_limits: bool = True,
    ) -> bool:
        """Send per-joint rotation commands.

        Args:
            angles_deg: Iterable of angles in degrees. `None` entries are skipped.
            mode: "abs" for absolute rotation, "rel" for incremental.
            delay: Optional delay (seconds) inserted between consecutive joints to
                avoid stressing slow serial buffers. The method itself does not
                sleep; it simply returns the recommended delay for callers.
            validate_limits: If True, validate angles against joint limits before sending.
        
        Returns:
            True if all commands sent successfully, False otherwise.
        """
        if mode not in {"abs", "rel"}:
            raise ValueError("mode must be 'abs' or 'rel'")
        
        # Validate joint limits if enabled
        if validate_limits and mode == "abs":
            # Filter out None values for validation
            angles_for_validation = [a if a is not None else 0.0 for a in angles_deg]
            is_valid, error_msg = JointLimits.validate_angles(angles_for_validation)
            if not is_valid:
                self.logger.error(f"Joint limit validation failed: {error_msg}")
                return False
        
        success = True
        for idx, angle in enumerate(angles_deg, start=1):
            if angle is None:
                continue
            cmd = f"{mode}_rotate {idx} {angle:.2f} 0 0 0 0"
            success &= self.send_command(cmd)
        if success and delay > 0:
            self.logger.debug("串口操作建议延时 %.3fs", delay)
        return success

    def send_end_effector(self, x: float, y: float, z: float) -> bool:
        """Shortcut for cartesian movement commands."""
        cmd = f"auto {x:.3f} {y:.3f} {z:.3f}"
        return self.send_command(cmd)

    def send_remote_velocity(self, vx: float, vy: float, vz: float) -> bool:
        p0 = -vx
        p1 = vy
        p2 = 0.0
        p3 = 0.0
        p4 = vz
        p5 = -vz
        cmd = f"remote_event {p0:.2f} {p1:.2f} {p2:.2f} {p3:.2f} {p4:.2f} {p5:.2f}"
        return self.send_command(cmd)

    def read_status(self) -> Optional[dict]:
        """
        读取机械臂状态报文（遥测数据）
        
        Returns:
            dict: 包含角度、错误码等信息的字典，格式：
            {
                'angles_deg': [j1, j2, j3, j4, j5, j6],
                'error_code': 0,
                'timestamp': 1234567890.123,
                'is_mock': True/False
            }
            如果没有数据或解析失败，返回 None
        
        协议格式（假设）:
            STATUS,j1,j2,j3,j4,j5,j6,error_code
            示例: STATUS,0.5,10.2,-5.3,0.0,45.6,-30.1,0
        """
        import time
        
        if self._mock_mode:
            # Mock 模式返回模拟数据（全零角度，无错误）
            return {
                'angles_deg': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                'error_code': 0,
                'timestamp': time.time(),
                'is_mock': True
            }
        
        line = self.read_line()
        if not line:
            return None
        
        # 解析协议
        try:
            parts = line.split(',')
            if parts[0].upper() == 'STATUS' and len(parts) >= 8:
                return {
                    'angles_deg': [float(parts[i]) for i in range(1, 7)],
                    'error_code': int(parts[7]) if len(parts) > 7 else 0,
                    'timestamp': time.time(),
                    'is_mock': False
                }
        except (ValueError, IndexError) as e:
            self.logger.warning(f"状态报文解析失败: {line}, 错误: {e}")
        
        return None

    # ------------------------------------------------------------------
    # Peripheral Control Methods (Placeholder for hardware integration)
    # ------------------------------------------------------------------
    
    def send_pump_control(self, state: bool) -> bool:
        """
        Control vacuum pump / gripper.
        
        Args:
            state: True to enable pump, False to disable
            
        Returns:
            True if command sent successfully
            
        Command Format (to be confirmed with hardware):
            - Enable:  "PUMP_ON\n" or "M3 S255\n" (G-code style)
            - Disable: "PUMP_OFF\n" or "M5\n"
        
        TODO: Replace with actual hardware protocol when available
        """
        if self._mock_mode:
            self.logger.info(f"[MOCK] 吸泵控制: {'开启' if state else '关闭'}")
            return True
        
        # Placeholder command format - adjust based on actual hardware
        command = "PUMP_ON" if state else "PUMP_OFF"
        return self.send_command(command)
    
    def send_pump_pwm(self, duty_cycle: int) -> bool:
        """
        Control pump suction strength via PWM.
        
        Args:
            duty_cycle: PWM duty cycle (0-255 or 0-100 depending on hardware)
            
        Returns:
            True if command sent successfully
            
        Command Format (to be confirmed):
            "PUMP_PWM <value>\n" or "M3 S<value>\n"
        
        TODO: Replace with actual hardware protocol when available
        """
        if self._mock_mode:
            self.logger.info(f"[MOCK] 吸泵强度: {duty_cycle}")
            return True
        
        if not (0 <= duty_cycle <= 255):
            self.logger.error(f"Invalid PWM duty cycle: {duty_cycle} (must be 0-255)")
            return False
        
        command = f"PUMP_PWM {duty_cycle}"
        return self.send_command(command)
    
    def send_led_control(self, state: bool, color: Optional[str] = None) -> bool:
        """
        Control status LED.
        
        Args:
            state: True to turn on, False to turn off
            color: Optional color code ("R", "G", "B", "RGB")
            
        Returns:
            True if command sent successfully
            
        Command Format (to be confirmed):
            "LED_ON [color]\n" or "LED_OFF\n"
        
        TODO: Replace with actual hardware protocol when available
        """
        if self._mock_mode:
            color_str = f" ({color})" if color else ""
            self.logger.info(f"[MOCK] LED控制: {'开启' if state else '关闭'}{color_str}")
            return True
        
        if state:
            command = f"LED_ON {color}" if color else "LED_ON"
        else:
            command = "LED_OFF"
        return self.send_command(command)
    
    def send_servo_control(self, servo_id: int, angle: float) -> bool:
        """
        Control additional servo motors (e.g., camera gimbal, extra DOF).
        
        Args:
            servo_id: Servo identifier (1-based)
            angle: Target angle in degrees
            
        Returns:
            True if command sent successfully
            
        Command Format (to be confirmed):
            "SERVO <id> <angle>\n"
        
        TODO: Replace with actual hardware protocol when available
        """
        if self._mock_mode:
            self.logger.info(f"[MOCK] 舵机控制: ID={servo_id}, 角度={angle}°")
            return True
        
        if not (1 <= servo_id <= 10):
            self.logger.error(f"Invalid servo ID: {servo_id} (must be 1-10)")
            return False
        
        command = f"SERVO {servo_id} {angle:.2f}"
        return self.send_command(command)
    
    def send_emergency_stop(self) -> bool:
        """
        Send emergency stop command to immediately halt all motion.
        
        Returns:
            True if command sent successfully
            
        Command Format (to be confirmed):
            "ESTOP\n" or "M112\n" (G-code emergency stop)
        
        CRITICAL: This should be the highest priority command
        TODO: Replace with actual hardware protocol when available
        """
        if self._mock_mode:
            self.logger.warning("[MOCK] ⚠️ 紧急停止触发")
            return True
        
        # Emergency stop should bypass normal queue and send immediately
        command = "ESTOP"
        with self._lock:
            if self._serial and self._serial.is_open:
                # Flush output buffer first to ensure ESTOP is sent immediately
                try:
                    self._serial.reset_output_buffer()
                except SerialException:
                    pass
                return self._write_line(command)
        return False
    
    def send_reset_controller(self) -> bool:
        """
        Reset the controller to initial state.
        
        Returns:
            True if command sent successfully
            
        Command Format (to be confirmed):
            "RESET\n" or "M999\n"
        
        TODO: Replace with actual hardware protocol when available
        """
        if self._mock_mode:
            self.logger.info("[MOCK] 控制器复位")
            return True
        
        command = "RESET"
        return self.send_command(command)

    def read_line(self) -> Optional[str]:
        """Read a line from the serial port (non-blocking)."""
        if self._mock_mode:
            return None
        if not self.connect():
            return None
        with self._lock:
            if not self._serial:
                return None
            try:
                raw = self._serial.readline()
            except SerialException as exc:  # type: ignore[misc]
                self.logger.error("串口读取失败: %s", exc)
                return None
        if not raw:
            return None
        try:
            return raw.decode("utf-8", errors="ignore").strip()
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="ignore").strip()

    def flush_input(self) -> None:
        if self._mock_mode or not self._serial:
            return
        with self._lock:
            try:
                self._serial.reset_input_buffer()
            except SerialException as exc:  # type: ignore[misc]
                self.logger.warning("串口输入缓冲清空失败: %s", exc)

    def flush_output(self) -> None:
        if self._mock_mode or not self._serial:
            return
        with self._lock:
            try:
                self._serial.reset_output_buffer()
            except SerialException as exc:  # type: ignore[misc]
                self.logger.warning("串口输出缓冲清空失败: %s", exc)

    @contextmanager
    def ensure_connection(self):
        """Context manager that guarantees the port is open while in scope."""
        opened = self.connect()
        try:
            yield opened
        finally:
            if not self.config.enabled:
                # 在模拟 / 配置关闭时不要重复关闭串口，以免影响后续 mock。
                return

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    @staticmethod
    def available_ports() -> List[str]:
        if list_ports is None:
            return []
        return [p.device for p in list_ports.comports()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _write_line(self, command: str) -> bool:
        if not self._serial:
            return False
        data = command if isinstance(command, bytes) else command.encode("utf-8")
        try:
            written = self._serial.write(data)
            self._serial.flush()
            if written <= 0:
                self.logger.warning("串口写入失败: %s", command)
                return False
            return True
        except SerialException as exc:  # type: ignore[misc]
            self.logger.error("串口写入异常: %s", exc)
            return False


__all__ = ["SerialConfig", "SerialTransport", "JointLimits"]
