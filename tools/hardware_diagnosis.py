#!/usr/bin/env python3
"""
硬件自动诊断工具 - Zero 机械臂项目
功能：自动扫描串口、测试波特率、探测协议格式、生成诊断报告

使用方法：
    python hardware_diagnosis.py

输出：
    debug_report.json - 完整诊断报告
    debug_report.txt  - 可读的文本格式报告
"""

import serial
import serial.tools.list_ports
import time
import json
import sys
import platform
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

# 测试配置
BAUDRATES = [9600, 19200, 38400, 57600, 115200, 230400, 250000, 460800, 921600]
TIMEOUT = 2.0  # 秒

# 常见测试指令
TEST_COMMANDS = [
    "?\n",                 # 通用查询
    "M114\n",              # G-code 位置查询
    "GET_STATUS\n",        # 自定义协议
    "remote_enable\n",     # 项目握手指令
    "V\n",                 # 版本查询
    "STATUS\n",            # 状态查询
    "INFO\n",              # 信息查询
    "\x01",                # SOH (Start of Heading) - 二进制握手
    "\x05",                # ENQ (Enquiry)
]


@dataclass
class PortTestResult:
    """单个端口测试结果"""
    port: str
    status: str  # 'success', 'timeout', 'error', 'permission_denied'
    baudrate: Optional[int] = None
    protocol_hints: Optional[Dict[str, Any]] = None
    latency_ms: Optional[Dict[str, float]] = None
    error: Optional[str] = None
    raw_responses: Optional[List[str]] = None


@dataclass
class DiagnosticReport:
    """完整诊断报告"""
    scan_time: str
    system: str
    python_version: str
    pyserial_version: str
    results: List[PortTestResult]
    recommendation: Optional[Dict[str, Any]] = None


def print_header(text: str):
    """打印分隔标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(step: int, text: str):
    """打印步骤"""
    print(f"\n[{step}] {text}")


def scan_ports() -> List[str]:
    """扫描所有可用串口"""
    print_step(1, "扫描串口设备...")
    ports = []
    
    for port in serial.tools.list_ports.comports():
        ports.append(port.device)
        print(f"  ✓ 发现: {port.device}")
        print(f"    描述: {port.description}")
        print(f"    硬件ID: {port.hwid}")
    
    if not ports:
        print("  ⚠️  未发现任何串口设备")
        print("  建议:")
        print("    1. 检查 USB 连接")
        print("    2. 安装驱动 (CH340/CP2102/FTDI)")
        print("    3. 检查设备管理器")
    
    return ports


def test_port_at_baudrate(port: str, baudrate: int, timeout: float = TIMEOUT) -> Optional[Dict[str, Any]]:
    """测试特定端口和波特率组合"""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        # 清空缓冲区
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        responses = []
        latencies = []
        
        # 测试所有指令
        for cmd in TEST_COMMANDS:
            try:
                # 发送指令
                start_time = time.time()
                ser.write(cmd.encode('utf-8') if isinstance(cmd, str) else cmd.encode('latin-1'))
                ser.flush()
                
                # 等待响应
                time.sleep(0.1)
                if ser.in_waiting > 0:
                    response_time = time.time() - start_time
                    raw = ser.read(ser.in_waiting)
                    
                    # 尝试解码
                    try:
                        decoded = raw.decode('utf-8', errors='ignore').strip()
                    except:
                        try:
                            decoded = raw.decode('latin-1', errors='ignore').strip()
                        except:
                            decoded = raw.hex()
                    
                    if decoded and len(decoded) > 0:
                        responses.append({
                            'command': cmd.strip(),
                            'response': decoded,
                            'raw_hex': raw.hex(),
                            'length': len(raw)
                        })
                        latencies.append(response_time * 1000)  # 转换为毫秒
            except Exception as e:
                continue
        
        ser.close()
        
        # 如果有有效响应，返回结果
        if responses:
            return {
                'responses': responses,
                'latency': {
                    'min': min(latencies) if latencies else 0,
                    'max': max(latencies) if latencies else 0,
                    'avg': sum(latencies) / len(latencies) if latencies else 0
                }
            }
        
        return None
        
    except serial.SerialException as e:
        if "PermissionError" in str(e) or "Access denied" in str(e):
            raise PermissionError(f"权限不足: {e}")
        raise
    except Exception as e:
        return None


def analyze_protocol(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析协议格式"""
    hints = {
        'format': 'unknown',
        'sample_response': '',
        'handshake_success': False,
        'possible_protocols': []
    }
    
    if not responses:
        return hints
    
    # 获取最长的响应作为示例
    longest = max(responses, key=lambda r: len(r['response']))
    hints['sample_response'] = longest['response']
    
    # 检测协议类型
    sample = longest['response']
    
    # JSON 检测
    if sample.startswith('{') or sample.startswith('['):
        hints['format'] = 'JSON'
        hints['possible_protocols'].append('Custom JSON Protocol')
    
    # CSV 检测
    elif ',' in sample and sample.count(',') >= 2:
        hints['format'] = 'CSV'
        hints['possible_protocols'].append('CSV Format (e.g., angles)')
    
    # G-code 检测
    elif sample.startswith('ok') or 'X:' in sample or 'Y:' in sample:
        hints['format'] = 'G-code'
        hints['possible_protocols'].append('G-code (Marlin/Repetier)')
    
    # 二进制检测
    elif all(c in '0123456789abcdefABCDEF' for c in sample.replace(' ', '')):
        hints['format'] = 'HEX/Binary'
        hints['possible_protocols'].append('Binary Protocol')
    
    # 纯文本
    else:
        hints['format'] = 'Text'
        hints['possible_protocols'].append('Custom Text Protocol')
    
    # 检测是否握手成功
    for resp in responses:
        if any(keyword in resp['response'].lower() for keyword in ['ok', 'ready', 'enabled', 'connected']):
            hints['handshake_success'] = True
            break
    
    return hints


def test_port(port: str) -> PortTestResult:
    """完整测试单个端口"""
    print(f"\n  测试端口: {port}")
    
    # 尝试所有波特率
    for baudrate in BAUDRATES:
        print(f"    尝试波特率 {baudrate}...", end=' ')
        sys.stdout.flush()
        
        try:
            result = test_port_at_baudrate(port, baudrate)
            
            if result:
                print("✓ 有响应")
                protocol_hints = analyze_protocol(result['responses'])
                
                return PortTestResult(
                    port=port,
                    status='success',
                    baudrate=baudrate,
                    protocol_hints=protocol_hints,
                    latency_ms=result['latency'],
                    raw_responses=[r['response'] for r in result['responses']]
                )
            else:
                print("✗ 无响应")
        
        except PermissionError as e:
            print("✗ 权限不足")
            return PortTestResult(
                port=port,
                status='permission_denied',
                error=str(e)
            )
        
        except Exception as e:
            print(f"✗ 错误: {e}")
            continue
    
    # 所有波特率都失败
    return PortTestResult(
        port=port,
        status='timeout',
        error='所有波特率均无响应'
    )


def generate_recommendation(results: List[PortTestResult]) -> Optional[Dict[str, Any]]:
    """生成推荐配置"""
    successful = [r for r in results if r.status == 'success']
    
    if not successful:
        return {
            'status': 'no_device_found',
            'message': '未检测到可用设备',
            'suggestions': [
                '检查 USB 连接是否正常',
                '确认设备已通电',
                '安装对应的 USB 转串口驱动',
                '以管理员身份运行本脚本'
            ]
        }
    
    # 选择延迟最低的端口
    best = min(successful, key=lambda r: r.latency_ms['avg'] if r.latency_ms else float('inf'))
    
    return {
        'status': 'ready',
        'best_port': best.port,
        'best_baudrate': best.baudrate,
        'suggested_protocol': best.protocol_hints['format'] if best.protocol_hints else 'unknown',
        'confidence': 'HIGH' if best.protocol_hints and best.protocol_hints['handshake_success'] else 'MEDIUM',
        'next_steps': [
            f'修改 config.json: SERIAL_PORT = "{best.port}"',
            f'修改 config.json: SERIAL_BAUDRATE = {best.baudrate}',
            f'协议格式: {best.protocol_hints["format"] if best.protocol_hints else "unknown"}',
            '运行 test_hardware.py 验证连接'
        ]
    }


def save_report(report: DiagnosticReport, json_path: str = 'debug_report.json', txt_path: str = 'debug_report.txt'):
    """保存诊断报告"""
    # 保存 JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)
    
    # 保存可读文本
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("硬件诊断报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"扫描时间: {report.scan_time}\n")
        f.write(f"系统: {report.system}\n")
        f.write(f"Python: {report.python_version}\n")
        f.write(f"PySerial: {report.pyserial_version}\n\n")
        
        for result in report.results:
            f.write(f"\n端口: {result.port}\n")
            f.write(f"状态: {result.status}\n")
            if result.baudrate:
                f.write(f"波特率: {result.baudrate}\n")
            if result.protocol_hints:
                f.write(f"协议格式: {result.protocol_hints['format']}\n")
                f.write(f"示例响应: {result.protocol_hints['sample_response'][:100]}\n")
            if result.latency_ms:
                f.write(f"延迟: {result.latency_ms['avg']:.1f} ms (平均)\n")
            if result.error:
                f.write(f"错误: {result.error}\n")
            f.write("-" * 60 + "\n")
        
        if report.recommendation:
            f.write("\n" + "=" * 60 + "\n")
            f.write("推荐配置\n")
            f.write("=" * 60 + "\n")
            for key, value in report.recommendation.items():
                if isinstance(value, list):
                    f.write(f"\n{key}:\n")
                    for item in value:
                        f.write(f"  - {item}\n")
                else:
                    f.write(f"{key}: {value}\n")


def main():
    """主函数"""
    print_header("Zero 机械臂硬件自动诊断工具")
    print(f"系统: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"PySerial: {serial.__version__}")
    
    # 扫描端口
    ports = scan_ports()
    
    if not ports:
        print("\n⚠️  没有可测试的端口，程序退出")
        return
    
    # 测试每个端口
    print_step(2, "测试端口通信...")
    results = []
    for port in ports:
        result = test_port(port)
        results.append(result)
    
    # 生成推荐
    print_step(3, "生成推荐配置...")
    recommendation = generate_recommendation(results)
    
    # 创建报告
    report = DiagnosticReport(
        scan_time=time.strftime('%Y-%m-%d %H:%M:%S'),
        system=f"{platform.system()} {platform.release()}",
        python_version=sys.version.split()[0],
        pyserial_version=serial.__version__,
        results=results,
        recommendation=recommendation
    )
    
    # 保存报告
    print_step(4, "保存诊断报告...")
    save_report(report)
    print("  ✓ 已保存: debug_report.json")
    print("  ✓ 已保存: debug_report.txt")
    
    # 打印摘要
    print_header("诊断摘要")
    successful = [r for r in results if r.status == 'success']
    
    if successful:
        print(f"\n✅ 成功检测到 {len(successful)} 个可用设备:")
        for r in successful:
            print(f"  • {r.port} @ {r.baudrate} baud")
            if r.protocol_hints:
                print(f"    协议: {r.protocol_hints['format']}")
                print(f"    握手: {'成功' if r.protocol_hints['handshake_success'] else '未确认'}")
        
        if recommendation:
            print("\n🎯 推荐配置:")
            print(f"  端口: {recommendation['best_port']}")
            print(f"  波特率: {recommendation['best_baudrate']}")
            print(f"  协议: {recommendation['suggested_protocol']}")
            print(f"  置信度: {recommendation['confidence']}")
            
            print("\n📋 下一步操作:")
            for step in recommendation.get('next_steps', []):
                print(f"  {step}")
    else:
        print("\n❌ 未检测到可用设备")
        if recommendation:
            print("\n💡 建议:")
            for suggestion in recommendation.get('suggestions', []):
                print(f"  • {suggestion}")
    
    print("\n" + "=" * 60)
    print("诊断完成！请将 debug_report.json 发送给 AI Agent 进行分析")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
