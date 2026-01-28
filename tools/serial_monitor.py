#!/usr/bin/env python3
"""
串口监视器 - 替代 PuTTY/CoolTerm 的本地工具
用于实时监控串口通信,支持手动发送指令
"""

import argparse
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

try:
    import serial
    from serial.tools import list_ports
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
except ImportError as e:
    print(f"缺少依赖库: {e}")
    print("请运行: pip install pyserial rich")
    sys.exit(1)

console = Console()

class SerialMonitor:
    def __init__(self, port, baudrate=115200, timeout=1.0, log_file=None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.log_file = log_file
        self.ser = None
        self.running = False
        self.rx_count = 0
        self.tx_count = 0
        self.rx_buffer = []
        self.tx_buffer = []
        self.max_buffer_size = 100
        
    def connect(self):
        """连接串口"""
        try:
            self.ser = serial.Serial(
                self.port, 
                self.baudrate, 
                timeout=self.timeout
            )
            console.print(f"[green]✓ 已连接到 {self.port} @ {self.baudrate} bps[/green]")
            return True
        except serial.SerialException as e:
            console.print(f"[red]✗ 串口连接失败: {e}[/red]")
            return False
    
    def disconnect(self):
        """断开串口"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            console.print("[yellow]串口已关闭[/yellow]")
    
    def send_data(self, data):
        """发送数据"""
        if not self.ser or not self.ser.is_open:
            console.print("[red]错误: 串口未连接[/red]")
            return False
        
        try:
            # 自动添加换行符
            if not data.endswith('\r\n') and not data.endswith('\n'):
                data += '\r\n'
            
            self.ser.write(data.encode('utf-8'))
            self.tx_count += len(data)
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.tx_buffer.append((timestamp, data.strip()))
            if len(self.tx_buffer) > self.max_buffer_size:
                self.tx_buffer.pop(0)
            
            if self.log_file:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[TX {timestamp}] {data}")
            
            return True
        except Exception as e:
            console.print(f"[red]发送失败: {e}[/red]")
            return False
    
    def read_thread(self):
        """后台读取线程"""
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.readline()
                    if data:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        decoded = data.decode('utf-8', errors='replace').strip()
                        
                        self.rx_count += len(data)
                        self.rx_buffer.append((timestamp, decoded))
                        if len(self.rx_buffer) > self.max_buffer_size:
                            self.rx_buffer.pop(0)
                        
                        if self.log_file:
                            with open(self.log_file, 'a', encoding='utf-8') as f:
                                f.write(f"[RX {timestamp}] {decoded}\n")
                else:
                    time.sleep(0.01)
            except Exception as e:
                if self.running:
                    console.print(f"[red]读取错误: {e}[/red]")
                    time.sleep(0.1)
    
    def start_monitoring(self):
        """启动监控"""
        self.running = True
        read_thread = threading.Thread(target=self.read_thread, daemon=True)
        read_thread.start()
        return read_thread
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
    
    def get_status_table(self):
        """生成状态表"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=12)
        table.add_column(style="white")
        
        table.add_row("端口", f"{self.port} @ {self.baudrate} bps")
        table.add_row("状态", "[green]已连接[/green]" if self.ser and self.ser.is_open else "[red]未连接[/red]")
        table.add_row("接收字节", str(self.rx_count))
        table.add_row("发送字节", str(self.tx_count))
        
        return table
    
    def get_data_panel(self):
        """生成数据面板"""
        # 接收数据
        rx_text = Text()
        for ts, data in self.rx_buffer[-20:]:  # 最近20条
            rx_text.append(f"[{ts}] ", style="dim")
            rx_text.append(f"{data}\n", style="green")
        
        # 发送数据
        tx_text = Text()
        for ts, data in self.tx_buffer[-10:]:  # 最近10条
            tx_text.append(f"[{ts}] ", style="dim")
            tx_text.append(f"{data}\n", style="yellow")
        
        layout = Layout()
        layout.split_column(
            Layout(Panel(rx_text or "[dim]等待数据...[/dim]", title="📥 接收 (RX)", border_style="green"), ratio=2),
            Layout(Panel(tx_text or "[dim]无发送记录[/dim]", title="📤 发送 (TX)", border_style="yellow"), ratio=1)
        )
        
        return layout


def list_serial_ports():
    """列出所有可用串口"""
    ports = list_ports.comports()
    
    if not ports:
        console.print("[yellow]未检测到任何串口设备[/yellow]")
        return []
    
    table = Table(title="可用串口设备")
    table.add_column("端口", style="cyan")
    table.add_column("描述", style="white")
    table.add_column("硬件ID", style="dim")
    
    for port in ports:
        table.add_row(port.device, port.description, port.hwid)
    
    console.print(table)
    return [p.device for p in ports]


def interactive_mode(monitor):
    """交互式模式"""
    console.print(Panel(
        "[bold cyan]串口监视器已启动[/bold cyan]\n\n"
        "命令说明:\n"
        "  • 直接输入文本并回车发送数据\n"
        "  • 输入 'quit' 或 'exit' 退出\n"
        "  • 输入 'clear' 清空缓冲区\n"
        "  • 输入 'status' 查看统计信息",
        title="💡 使用提示",
        border_style="blue"
    ))
    
    # 启动监控
    read_thread = monitor.start_monitoring()
    
    # 主循环
    try:
        while True:
            try:
                user_input = input("\n[发送] > ")
                
                if user_input.lower() in ['quit', 'exit']:
                    console.print("[yellow]正在退出...[/yellow]")
                    break
                elif user_input.lower() == 'clear':
                    monitor.rx_buffer.clear()
                    monitor.tx_buffer.clear()
                    console.clear()
                    console.print("[green]缓冲区已清空[/green]")
                elif user_input.lower() == 'status':
                    console.print(monitor.get_status_table())
                elif user_input.strip():
                    monitor.send_data(user_input)
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]检测到 Ctrl+C,正在退出...[/yellow]")
                break
    finally:
        monitor.stop_monitoring()
        read_thread.join(timeout=1)
        monitor.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="串口监视器 - 本地硬件调试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 列出所有串口
  python serial_monitor.py --list
  
  # 连接到 COM3,波特率 115200
  python serial_monitor.py --port COM3 --baudrate 115200
  
  # 连接并保存日志
  python serial_monitor.py --port COM3 --log serial.log
        """
    )
    
    parser.add_argument('--port', '-p', type=str, help='串口号 (例如: COM3 或 /dev/ttyUSB0)')
    parser.add_argument('--baudrate', '-b', type=int, default=115200, help='波特率 (默认: 115200)')
    parser.add_argument('--timeout', '-t', type=float, default=1.0, help='超时时间 (秒, 默认: 1.0)')
    parser.add_argument('--log', '-l', type=str, help='日志文件路径')
    parser.add_argument('--list', action='store_true', help='列出所有可用串口')
    
    args = parser.parse_args()
    
    # 显示欢迎信息
    console.print(Panel.fit(
        "[bold magenta]🔌 串口监视器[/bold magenta]\n"
        "替代 PuTTY/CoolTerm 的本地调试工具",
        border_style="magenta"
    ))
    
    # 列出串口
    if args.list:
        list_serial_ports()
        return
    
    # 检查端口参数
    if not args.port:
        console.print("[yellow]未指定串口,正在扫描...[/yellow]\n")
        available_ports = list_serial_ports()
        
        if not available_ports:
            console.print("\n[red]请使用 --port 参数指定串口[/red]")
            return
        
        console.print(f"\n[cyan]提示: 使用 --port {available_ports[0]} 连接到第一个设备[/cyan]")
        return
    
    # 创建监视器
    monitor = SerialMonitor(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        log_file=args.log
    )
    
    # 连接
    if not monitor.connect():
        sys.exit(1)
    
    if args.log:
        console.print(f"[cyan]日志保存到: {args.log}[/cyan]")
    
    # 进入交互模式
    interactive_mode(monitor)
    
    console.print("[green]✓ 串口监视器已关闭[/green]")


if __name__ == '__main__':
    main()
