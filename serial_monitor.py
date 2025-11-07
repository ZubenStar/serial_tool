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
        
        # 数据统计
        self.total_bytes_received = 0  # 接收的总字节数
        self.stats_lock = threading.Lock()  # 统计数据锁
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Replace path separators to create valid filename
        safe_port_name = port.replace('/', '_').replace('\\', '_')
        self.log_file = self.log_dir / f"{safe_port_name}_{timestamp}.log"
        
    def update_filters(self, keywords: Optional[List[str]] = None, regex_patterns: Optional[List[str]] = None):
        """动态更新过滤条件，无需重启串口
        
        Args:
            keywords: 新的关键词列表
            regex_patterns: 新的正则表达式列表（字符串）
        """
        if keywords is not None:
            self.keywords = keywords
        
        if regex_patterns is not None:
            self.regex_patterns = [re.compile(pattern) for pattern in regex_patterns]
    
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
                    
                    # 更新接收的总字节数
                    with self.stats_lock:
                        self.total_bytes_received += len(raw_data)
                    
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
        """立即回调函数（移除节流以确保实时性）"""
        # 直接调用callback，不再使用缓冲区和节流
        if self.callback:
            try:
                self.callback(port, timestamp, data, colored_log_entry)
            except Exception as e:
                print(f"回调函数错误: {e}")
    
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
            
        except serial.SerialException as e:
            if self.enable_color:
                error_msg = f"{Colors.BRIGHT_RED}串口错误{Colors.RESET} {self.port_color}{self.port}{Colors.RESET}: {Colors.RED}{e}{Colors.RESET}"
            else:
                error_msg = f"串口错误 {self.port}: {e}"
            print(error_msg)
            return False
        except Exception as e:
            if self.enable_color:
                error_msg = f"{Colors.BRIGHT_RED}启动失败{Colors.RESET} {self.port_color}{self.port}{Colors.RESET}: {Colors.RED}{type(e).__name__}: {e}{Colors.RESET}"
            else:
                error_msg = f"启动失败 {self.port}: {type(e).__name__}: {e}"
            print(error_msg)
            return False
    
    def stop(self):
        """停止串口监控"""
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=2)
            # 如果线程未能在超时时间内结束，记录警告
            if self.thread.is_alive():
                if self.enable_color:
                    print(f"{Colors.BRIGHT_YELLOW}警告: 串口 {self.port} 监控线程未能正常停止{Colors.RESET}")
                else:
                    print(f"警告: 串口 {self.port} 监控线程未能正常停止")
        
        # 停止前刷新剩余的回调
        with self.callback_lock:
            self._flush_callback_buffer_internal()
        
        # 安全关闭串口连接
        if self.serial_conn:
            try:
                if self.serial_conn.is_open:
                    self.serial_conn.close()
            except Exception as e:
                if self.enable_color:
                    print(f"{Colors.BRIGHT_RED}关闭串口时出错{Colors.RESET}: {e}")
                else:
                    print(f"关闭串口时出错: {e}")
        
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
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self.stats_lock:
            return {
                'total_bytes': self.total_bytes_received,
                'port': self.port
            }
    
    def change_baudrate(self, new_baudrate: int) -> bool:
        """动态修改波特率，无需停止串口监控
        
        Args:
            new_baudrate: 新的波特率
        
        Returns:
            bool: 修改是否成功
        """
        try:
            if self.serial_conn and self.serial_conn.is_open:
                # 保存当前状态
                old_baudrate = self.baudrate
                
                # 修改波特率
                self.serial_conn.baudrate = new_baudrate
                self.baudrate = new_baudrate
                
                if self.enable_color:
                    msg = f"{self.port_color}串口 {self.port} 波特率已从 {old_baudrate} 修改为 {new_baudrate}{Colors.RESET}"
                else:
                    msg = f"串口 {self.port} 波特率已从 {old_baudrate} 修改为 {new_baudrate}"
                print(msg)
                
                # 记录到日志
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                log_entry = f"[{timestamp}] [{self.port}] 波特率修改: {old_baudrate} -> {new_baudrate}"
                self._write_log(log_entry)
                
                return True
            else:
                if self.enable_color:
                    msg = f"{Colors.BRIGHT_RED}错误: 串口 {self.port} 未打开{Colors.RESET}"
                else:
                    msg = f"错误: 串口 {self.port} 未打开"
                print(msg)
                return False
        except Exception as e:
            if self.enable_color:
                error_msg = f"{Colors.BRIGHT_RED}修改波特率失败{Colors.RESET} {self.port_color}{self.port}{Colors.RESET}: {Colors.RED}{e}{Colors.RESET}"
            else:
                error_msg = f"修改波特率失败 {self.port}: {e}"
            print(error_msg)
            return False


class MultiSerialMonitor:
    """多串口监控管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.monitors: Dict[str, SerialMonitor] = {}
        self.log_dir = log_dir
        self.start_lock = threading.Lock()  # 用于并行启动的线程安全
    
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
            callback_throttle_ms: 回调节流时间（毫秒），默认1ms
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
    
    def add_monitors_parallel(self, port_configs: List[Dict]) -> Dict[str, bool]:
        """并行添加多个串口监控（加快启动速度）
        
        Args:
            port_configs: 串口配置列表，每个配置包含:
                - port: 串口名称
                - baudrate: 波特率 (可选，默认9600)
                - keywords: 关键词列表 (可选)
                - regex_patterns: 正则表达式列表 (可选)
                - callback: 回调函数 (可选)
                - save_all_to_log: 是否保存所有数据 (可选，默认True)
                - callback_throttle_ms: 回调节流时间 (可选，默认1)
                - enable_color: 是否启用颜色 (可选，默认True)
        
        Returns:
            Dict[str, bool]: 每个串口的启动结果
        """
        results = {}
        threads = []
        
        def start_single_monitor(config: Dict):
            port = config['port']
            try:
                success = self.add_monitor(
                    port=port,
                    baudrate=config.get('baudrate', 9600),
                    keywords=config.get('keywords'),
                    regex_patterns=config.get('regex_patterns'),
                    callback=config.get('callback'),
                    save_all_to_log=config.get('save_all_to_log', True),
                    callback_throttle_ms=config.get('callback_throttle_ms', 10),
                    enable_color=config.get('enable_color', True)
                )
                with self.start_lock:
                    results[port] = success
            except Exception as e:
                print(f"并行启动串口 {port} 失败: {e}")
                with self.start_lock:
                    results[port] = False
        
        # 为每个串口创建启动线程
        for config in port_configs:
            thread = threading.Thread(target=start_single_monitor, args=(config,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        return results
    
    def update_monitor_filters(self, port: str, keywords: Optional[List[str]] = None,
                               regex_patterns: Optional[List[str]] = None) -> bool:
        """更新指定串口的过滤条件，无需重启串口
        
        Args:
            port: 串口名称
            keywords: 新的关键词列表
            regex_patterns: 新的正则表达式列表（字符串）
        
        Returns:
            bool: 更新是否成功
        """
        if port in self.monitors:
            self.monitors[port].update_filters(keywords, regex_patterns)
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
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有串口的统计信息"""
        stats = {}
        for port, monitor in self.monitors.items():
            stats[port] = monitor.get_stats()
        return stats
    
    def change_baudrate(self, port: str, new_baudrate: int) -> bool:
        """修改指定串口的波特率
        
        Args:
            port: 串口名称
            new_baudrate: 新的波特率
        
        Returns:
            bool: 修改是否成功
        """
        if port in self.monitors:
            return self.monitors[port].change_baudrate(new_baudrate)
        return False
    
    def change_all_baudrates(self, new_baudrate: int) -> Dict[str, bool]:
        """修改所有活动串口的波特率
        
        Args:
            new_baudrate: 新的波特率
        
        Returns:
            Dict[str, bool]: 每个串口的修改结果
        """
        results = {}
        for port in self.monitors.keys():
            results[port] = self.change_baudrate(port, new_baudrate)
        return results
    
    @staticmethod
    def list_available_ports() -> List[str]:
        """列出系统可用的串口"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]