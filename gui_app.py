import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
import time
from pathlib import Path
from typing import Dict, List

# 延迟导入serial_monitor以加快启动
_monitor_module = None

def get_monitor_module():
    """延迟导入串口监控模块"""
    global _monitor_module
    if _monitor_module is None:
        from serial_monitor import MultiSerialMonitor, Colors
        _monitor_module = {'MultiSerialMonitor': MultiSerialMonitor, 'Colors': Colors}
    return _monitor_module

# 读取版本信息 - 优化：缓存版本号
_version_cache = None

def get_version() -> str:
    """从VERSION文件读取版本号（带缓存）"""
    global _version_cache
    if _version_cache is not None:
        return _version_cache
    
    try:
        version_file = Path(__file__).parent / "VERSION"
        if version_file.exists():
            _version_cache = version_file.read_text(encoding='utf-8').strip()
            return _version_cache
    except Exception:
        pass
    _version_cache = "1.0.0"
    return _version_cache

VERSION = get_version()

class SerialToolGUI:
    """串口工具图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"多串口监控工具 v{VERSION}")
        self.root.geometry("1200x800")
        # 设置默认全屏
        self.root.state('zoomed')
        
        # 延迟初始化monitor
        monitor_mod = get_monitor_module()
        self.monitor = monitor_mod['MultiSerialMonitor'](log_dir="logs")
        self.port_configs: Dict[str, Dict] = {}
        self.config_file = "serial_tool_config.json"
        self.batch_configs_file = "serial_tool_batch_configs.json"  # 批量配置文件
        self.batch_port_configs: List[Dict] = []  # 批量串口配置列表
        
        # 性能优化：批量更新缓冲区 - 自适应策略
        self.display_buffer = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 100  # 批量处理的最大条目数（平衡性能与实时性）
        self.update_interval = 30  # UI更新间隔(毫秒)（平衡刷新频率）
        self.min_update_interval = 16  # 最小更新间隔(约60fps)
        self.max_update_interval = 100  # 最大更新间隔
        self.adaptive_threshold = 20  # 缓冲区低于此值时加速刷新
        self.max_display_lines = 1000  # 最大显示行数
        self.trim_to_lines = 800  # 超过最大行数时保留的行数
        self.last_trim_time = 0  # 上次清理时间
        self.trim_interval = 10.0  # 清理间隔(秒)（减少清理频率）
        
        # 数据统计更新
        self.stats_update_interval = 2000  # 统计信息更新间隔(毫秒)（降低更新频率）
        
        self._create_widgets()
        self._load_config()
        self._start_ui_update_loop()
        
        # 优化：延迟启动非关键任务
        self.root.after(100, self._delayed_init)
    
    def _delayed_init(self):
        """延迟初始化非关键组件"""
        self._update_available_ports()
        self._start_stats_update_loop()
        
    def _create_widgets(self):
        """创建界面组件 - 左右布局（优化：减少不必要的配置）"""
        # 创建主容器框架
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 优化：使用after延迟初始化统计显示，减少启动时间
        self._stats_display_created = False
        
        # 左侧控制面板
        left_panel = ttk.Frame(main_container, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(5, 2))
        left_panel.pack_propagate(False)  # 防止自动收缩
        
        # 右侧数据显示区域
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 5))
        
        # === 左侧面板内容 ===
        # 串口控制区
        control_frame = ttk.LabelFrame(left_panel, text="串口控制", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 串口选择
        port_frame = ttk.Frame(control_frame)
        port_frame.pack(fill=tk.X, pady=2)
        ttk.Label(port_frame, text="串口:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, width=12)
        self.port_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(port_frame, text="刷新", command=self._update_available_ports, width=6).pack(side=tk.LEFT)
        
        # 波特率
        baud_frame = ttk.Frame(control_frame)
        baud_frame.pack(fill=tk.X, pady=2)
        ttk.Label(baud_frame, text="波特率:").pack(side=tk.LEFT)
        self.baudrate_var = tk.StringVar(value="9600")
        baudrate_combo = ttk.Combobox(baud_frame, textvariable=self.baudrate_var, width=12,
                                      values=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600", "3000000"])
        baudrate_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.baudrate_var.trace_add('write', self._on_config_change)
        
        # 关键词过滤
        kw_frame = ttk.Frame(control_frame)
        kw_frame.pack(fill=tk.X, pady=2)
        ttk.Label(kw_frame, text="关键词:").pack(anchor=tk.W)
        self.keywords_var = tk.StringVar()
        ttk.Entry(kw_frame, textvariable=self.keywords_var).pack(fill=tk.X, pady=2)
        self.keywords_var.trace_add('write', self._on_config_change)
        ttk.Label(kw_frame, text="(逗号分隔)", font=("TkDefaultFont", 8)).pack(anchor=tk.W)
        
        # 正则表达式
        regex_frame = ttk.Frame(control_frame)
        regex_frame.pack(fill=tk.X, pady=2)
        ttk.Label(regex_frame, text="正则:").pack(anchor=tk.W)
        self.regex_var = tk.StringVar()
        ttk.Entry(regex_frame, textvariable=self.regex_var).pack(fill=tk.X, pady=2)
        self.regex_var.trace_add('write', self._on_config_change)
        ttk.Label(regex_frame, text="(逗号分隔)", font=("TkDefaultFont", 8)).pack(anchor=tk.W)
        
        # 实时应用过滤按钮
        filter_apply_frame = ttk.Frame(control_frame)
        filter_apply_frame.pack(fill=tk.X, pady=5)
        ttk.Button(filter_apply_frame, text="🔄 实时应用过滤", command=self._apply_filters_realtime).pack(fill=tk.X)
        ttk.Label(filter_apply_frame, text="(无需重启串口)", font=("TkDefaultFont", 8), foreground="gray").pack(anchor=tk.W)
        
        # 控制按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="启动监控", command=self._start_monitor).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="停止监控", command=self._stop_monitor).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        btn_frame2 = ttk.Frame(control_frame)
        btn_frame2.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame2, text="停止所有", command=self._stop_all).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(btn_frame2, text="清除显示", command=self._clear_display).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # 批量操作区
        batch_frame = ttk.LabelFrame(left_panel, text="批量操作", padding=10)
        batch_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(batch_frame, text="添加到批量配置", command=self._add_to_batch).pack(fill=tk.X, pady=2)
        ttk.Button(batch_frame, text="🚀 快速启动批量配置", command=self._start_batch).pack(fill=tk.X, pady=2)
        
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(batch_btn_frame, text="查看配置", command=self._show_batch_configs).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(batch_btn_frame, text="清空配置", command=self._clear_batch).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # 发送数据区 - 移到活动串口列表之前
        send_frame = ttk.LabelFrame(left_panel, text="发送数据", padding=10)
        send_frame.pack(fill=tk.X, pady=5)
        
        send_port_frame = ttk.Frame(send_frame)
        send_port_frame.pack(fill=tk.X, pady=2)
        ttk.Label(send_port_frame, text="目标串口:").pack(side=tk.LEFT)
        self.send_port_var = tk.StringVar()
        self.send_port_combo = ttk.Combobox(send_port_frame, textvariable=self.send_port_var, width=12)
        self.send_port_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        send_data_frame = ttk.Frame(send_frame)
        send_data_frame.pack(fill=tk.X, pady=2)
        ttk.Label(send_data_frame, text="数据:").pack(anchor=tk.W)
        self.send_data_var = tk.StringVar()
        ttk.Entry(send_data_frame, textvariable=self.send_data_var).pack(fill=tk.X, pady=2)
        self.send_data_var.trace_add('write', self._on_config_change)
        ttk.Button(send_data_frame, text="发送", command=self._send_data).pack(fill=tk.X, pady=2)
        
        # 活动串口列表 - 移到发送数据区之后
        active_frame = ttk.LabelFrame(left_panel, text="活动串口", padding=10)
        active_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.active_list = tk.Listbox(active_frame, height=4)
        self.active_list.pack(fill=tk.BOTH, expand=True)
        
        # === 右侧数据显示区 ===
        display_frame = ttk.LabelFrame(right_panel, text="数据显示", padding=10)
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_display = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD)
        self.text_display.pack(fill=tk.BOTH, expand=True)
        
        # 配置基本颜色标签
        self.text_display.tag_config("timestamp", foreground="gray")
        self.text_display.tag_config("default", foreground="black")
        self.text_display.tag_config("error", foreground="#FF5555", font=("TkDefaultFont", 9, "bold"))
        self.text_display.tag_config("warning", foreground="#FFAA00", font=("TkDefaultFont", 9, "bold"))
        self.text_display.tag_config("success", foreground="#55FF55")
        
        # 动态端口颜色映射
        self.port_color_tags = {}
        self._init_color_tags()
        
        # 数据统计显示区域（在数据显示区下方） - 优化：延迟创建
        self.stats_frame = ttk.LabelFrame(right_panel, text="数据统计", padding=5)
        self.stats_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 使用Text widget来显示统计信息，支持多行
        self.stats_display = tk.Text(self.stats_frame, height=3, wrap=tk.WORD, state=tk.DISABLED,
                                      background='#f0f0f0', relief=tk.FLAT)
        self.stats_display.pack(fill=tk.X)
        
        # 优化：延迟配置颜色标签
        self._stats_tags_configured = False
        
        # 状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 版本信息标签
        version_label = ttk.Label(status_frame, text=f"v{VERSION}", relief=tk.SUNKEN, foreground="gray")
        version_label.pack(side=tk.RIGHT, padx=5)
    
    def _init_color_tags(self):
        """初始化颜色标签映射"""
        # 定义Tkinter可用的颜色（对应ANSI颜色）
        self.color_map = {
            'BRIGHT_BLUE': '#5555FF',
            'BRIGHT_GREEN': '#55FF55',
            'BRIGHT_CYAN': '#55FFFF',
            'BRIGHT_MAGENTA': '#FF55FF',
            'BRIGHT_YELLOW': '#FFFF55',
            'BRIGHT_RED': '#FF5555',
            'BLUE': '#0000AA',
            'GREEN': '#00AA00',
            'CYAN': '#00AAAA',
            'MAGENTA': '#AA00AA',
        }
    
    def _get_port_color_tag(self, port: str) -> str:
        """获取或创建端口的颜色标签"""
        if port not in self.port_color_tags:
            # 使用与serial_monitor相同的颜色选择逻辑
            color_names = [
                'BRIGHT_BLUE', 'BRIGHT_GREEN', 'BRIGHT_CYAN',
                'BRIGHT_MAGENTA', 'BRIGHT_YELLOW', 'BRIGHT_RED',
                'BLUE', 'GREEN', 'CYAN', 'MAGENTA'
            ]
            index = hash(port) % len(color_names)
            color_name = color_names[index]
            tag_name = f"port_{port}"
            
            # 配置颜色标签
            self.text_display.tag_config(tag_name, foreground=self.color_map[color_name])
            self.port_color_tags[port] = tag_name
        
        return self.port_color_tags[port]
        
    def _update_available_ports(self):
        """更新可用串口列表（优化：异步扫描）"""
        def scan_ports():
            monitor_mod = get_monitor_module()
            ports = monitor_mod['MultiSerialMonitor'].list_available_ports()
            # 在主线程更新UI
            self.root.after(0, lambda: self._update_port_list(ports))
        
        # 启动时显示加载状态
        self.status_var.set("正在扫描串口...")
        # 异步扫描
        threading.Thread(target=scan_ports, daemon=True).start()
    
    def _update_port_list(self, ports):
        """更新端口列表（在主线程中调用）"""
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
        self.status_var.set(f"找到 {len(ports)} 个可用串口")
        
    def _get_filter_config(self):
        """获取过滤配置"""
        keywords = [k.strip() for k in self.keywords_var.get().split(',') if k.strip()]
        regex_patterns = [r.strip() for r in self.regex_var.get().split(',') if r.strip()]
        return keywords, regex_patterns
    
    def _apply_filters_realtime(self):
        """实时应用过滤条件到所有活动串口，无需重启串口"""
        active_ports = self.monitor.get_active_ports()
        
        if not active_ports:
            messagebox.showinfo("提示", "当前没有活动的串口监控")
            return
        
        keywords, regex_patterns = self._get_filter_config()
        
        # 更新所有活动串口的过滤条件
        success_count = 0
        for port in active_ports:
            if self.monitor.update_monitor_filters(port, keywords, regex_patterns):
                # 更新本地配置
                if port in self.port_configs:
                    self.port_configs[port]['keywords'] = keywords
                    self.port_configs[port]['regex'] = regex_patterns
                success_count += 1
        
        # 更新活动串口列表显示
        self._update_active_list()
        
        # 显示提示信息
        filter_info = []
        if keywords:
            filter_info.append(f"关键词: {', '.join(keywords[:3])}")
        if regex_patterns:
            filter_info.append(f"正则: {', '.join(regex_patterns[:2])}")
        
        if filter_info:
            filter_desc = " | ".join(filter_info)
            msg = f"已实时更新 {success_count} 个串口的过滤条件\n{filter_desc}"
        else:
            msg = f"已清除 {success_count} 个串口的过滤条件（显示全部数据）"
        
        messagebox.showinfo("过滤已应用", msg)
        self.status_var.set(f"已实时更新过滤: {success_count}个串口")
    
    def _on_config_change(self, *args):
        """配置变化时自动保存"""
        self._save_config()
        
    def _start_monitor(self):
        """启动串口监控"""
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("警告", "请选择串口")
            return
        
        try:
            baudrate = int(self.baudrate_var.get())
        except ValueError:
            messagebox.showerror("错误", "波特率必须是数字")
            return
        
        keywords, regex_patterns = self._get_filter_config()
        
        def callback(port, timestamp, data, colored_log_entry=""):
            self._display_data(port, timestamp, data)
        
        if self.monitor.add_monitor(port, baudrate, keywords, regex_patterns, callback, enable_color=False):
            self.port_configs[port] = {
                'baudrate': baudrate,
                'keywords': keywords,
                'regex': regex_patterns
            }
            self._update_active_list()
            self.status_var.set(f"已启动 {port}")
        else:
            messagebox.showerror("错误", f"无法启动串口 {port}")
    
    def _stop_monitor(self):
        """停止选中的串口监控"""
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("警告", "请选择串口")
            return
        
        if self.monitor.remove_monitor(port):
            if port in self.port_configs:
                del self.port_configs[port]
            self._update_active_list()
            self.status_var.set(f"已停止 {port}")
        else:
            messagebox.showwarning("警告", f"串口 {port} 未在监控中")
    
    def _stop_all(self):
        """停止所有串口监控"""
        self.monitor.stop_all()
        self.port_configs.clear()
        self._update_active_list()
        self.status_var.set("已停止所有串口")
    
    def _update_active_list(self):
        """更新活动串口列表"""
        self.active_list.delete(0, tk.END)
        active_ports = self.monitor.get_active_ports()
        
        for port in active_ports:
            config = self.port_configs.get(port, {})
            info = f"{port} @ {config.get('baudrate', 'N/A')} bps"
            if config.get('keywords'):
                info += f" | 关键词: {', '.join(config['keywords'][:3])}"
            if config.get('regex'):
                info += f" | 正则: {', '.join(config['regex'][:2])}"
            self.active_list.insert(tk.END, info)
        
        # 更新发送串口选择
        self.send_port_combo['values'] = active_ports
        if active_ports and not self.send_port_var.get():
            self.send_port_combo.current(0)
    
    def _display_data(self, port, timestamp, data):
        """显示接收到的数据（使用缓冲区批量处理）"""
        with self.buffer_lock:
            self.display_buffer.append({
                'port': port,
                'timestamp': timestamp,
                'data': data
            })
    
    def _start_ui_update_loop(self):
        """启动UI更新循环"""
        self._process_display_buffer()
    
    def _process_display_buffer(self):
        """批量处理显示缓冲区（自适应策略：根据缓冲区大小动态调整）"""
        try:
            with self.buffer_lock:
                buffer_size = len(self.display_buffer)
                
                if buffer_size == 0:
                    # 缓冲区为空，使用标准间隔
                    self.root.after(self.update_interval, self._process_display_buffer)
                    return
                
                # 自适应策略：缓冲区数据少时快速刷新，数据多时批量处理
                if buffer_size < self.adaptive_threshold:
                    # 数据少，立即显示（实时性优先）
                    batch = self.display_buffer[:buffer_size]
                    self.display_buffer = []
                    next_interval = self.min_update_interval
                elif buffer_size < self.max_buffer_size:
                    # 中等数据量，取所有数据
                    batch = self.display_buffer[:buffer_size]
                    self.display_buffer = []
                    next_interval = self.update_interval
                else:
                    # 数据量大，批量处理（性能优先）
                    batch = self.display_buffer[:self.max_buffer_size]
                    self.display_buffer = self.display_buffer[self.max_buffer_size:]
                    next_interval = self.min_update_interval  # 加速处理积压
            
            # 优化：禁用自动滚动，批量插入后一次性滚动
            self.text_display.config(state=tk.NORMAL)
            
            # 批量插入数据到文本框
            for item in batch:
                port = item['port']
                timestamp = item['timestamp']
                data = item['data']
                
                # 获取端口的颜色标签
                port_tag = self._get_port_color_tag(port)
                
                # 分段插入以应用不同的颜色
                self.text_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
                self.text_display.insert(tk.END, f"[{port}] ", port_tag)
                self.text_display.insert(tk.END, f"{data}\n", "default")
            
            # 滚动到底部（一次性操作）
            self.text_display.see(tk.END)
            
            # 定期清理超出的行数（避免每次都检查）
            current_time = time.time()
            if current_time - self.last_trim_time > self.trim_interval:
                self._trim_display_lines()
                self.last_trim_time = current_time
            
        except Exception as e:
            print(f"处理显示缓冲区错误: {e}")
            next_interval = self.update_interval
        
        # 继续循环（使用动态间隔）
        self.root.after(next_interval, self._process_display_buffer)
    
    def _trim_display_lines(self):
        """清理超出的显示行数"""
        try:
            lines = int(self.text_display.index('end-1c').split('.')[0])
            if lines > self.max_display_lines:
                # 删除前面的行，保留最近的数据
                delete_lines = lines - self.trim_to_lines
                self.text_display.delete('1.0', f'{delete_lines}.0')
        except Exception as e:
            print(f"清理显示行数错误: {e}")
    
    def _clear_display(self):
        """清除显示区域"""
        self.text_display.delete('1.0', tk.END)
        self.status_var.set("已清除显示")
    
    def _send_data(self):
        """发送数据到串口"""
        port = self.send_port_var.get()
        data = self.send_data_var.get()
        
        if not port:
            messagebox.showwarning("警告", "请选择目标串口")
            return
        
        if not data:
            messagebox.showwarning("警告", "请输入要发送的数据")
            return
        
        # 添加换行符
        if not data.endswith('\n'):
            data += '\n'
        
        if self.monitor.send(port, data):
            self.status_var.set(f"已发送到 {port}: {data.strip()}")
            self.send_data_var.set("")
        else:
            messagebox.showerror("错误", f"发送失败: {port}")
    
    def _add_to_batch(self):
        """将当前配置添加到批量配置列表"""
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("警告", "请选择串口")
            return
        
        try:
            baudrate = int(self.baudrate_var.get())
        except ValueError:
            messagebox.showerror("错误", "波特率必须是数字")
            return
        
        keywords, regex_patterns = self._get_filter_config()
        
        # 检查是否已存在
        for config in self.batch_port_configs:
            if config['port'] == port:
                messagebox.showinfo("提示", f"串口 {port} 已在批量配置中")
                return
        
        config = {
            'port': port,
            'baudrate': baudrate,
            'keywords': keywords,
            'regex_patterns': regex_patterns
        }
        
        self.batch_port_configs.append(config)
        self._save_batch_configs()
        self.status_var.set(f"已添加 {port} 到批量配置 (共{len(self.batch_port_configs)}个)")
    
    def _start_batch(self):
        """快速启动批量配置的所有串口"""
        if not self.batch_port_configs:
            messagebox.showwarning("警告", "批量配置为空，请先添加串口配置")
            return
        
        # 准备回调函数
        def callback(port, timestamp, data, colored_log_entry=""):
            self._display_data(port, timestamp, data)
        
        # 为每个配置添加回调
        configs_with_callback = []
        for config in self.batch_port_configs:
            config_copy = config.copy()
            config_copy['callback'] = callback
            config_copy['enable_color'] = False
            configs_with_callback.append(config_copy)
        
        # 使用并行启动
        self.status_var.set("正在并行启动批量串口...")
        self.root.update()
        
        # 在后台线程中执行以避免阻塞UI
        def start_thread():
            results = self.monitor.add_monitors_parallel(configs_with_callback)
            
            # 更新配置和UI
            success_count = 0
            failed_ports = []
            for port, success in results.items():
                if success:
                    success_count += 1
                    # 保存端口配置
                    for config in self.batch_port_configs:
                        if config['port'] == port:
                            self.port_configs[port] = config
                            break
                else:
                    failed_ports.append(port)
            
            # 在主线程中更新UI
            self.root.after(0, lambda: self._update_after_batch_start(success_count, failed_ports))
        
        threading.Thread(target=start_thread, daemon=True).start()
    
    def _update_after_batch_start(self, success_count, failed_ports):
        """批量启动后更新UI"""
        self._update_active_list()
        
        if failed_ports:
            msg = f"批量启动完成: 成功{success_count}个，失败{len(failed_ports)}个\n失败串口: {', '.join(failed_ports)}"
            messagebox.showwarning("部分成功", msg)
        else:
            msg = f"批量启动成功: 已启动{success_count}个串口"
            messagebox.showinfo("成功", msg)
        
        self.status_var.set(f"批量启动完成: {success_count}个串口已就绪")
    
    def _clear_batch(self):
        """清空批量配置"""
        if not self.batch_port_configs:
            messagebox.showinfo("提示", "批量配置已为空")
            return
        
        result = messagebox.askyesno("确认", f"确定要清空所有批量配置吗？(共{len(self.batch_port_configs)}个)")
        if result:
            self.batch_port_configs.clear()
            self._save_batch_configs()
            self.status_var.set("已清空批量配置")
    
    def _show_batch_configs(self):
        """显示批量配置详情"""
        if not self.batch_port_configs:
            messagebox.showinfo("批量配置", "批量配置为空")
            return
        
        info = f"批量配置列表 (共{len(self.batch_port_configs)}个):\n\n"
        for i, config in enumerate(self.batch_port_configs, 1):
            info += f"{i}. {config['port']} @ {config['baudrate']} bps"
            if config.get('keywords'):
                info += f"\n   关键词: {', '.join(config['keywords'])}"
            if config.get('regex_patterns'):
                info += f"\n   正则: {', '.join(config['regex_patterns'])}"
            info += "\n\n"
        
        messagebox.showinfo("批量配置详情", info)
    
    def _save_config(self):
        """保存配置到文件"""
        config = {
            'baudrate': self.baudrate_var.get(),
            'keywords': self.keywords_var.get(),
            'regex': self.regex_var.get(),
            'send_data': self.send_data_var.get()
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _save_batch_configs(self):
        """保存批量配置到文件"""
        try:
            with open(self.batch_configs_file, 'w', encoding='utf-8') as f:
                json.dump(self.batch_port_configs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存批量配置失败: {e}")
    
    def _load_config(self):
        """从文件加载配置"""
        # 加载基本配置
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 恢复配置
                if 'baudrate' in config:
                    self.baudrate_var.set(config['baudrate'])
                if 'keywords' in config:
                    self.keywords_var.set(config['keywords'])
                if 'regex' in config:
                    self.regex_var.set(config['regex'])
                if 'send_data' in config:
                    self.send_data_var.set(config['send_data'])
                    
                self.status_var.set("已加载上次配置")
            except Exception as e:
                print(f"加载配置失败: {e}")
        
        # 加载批量配置
        if os.path.exists(self.batch_configs_file):
            try:
                with open(self.batch_configs_file, 'r', encoding='utf-8') as f:
                    self.batch_port_configs = json.load(f)
                if self.batch_port_configs:
                    self.status_var.set(f"已加载上次配置和{len(self.batch_port_configs)}个批量串口配置")
            except Exception as e:
                print(f"加载批量配置失败: {e}")
    
    def _format_bytes(self, bytes_count: int) -> str:
        """格式化字节数为可读格式"""
        if bytes_count < 1024:
            return f"{bytes_count} B"
        elif bytes_count < 1024 * 1024:
            return f"{bytes_count / 1024:.2f} KB"
        elif bytes_count < 1024 * 1024 * 1024:
            return f"{bytes_count / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"
    
    def _update_stats_display(self):
        """更新统计信息显示（优化：延迟配置标签）"""
        try:
            # 首次调用时配置颜色标签
            if not self._stats_tags_configured:
                self.stats_display.tag_config("port_name", foreground="blue", font=("TkDefaultFont", 9, "bold"))
                self.stats_display.tag_config("bytes", foreground="green", font=("TkDefaultFont", 9))
                self.stats_display.tag_config("separator", foreground="gray")
                self._stats_tags_configured = True
            
            # 获取所有串口的统计信息
            all_stats = self.monitor.get_all_stats()
            
            if not all_stats:
                # 没有活动串口
                self.stats_display.config(state=tk.NORMAL)
                self.stats_display.delete('1.0', tk.END)
                self.stats_display.insert(tk.END, "无活动串口", "separator")
                self.stats_display.config(state=tk.DISABLED)
                return
            
            # 构建显示内容
            self.stats_display.config(state=tk.NORMAL)
            self.stats_display.delete('1.0', tk.END)
            
            # 按端口排序
            sorted_ports = sorted(all_stats.keys())
            
            for i, port in enumerate(sorted_ports):
                stats = all_stats[port]
                bytes_count = stats['total_bytes']
                formatted_bytes = self._format_bytes(bytes_count)
                
                # 插入端口名
                self.stats_display.insert(tk.END, port, "port_name")
                self.stats_display.insert(tk.END, ": ", "separator")
                self.stats_display.insert(tk.END, formatted_bytes, "bytes")
                
                # 如果不是最后一个，添加分隔符
                if i < len(sorted_ports) - 1:
                    self.stats_display.insert(tk.END, "  |  ", "separator")
            
            self.stats_display.config(state=tk.DISABLED)
            
        except Exception as e:
            print(f"更新统计信息错误: {e}")
    
    def _start_stats_update_loop(self):
        """启动统计信息更新循环"""
        self._update_stats_display()
        self.root.after(self.stats_update_interval, self._start_stats_update_loop)
    
    def close(self):
        """关闭应用"""
        self._save_config()
        self.monitor.stop_all()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SerialToolGUI(root)
    
    def on_closing():
        app.close()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()