import serial
import serial.tools.list_ports
import threading
import re
import queue
from datetime import datetime
from pathlib import Path
import time
from typing import List, Dict, Optional, Callable


class SerialMonitor:
    """串口监控类，支持多串口同时监控"""
    
    def __init__(self, port: str, baudrate: int = 9600,
                 keywords: Optional[List[str]] = None,
                 regex_patterns: Optional[List[str]] = None,
                 log_dir: str = "logs",
                 callback: Optional[Callable] = None,
                 save_all_to_log: bool = True):
        self.port = port
        self.baudrate = baudrate
        self.keywords = keywords or []
        self.regex_patterns = [re.compile(pattern) for pattern in (regex_patterns or [])]
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.callback = callback
        self.save_all_to_log = save_all_to_log  # 是否将所有数据保存到日志
        
        self.serial_conn: Optional[serial.Serial] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.data_queue = queue.Queue()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{port.replace('/', '_').replace('\\', '_')}_{timestamp}.log"
        
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
                                
                                self.data_queue.put({
                                    'port': self.port,
                                    'timestamp': timestamp,
                                    'data': line,
                                    'log_entry': log_entry
                                })
                                
                                # 只有匹配的数据才触发回调
                                if self.callback:
                                    self.callback(self.port, timestamp, line)
                else:
                    time.sleep(0.01)
                    
            except Exception as e:
                error_msg = f"[{datetime.now()}] [{self.port}] 错误: {e}"
                self._write_log(error_msg)
                if isinstance(e, serial.SerialException):
                    break
    
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
            
            msg = f"串口 {self.port} 已启动 (波特率: {self.baudrate})"
            print(msg)
            return True
            
        except Exception as e:
            print(f"启动失败 {self.port}: {e}")
            return False
    
    def stop(self):
        """停止串口监控"""
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=2)
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        
        print(f"串口 {self.port} 已停止")
    
    def send(self, data: str) -> bool:
        """向串口发送数据"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(data.encode('utf-8'))
                return True
            return False
        except Exception as e:
            print(f"发送失败: {e}")
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
                   save_all_to_log: bool = True) -> bool:
        """添加串口监控
        
        Args:
            port: 串口名称
            baudrate: 波特率
            keywords: 关键词列表（用于过滤显示）
            regex_patterns: 正则表达式列表（用于过滤显示）
            callback: 回调函数（只在数据匹配过滤条件时调用）
            save_all_to_log: 是否将所有数据保存到日志（默认True，即使有过滤条件也保存全部数据）
        """
        if port in self.monitors:
            print(f"串口 {port} 已存在")
            return False
        
        monitor = SerialMonitor(
            port=port,
            baudrate=baudrate,
            keywords=keywords,
            regex_patterns=regex_patterns,
            log_dir=self.log_dir,
            callback=callback,
            save_all_to_log=save_all_to_log
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