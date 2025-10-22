import serial
import serial.tools.list_ports
import threading
import re
import queue
from datetime import datetime
from pathlib import Path
import time
from typing import List, Dict, Optional, Callable

# ANSI颜色代码
class Colors:
    """ANSI终端颜色代码"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 亮色
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    @staticmethod
    def get_port_color(port: str) -> str:
        """根据串口名称返回对应的颜色代码"""
        # 为不同的串口分配不同的颜色
        colors = [
            Colors.BRIGHT_BLUE,
            Colors.BRIGHT_GREEN,
            Colors.BRIGHT_CYAN,
            Colors.BRIGHT_MAGENTA,
            Colors.BRIGHT_YELLOW,
            Colors.BRIGHT_RED,
            Colors.BLUE,
            Colors.GREEN,
            Colors.CYAN,
            Colors.MAGENTA,
        ]
        # 使用端口名的哈希值来选择颜色
        index = hash(port) % len(colors)
        return colors[index]


class SerialMonitor:
    """串口监控类，支持多串口同时监控"""
    
    def __init__(self, port: str, baudrate: int = 9600,
                 keywords: Optional[List[str]] = None,
                 regex_patterns: Optional[List[str]] = None,
                 log_dir: str = "logs",
                 callback: Optional[Callable] = None,
                 save_all_to_log: bool = True,
                 callback_throttle_ms: int = 10,
                 enable_color: bool = True):
        self.port = port
        self.baudrate = baudrate
        self.keywords = keywords or []
        self.regex_patterns = [re.compile(pattern) for pattern in (regex_patterns or [])]
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.callback = callback
        self.save_all_to_log = save_all_to_log  # 是否将所有数据保存到日志
        self.callback_throttle_ms = callback_throttle_ms  # 回调节流时间（毫秒）
        self.enable_color = enable_color  # 是否启用颜色输出
        self.port_color = Colors.get_port_color(port)  # 获取该串口的颜色
        
        self.serial_conn: Optional[serial.Serial] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.data_queue = queue.Queue()
        self.last_callback_time = 0  # 上次回调时间
        self.callback_buffer = []  # 回调缓冲区
        self.callback_lock = threading.Lock()  # 回调缓冲区锁
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Replace path separators to create valid filename
        safe_port_name = port.replace('/', '_').replace('\\', '_')
        self.log_file = self.log_dir / f"{safe_port_name}_{timestamp}.log"
        
    def _matches_filter(self, data: str) -> bool:
        """检查数据是否匹配过滤条件"""
        if not self.keywords and not self.regex_patterns:
            return True
        
        for keyword in self.keywords:
            if keyword in data:
                return True
        
        for pattern in self.regex_patterns:
            if pattern.search(data):
                return True
        
        return False
    
    def _read_loop(self):
        """串口读取循环"""
        buffer = ""
        
        while self.is_running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    raw_data = self.serial_conn.read(self.serial_conn.in_waiting)
                    
                    try:
                        data = raw_data.decode('utf-8', errors='ignore')
                    except:
                        data = raw_data.decode('gbk', errors='ignore')
                    
                    buffer += data
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            log_entry = f"[{timestamp}] [{self.port}] {line}"
                            
                            # 始终保存到日志文件（如果启用）
                            if self.save_all_to_log:
                                self._write_log(log_entry)
                            
                            # 检查是否匹配过滤条件
                            if self._matches_filter(line):
                                # 如果没有启用保存全部日志，则只保存匹配的
                                if not self.save_all_to_log:
                                    self._write_log(log_entry)
                                
                                # 创建带颜色的日志条目
                                colored_log_entry = self._format_colored_output(timestamp, line)
                                
                                self.data_queue.put({
                                    'port': self.port,
                                    'timestamp': timestamp,
                                    'data': line,
                                    'log_entry': log_entry,
                                    'colored_log_entry': colored_log_entry,
                                    'color': self.port_color
                                })
                                
                                # 只有匹配的数据才触发回调（带节流）
                                if self.callback:
                                    self._throttled_callback(self.port, timestamp, line, colored_log_entry)
                else:
                    time.sleep(0.01)
                    
            except Exception as e:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                error_msg = f"[{timestamp}] [{self.port}] 错误: {e}"
                self._write_log(error_msg)
                
                # 打印带颜色的错误信息
                if self.enable_color:
                    colored_error = f"{Colors.BRIGHT_BLACK}[{timestamp}]{Colors.RESET} {self.port_color}[{self.port}]{Colors.RESET} {Colors.BRIGHT_RED}错误: {e}{Colors.RESET}"
                    print(colored_error)
                else:
                    print(error_msg)
                
                if isinstance(e, serial.SerialException):
                    break
    
    def _format_colored_output(self, timestamp: str, data: str) -> str:
        """格式化带颜色的输出"""
        if self.enable_color:
            return f"{Colors.BRIGHT_BLACK}[{timestamp}]{Colors.RESET} {self.port_color}[{self.port}]{Colors.RESET} {data}"
        else:
            return f"[{timestamp}] [{self.port}] {data}"
    
    def _throttled_callback(self, port: str, timestamp: str, data: str, colored_log_entry: str = ""):
        """节流的回调函数"""
        current_time = time.time() * 1000  # 转换为毫秒
        
        with self.callback_lock:
            self.callback_buffer.append((port, timestamp, data, colored_log_entry))
            
            # 检查是否到达节流时间或缓冲区已满
            if (current_time - self.last_callback_time >= self.callback_throttle_ms or
                len(self.callback_buffer) >= 10):  # 缓冲区达到10条就立即刷新
                self._flush_callback_buffer_internal()
                self.last_callback_time = current_time
    
    def _flush_callback_buffer_internal(self):
        """内部刷新回调缓冲区（需要持有锁）"""
        if self.callback_buffer and self.callback:
            # 批量调用回调
            for item in self.callback_buffer:
                port, timestamp, data = item[0], item[1], item[2]
                colored_log_entry = item[3] if len(item) > 3 else ""
                try:
                    self.callback(port, timestamp, data, colored_log_entry)
                except Exception as e:
                    print(f"回调函数错误: {e}")
            self.callback_buffer.clear()
    
    def _write_log(self, log_entry: str):
        """写入日志文件"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"写入日志失败: {e}")
    
    def start(self) -> bool:
        """启动串口监控"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            
            self.is_running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            
            if self.enable_color:
                msg = f"{self.port_color}串口 {self.port} 已启动{Colors.RESET} (波特率: {self.baudrate})"
            else:
                msg = f"串口 {self.port} 已启动 (波特率: {self.baudrate})"
            print(msg)
            return True
            
        except Exception as e:
            if self.enable_color:
                error_msg = f"{Colors.BRIGHT_RED}启动失败{Colors.RESET} {self.port_color}{self.port}{Colors.RESET}: {Colors.RED}{e}{Colors.RESET}"
            else:
                error_msg = f"启动失败 {self.port}: {e}"
            print(error_msg)
            return False
    
    def stop(self):
        """停止串口监控"""
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=2)
        
        # 停止前刷新剩余的回调
        with self.callback_lock:
            self._flush_callback_buffer_internal()
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        
        if self.enable_color:
            print(f"{self.port_color}串口 {self.port} 已停止{Colors.RESET}")
        else:
            print(f"串口 {self.port} 已停止")
    
    def send(self, data: str) -> bool:
        """向串口发送数据"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(data.encode('utf-8'))
                return True
            return False
        except Exception as e:
            if self.enable_color:
                error_msg = f"{Colors.BRIGHT_RED}发送失败{Colors.RESET}: {Colors.RED}{e}{Colors.RESET}"
            else:
                error_msg = f"发送失败: {e}"
            print(error_msg)
            return False


class MultiSerialMonitor:
    """多串口监控管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.monitors: Dict[str, SerialMonitor] = {}
        self.log_dir = log_dir
    
    def add_monitor(self, port: str, baudrate: int = 9600,
                   keywords: Optional[List[str]] = None,
                   regex_patterns: Optional[List[str]] = None,
                   callback: Optional[Callable] = None,
                   save_all_to_log: bool = True,
                   callback_throttle_ms: int = 10,
                   enable_color: bool = True) -> bool:
        """添加串口监控
        
        Args:
            port: 串口名称
            baudrate: 波特率
            keywords: 关键词列表（用于过滤显示）
            regex_patterns: 正则表达式列表（用于过滤显示）
            callback: 回调函数（只在数据匹配过滤条件时调用）
            save_all_to_log: 是否将所有数据保存到日志（默认True，即使有过滤条件也保存全部数据）
            callback_throttle_ms: 回调节流时间（毫秒），默认10ms
            enable_color: 是否启用颜色输出（默认True）
        """
        if port in self.monitors:
            if enable_color:
                msg = f"{Colors.BRIGHT_YELLOW}警告: 串口 {port} 已存在{Colors.RESET}"
            else:
                msg = f"串口 {port} 已存在"
            print(msg)
            return False
        
        monitor = SerialMonitor(
            port=port,
            baudrate=baudrate,
            keywords=keywords,
            regex_patterns=regex_patterns,
            log_dir=self.log_dir,
            callback=callback,
            save_all_to_log=save_all_to_log,
            callback_throttle_ms=callback_throttle_ms,
            enable_color=enable_color
        )
        
        if monitor.start():
            self.monitors[port] = monitor
            return True
        return False
    
    def remove_monitor(self, port: str) -> bool:
        """移除串口监控"""
        if port in self.monitors:
            self.monitors[port].stop()
            del self.monitors[port]
            return True
        return False
    
    def send(self, port: str, data: str) -> bool:
        """向指定串口发送数据"""
        if port in self.monitors:
            return self.monitors[port].send(data)
        return False
    
    def stop_all(self):
        """停止所有串口监控"""
        for monitor in self.monitors.values():
            monitor.stop()
        self.monitors.clear()
    
    def get_active_ports(self) -> List[str]:
        """获取活动串口列表"""
        return list(self.monitors.keys())
    
    @staticmethod
    def list_available_ports() -> List[str]:
        """列出系统可用的串口"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]