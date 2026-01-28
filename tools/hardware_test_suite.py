#!/usr/bin/env python3
"""
硬件集成测试套件
自动化测试串口通信、角度回传、性能基准等
"""

import argparse
import sys
import time
import json
from datetime import datetime
from pathlib import Path

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("缺少依赖库: pyserial")
    print("请运行: pip install pyserial")
    sys.exit(1)


class HardwareTestSuite:
    def __init__(self, port, baudrate=115200, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.test_results = {}
        
    def connect(self):
        """连接串口"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"✓ 已连接到 {self.port} @ {self.baudrate} bps")
            return True
        except serial.SerialException as e:
            print(f"✗ 串口连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开串口"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")
    
    def test_connection(self):
        """测试 1: 基础连接测试"""
        print("\n" + "="*60)
        print("测试 1: 基础串口连接")
        print("="*60)
        
        result = {
            "name": "基础连接测试",
            "passed": False,
            "details": {}
        }
        
        try:
            if self.ser and self.ser.is_open:
                result["passed"] = True
                result["details"]["port"] = self.port
                result["details"]["baudrate"] = self.baudrate
                result["details"]["is_open"] = self.ser.is_open
                print("✓ 串口连接正常")
            else:
                result["details"]["error"] = "串口未打开"
                print("✗ 串口连接失败")
        except Exception as e:
            result["details"]["error"] = str(e)
            print(f"✗ 连接测试异常: {e}")
        
        self.test_results["connection"] = result
        return result["passed"]
    
    def test_read_angles(self, num_samples=10):
        """测试 2: 角度回传测试"""
        print("\n" + "="*60)
        print("测试 2: 角度回传")
        print("="*60)
        
        result = {
            "name": "角度回传测试",
            "passed": False,
            "details": {
                "samples": [],
                "success_count": 0,
                "fail_count": 0
            }
        }
        
        print(f"正在读取 {num_samples} 组角度数据...")
        
        for i in range(num_samples):
            try:
                # 发送查询指令 (根据实际协议调整)
                self.ser.write(b"GET_ANGLES\r\n")
                time.sleep(0.1)
                
                # 读取返回
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8', errors='replace').strip()
                    
                    if data:
                        result["details"]["samples"].append(data)
                        result["details"]["success_count"] += 1
                        print(f"  [{i+1}/{num_samples}] ✓ {data}")
                    else:
                        result["details"]["fail_count"] += 1
                        print(f"  [{i+1}/{num_samples}] ✗ 无数据")
                else:
                    result["details"]["fail_count"] += 1
                    print(f"  [{i+1}/{num_samples}] ✗ 超时")
                
                time.sleep(0.2)
                
            except Exception as e:
                result["details"]["fail_count"] += 1
                print(f"  [{i+1}/{num_samples}] ✗ 错误: {e}")
        
        success_rate = result["details"]["success_count"] / num_samples * 100
        result["details"]["success_rate"] = success_rate
        result["passed"] = success_rate >= 80  # 80% 成功率
        
        print(f"\n成功率: {success_rate:.1f}% ({result['details']['success_count']}/{num_samples})")
        
        if result["passed"]:
            print("✓ 角度回传测试通过")
        else:
            print("✗ 角度回传测试失败 (成功率低于 80%)")
        
        self.test_results["read_angles"] = result
        return result["passed"]
    
    def test_send_command(self):
        """测试 3: 指令发送测试"""
        print("\n" + "="*60)
        print("测试 3: 控制指令发送")
        print("="*60)
        
        result = {
            "name": "指令发送测试",
            "passed": False,
            "details": {}
        }
        
        test_commands = [
            b"#0P1500T1000\r\n",  # 舵机控制示例
            b"{\"action\":\"move\",\"joint\":0,\"angle\":90}\r\n"  # JSON 格式示例
        ]
        
        try:
            for i, cmd in enumerate(test_commands):
                self.ser.write(cmd)
                print(f"  [{i+1}] 已发送: {cmd.decode('utf-8', errors='replace').strip()}")
                time.sleep(0.5)
            
            result["passed"] = True
            result["details"]["commands_sent"] = len(test_commands)
            print("✓ 指令发送成功")
            
        except Exception as e:
            result["details"]["error"] = str(e)
            print(f"✗ 指令发送失败: {e}")
        
        self.test_results["send_command"] = result
        return result["passed"]
    
    def test_latency(self, num_iterations=20):
        """测试 4: 通信延迟测试"""
        print("\n" + "="*60)
        print("测试 4: 通信延迟")
        print("="*60)
        
        result = {
            "name": "延迟测试",
            "passed": False,
            "details": {
                "latencies": [],
                "avg_latency": 0,
                "min_latency": 0,
                "max_latency": 0
            }
        }
        
        print(f"测量 {num_iterations} 次往返延迟...")
        
        latencies = []
        
        for i in range(num_iterations):
            try:
                start_time = time.time()
                
                # 发送
                self.ser.write(b"PING\r\n")
                
                # 等待响应
                if self.ser.in_waiting > 0 or self._wait_for_data(timeout=1.0):
                    self.ser.readline()
                    end_time = time.time()
                    
                    latency = (end_time - start_time) * 1000  # ms
                    latencies.append(latency)
                    print(f"  [{i+1}/{num_iterations}] {latency:.2f} ms")
                else:
                    print(f"  [{i+1}/{num_iterations}] 超时")
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  [{i+1}/{num_iterations}] 错误: {e}")
        
        if latencies:
            result["details"]["latencies"] = latencies
            result["details"]["avg_latency"] = sum(latencies) / len(latencies)
            result["details"]["min_latency"] = min(latencies)
            result["details"]["max_latency"] = max(latencies)
            result["passed"] = result["details"]["avg_latency"] < 100  # 目标 < 100ms
            
            print(f"\n平均延迟: {result['details']['avg_latency']:.2f} ms")
            print(f"最小延迟: {result['details']['min_latency']:.2f} ms")
            print(f"最大延迟: {result['details']['max_latency']:.2f} ms")
            
            if result["passed"]:
                print("✓ 延迟测试通过 (< 100ms)")
            else:
                print("⚠ 延迟较高 (> 100ms)")
        else:
            print("✗ 延迟测试失败 (无有效数据)")
        
        self.test_results["latency"] = result
        return result["passed"]
    
    def _wait_for_data(self, timeout=1.0):
        """等待串口数据"""
        start = time.time()
        while time.time() - start < timeout:
            if self.ser.in_waiting > 0:
                return True
            time.sleep(0.01)
        return False
    
    def test_refresh_rate(self, duration=5):
        """测试 5: 角度刷新率测试"""
        print("\n" + "="*60)
        print("测试 5: 角度刷新率")
        print("="*60)
        
        result = {
            "name": "刷新率测试",
            "passed": False,
            "details": {
                "duration": duration,
                "sample_count": 0,
                "refresh_rate": 0
            }
        }
        
        print(f"持续 {duration} 秒监控刷新率...")
        
        sample_count = 0
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                if self.ser.in_waiting > 0:
                    self.ser.readline()
                    sample_count += 1
                time.sleep(0.01)
            except Exception:
                pass
        
        elapsed = time.time() - start_time
        refresh_rate = sample_count / elapsed
        
        result["details"]["sample_count"] = sample_count
        result["details"]["refresh_rate"] = refresh_rate
        result["passed"] = refresh_rate >= 5  # 目标 >= 5 Hz
        
        print(f"\n采样数: {sample_count}")
        print(f"刷新率: {refresh_rate:.1f} Hz")
        
        if result["passed"]:
            print("✓ 刷新率测试通过 (>= 5 Hz)")
        else:
            print("⚠ 刷新率较低 (< 5 Hz)")
        
        self.test_results["refresh_rate"] = result
        return result["passed"]
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🧪 硬件集成测试套件")
        print("="*60)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"串口: {self.port} @ {self.baudrate} bps")
        
        # 运行测试
        tests = [
            ("基础连接", self.test_connection),
            ("角度回传", lambda: self.test_read_angles(10)),
            ("指令发送", self.test_send_command),
            ("通信延迟", lambda: self.test_latency(20)),
            ("刷新率", lambda: self.test_refresh_rate(5))
        ]
        
        passed_count = 0
        total_count = len(tests)
        
        for name, test_func in tests:
            try:
                if test_func():
                    passed_count += 1
            except Exception as e:
                print(f"\n✗ 测试 '{name}' 异常: {e}")
        
        # 生成报告
        self._generate_report(passed_count, total_count)
    
    def _generate_report(self, passed, total):
        """生成测试报告"""
        print("\n\n" + "="*60)
        print("📊 测试报告")
        print("="*60)
        
        for test_name, result in self.test_results.items():
            status = "✓ 通过" if result["passed"] else "✗ 失败"
            print(f"{result['name']:<20} {status}")
        
        print("="*60)
        print(f"总计: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有测试通过!")
        elif passed >= total * 0.8:
            print("⚠ 大部分测试通过,部分需要优化")
        else:
            print("❌ 多项测试失败,需要检查硬件连接和协议")
        
        # 保存 JSON 报告
        report_file = f"hardware_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "port": self.port,
                "baudrate": self.baudrate,
                "summary": {
                    "passed": passed,
                    "total": total,
                    "pass_rate": passed / total * 100
                },
                "tests": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description="硬件集成测试套件",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--port', '-p', required=True, help='串口号 (例如: COM3)')
    parser.add_argument('--baudrate', '-b', type=int, default=115200, help='波特率 (默认: 115200)')
    parser.add_argument('--list', action='store_true', help='列出所有可用串口')
    
    args = parser.parse_args()
    
    # 列出串口
    if args.list:
        print("可用串口设备:")
        ports = list_ports.comports()
        for port in ports:
            print(f"  - {port.device}: {port.description}")
        return
    
    # 运行测试
    suite = HardwareTestSuite(args.port, args.baudrate)
    
    if suite.connect():
        try:
            suite.run_all_tests()
        finally:
            suite.disconnect()
    else:
        print("\n无法连接到串口,测试终止")
        sys.exit(1)


if __name__ == '__main__':
    main()
