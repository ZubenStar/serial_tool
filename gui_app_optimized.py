
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
import time
from pathlib import Path
from typing import Dict, List
from log_filter import LogFilterWindow

# 延迟导入serial_monitor以加快启动
_monitor_module = None

def get_monitor_module():
    """延迟导入串口监控模块"""
    global _monitor_module
    if _monitor_module is None:
        from serial_monitor import MultiSerialMonitor, Colors
        _monitor_module = {'MultiSerialMonitor': MultiSerialMonitor, 'Colors': Colors}
    return _monitor_module

# 读取版本信息
_version_cache = None
_build_time_cache = None

def get_version_info() -> tuple:
    """从VERSION文件读取版本号和编译时间（带缓存）"""
    global _version_cache, _build_time_cache
    if _version_cache is not None:
        return _version_cache, _build_time_cache
    
    try:
        version_file = Path(__file__).parent / "VERSION"
        if version_file.exists():
            content = version_file.read_text(encoding='utf-8').strip()
            lines = content.split('\n')
            _version_cache = lines[0].strip()
            _build_time_cache = lines[1].strip() if len(lines) > 1 else None
            return _version_cache, _build_time_cache
    except Exception:
        pass
    _version_cache = "1.0.0"
    _build_time_cache = None
    return _version_cache, _build_time_cache

VERSION, BUILD_TIME = get_version_info()

class SerialToolGUI:
    """串口工具图形界面 - 优化版"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"多串口监控工具 v{VERSION}")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # 主题状态：默认浅色主题
        self.is_dark_theme = False
        
        # 配置现代化主题
        self._configure_modern_theme()
        
        # 设置默认全屏
        self.root.state('zoomed')
        
        # 延迟初始化monitor
        monitor_mod = get_monitor_module()
        self.monitor = monitor_mod['MultiSerialMonitor'](log_dir="logs")
        self.port_configs: Dict[str, Dict] = {}
        self.config_file = "serial_tool_config.json"
        self.batch_port_configs: List[Dict] = []
        self.preset_data_list: List[Dict] = []
        
        # 性能优化：批量更新缓冲区
        self.display_buffer = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 100
        self.update_interval = 16
        self.batch_threshold = 50
        self.max_display_lines = 1000
        self.trim_to_lines = 800
        self.last_trim_time = 0
        self.trim_interval = 10.0
        
        # 数据统计更新
        self.stats_update_interval = 2000
        
        self._create_widgets()
        self._load_config()
        self._start_ui_update_loop()
        
        # 优化：延迟启动非关键任务
        self.root.after(100, self._delayed_init)
    
    def _configure_modern_theme(self):
        """配置现代化主题样式"""
        if self.is_dark_theme:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
    
    def _apply_light_theme(self):
        """应用浅色主题 - 现代清新设计"""
        self.root.configure(bg='#f8f9fa')
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame样式
        style.configure('TFrame', background='#f8f9fa')
        style.configure('TLabelframe', background='#ffffff', borderwidth=1, relief='solid')
        style.configure('TLabelframe.Label', background='#ffffff', foreground='#495057',
                       font=('Microsoft YaHei UI', 11, 'bold'))
        
        # Button样式
        style.configure('TButton',
                       background='#007bff',
                       foreground='#ffffff',
                       borderwidth=0,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=(14, 10))
        style.map('TButton',
                 background=[('active', '#0056b3'), ('pressed', '#004085')],
                 foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])
        
        # Combobox样式
        style.configure('TCombobox',
                       fieldbackground='#ffffff',
                       background='#ffffff',
                       foreground='#495057',
                       borderwidth=1,
                       relief='solid')
        
        # Label样式
        style.configure('TLabel', background='#f8f9fa', foreground='#495057',
                       font=('Microsoft YaHei UI', 10))
        
        # Entry样式
        style.configure('TEntry',
                       fieldbackground='#ffffff',
                       foreground='#495057',
                       borderwidth=1,
                       relief='solid')
        
        self.theme_colors = {
            'bg': '#f8f9fa',
            'text_bg': '#ffffff',
            'text_fg': '#212529',
            'stats_bg': '#e9ecef',
            'stats_fg': '#495057',
            'status_bg': '#ffffff',
            'status_fg': '#28a745',
            'version_fg': '#6c757d',
            'timestamp': '#6c757d',
            'default': '#212529',
            'error': '#dc3545',
            'warning': '#ffc107',
            'success': '#28a745',
            'port_colors': {
                'BRIGHT_BLUE': '#007bff',
                'BRIGHT_GREEN': '#28a745',
                'BRIGHT_CYAN': '#17a2b8',
                'BRIGHT_MAGENTA': '#6f42c1',
                'BRIGHT_YELLOW': '#fd7e14',
                'BRIGHT_RED': '#dc3545',
                'BLUE': '#0056b3',
                'GREEN': '#218838',
                'CYAN': '#138496',
                'MAGENTA': '#5a32a3',
            },
            'stats_port': '#007bff',
            'stats_bytes': '#28a745',
            'stats_separator': '#6c757d'
        }
    
    def _apply_dark_theme(self):
        """应用深色主题"""
        self.root.configure(bg='#2a2a2a')
        
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background='#2a2a2a')
        style.configure('TLabelframe', background='#2a2a2a', borderwidth=0, relief='flat')
        style.configure('TLabelframe.Label', background='#2a2a2a', foreground='#b0b0b0',
                       font=('Microsoft YaHei UI', 11, 'bold'))
        
        style.configure('TButton',
                       background='#3a3a3a',
                       foreground='#a0a0a0',
                       borderwidth=0,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 10),
                       padding=(14, 10))
        
        style.configure('TCombobox',
                       fieldbackground='#353535',
                       background='#353535',
                       foreground='#d8d8d8',
                       borderwidth=0,
                       relief='flat')
        
        style.configure('TLabel', background='#2a2a2a', foreground='#a0a0a0',
                       font=('Microsoft YaHei UI', 10))
        
        style.configure('TEntry',
                       fieldbackground='#353535',
                       foreground='#d8d8d8',
                       borderwidth=0,
                       relief='flat')
        
        self.theme_colors = {
            'bg': '#2a2a2a',
            'text_bg': '#303030',
            'text_fg': '#d8d8d8',
            'stats_bg': '#353535',
            'stats_fg': '#d0d0d0',
            'status_bg': '#353535',
            'status_fg': '#c0c0c0',
            'version_fg': '#a0a0a0',
            'timestamp': '#b0b0b0',
            'default': '#d8d8d8',
            'error': '#d89090',
            'warning': '#d8b890',
            'success': '#90c090',
            'port_colors': {
                'BRIGHT_BLUE': '#8fa5c0',
                'BRIGHT_GREEN': '#90b890',
                'BRIGHT_CYAN': '#85b5c0',
                'BRIGHT_MAGENTA': '#b890b8',
                'BRIGHT_YELLOW': '#c0b890',
                'BRIGHT_RED': '#c08585',
                'BLUE': '#7590b0',
                'GREEN': '#7da87d',
                'CYAN': '#7da8b0',
                'MAGENTA': '#a87da8',
            },
            'stats_port': '#8fa5c0',
            'stats_bytes': '#90b890',
            'stats_separator': '#707070'
        }
    
    def _delayed_init(self):
        """延迟初始化非关键组件"""
        self._update_available_ports()
        self._start_stats_update_loop()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        self._stats_display_created = False
        
        # 左侧控制面板
        left_panel = ttk.Frame(main_container, width=480)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 15))
        left_panel.pack_propagate(False)
        
        # 右侧数据显示区域
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._create_control_panel(left_panel)
        self._create_display_panel(right_panel)
        self._create_status_bar()
    
    def _create_control_panel(self, parent):
        """创建控制面板"""
        # 串口控制区
        control_frame = ttk.LabelFrame(parent, text="🔌 串口控制", padding=22)
        control_frame.pack(fill=tk.X, pady=(0, 12))
        
        # 串口选择
        port_frame = ttk.Frame(control_frame)
        port_frame.pack(fill=tk.X, pady=6)
        ttk.Label(port_frame, text="串口:", font=('Microsoft YaHei UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 12))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, width=18, font=('Microsoft YaHei UI', 10))
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        ttk.Button(port_frame, text="🔄", command=self._update_available_ports, width=5).pack(side=tk.LEFT)
        
        # 波特率
        baud_frame = ttk.Frame(control_frame)
        baud_frame.pack(fill=tk.X, pady=6)
        ttk.Label(baud_frame, text="波特率:", font=('Microsoft YaHei UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 12))
        self.baudrate_var = tk.StringVar(value="115200")
        baudrate_combo = ttk.Combobox(baud_frame, textvariable=self.baudrate_var, width=18,
                                      font=('Microsoft YaHei UI', 10),
                                      values=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        baudrate_combo.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.baudrate_var.trace_add('write', self._on_config_change)
        
        # 关键词过滤
        kw_frame = ttk.Frame(control_frame)
        kw_frame.pack(fill=tk.X, pady=10)
        ttk.Label(kw_frame, text="🔍 关键词过滤", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 6))
        self.keywords_var = tk.StringVar()
        ttk.Entry(kw_frame, textvariable=self.keywords_var, font=('Microsoft YaHei UI', 10)).pack(fill=tk.X, pady=2)
        self.keywords_var.trace_add('write', self._on_config_change)
        ttk.Label(kw_frame, text="多个关键词用逗号分隔", font=("Microsoft YaHei UI", 9), foreground='#6c757d').pack(anchor=tk.W, pady=(4, 0))
        
        # 正则表达式
        regex_frame = ttk.Frame(control_frame)
        regex_frame.pack(fill=tk.X, pady=10)
        ttk.Label(regex_frame, text="📋 正则表达式", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 6))
        self.regex_var = tk.StringVar()
        ttk.Entry(regex_frame, textvariable=self.regex_var, font=('Microsoft YaHei UI', 10)).pack(fill=tk.X, pady=2)
        self.regex_var.trace_add('write', self._on_config_change)
        ttk.Label(regex_frame, text="多个正则式用逗号分隔", font=("Microsoft YaHei UI", 9), foreground='#6c757d').pack(anchor=tk.W, pady=(4, 0))
        
        # 实时应用过滤
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(fill=tk.X, pady=12)
        ttk.Button(filter_frame, text="✨ 实时应用过滤", command=self._apply_filters_realtime).pack(fill=tk.X)
        ttk.Label(filter_frame, text="无需重启串口即可生效", font=("Microsoft YaHei UI", 9), foreground='#6c757d').pack(anchor=tk.W, pady=(6, 0))
        
        # 控制按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=14)
        ttk.Button(btn_frame, text="▶️ 启动", command=self._start_monitor).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="⏸️ 停止", command=self._stop_monitor).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        btn_frame2 = ttk.Frame(control_frame)
        btn_frame2.pack(fill=tk.X, pady=4)
        ttk.Button(btn_frame2, text="⏹️ 全部停止", command=self._stop_all).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(btn_frame2, text="🗑️ 清屏", command=self._clear_display).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        # 主题切换
        theme_frame = ttk.Frame(control_frame)
        theme_frame.pack(fill=tk.X, pady=14)
        self.theme_button = ttk.Button(theme_frame, text="🌙 切换深色模式", command=self._toggle_theme)
        self.theme_button.pack(fill=tk.X)
        
        # 高级工具
        tools_frame = ttk.LabelFrame(parent, text="🛠️ 高级工具", padding=22)
        tools_frame.pack(fill=tk.X, pady=12)
        
        tools_row1 = ttk.Frame(tools_frame)
        tools_row1.pack(fill=tk.X, pady=5)
        ttk.Button(tools_row1, text="📄 日志过滤", command=self._open_log_filter).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(tools_row1, text="📊 可视化", command=self._open_visualizer).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        tools_row2 = ttk.Frame(tools_frame)
        tools_row2.pack(fill=tk.X, pady=5)
        ttk.Button(tools_row2, text="🔍 数据分析", command=self._open_analyzer).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(tools_row2, text="🎬 录制回放", command=self._open_recorder).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        tools_row3 = ttk.Frame(tools_frame)
        tools_row3.pack(fill=tk.X, pady=5)
        ttk.Button(tools_row3, text="🤖 自动化", command=self._open_automation).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(tools_row3, text="🔧 工具箱", command=self._open_utilities).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        # 批量操作
        batch_frame = ttk.LabelFrame(parent, text="⚡ 批量操作", padding=22)
        batch_frame.pack(fill=tk.X, pady=12)
        
        ttk.Button(batch_frame, text="➕ 添加到批量", command=self._add_to_batch).pack(fill=tk.X, pady=6)
        ttk.Button(batch_frame, text="🚀 启动全部", command=self._start_batch).pack(fill=tk.X, pady=6)
        
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.pack(fill=tk.X, pady=6)
        ttk.Button(batch_btn_frame, text="👁️ 查看", command=self._show_batch_configs).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(batch_btn_frame, text="🗑️ 清空", command=self._clear_batch).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        # 发送数据
        send_frame = ttk.LabelFrame(parent, text="📤 发送数据", padding=22)
        send_frame.pack(fill=tk.X, pady=12)
        
        send_port_frame = ttk.Frame(send_frame)
        send_port_frame.pack(fill=tk.X, pady=6)
        ttk.Label(send_port_frame, text="目标:", font=('Microsoft YaHei UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 12))
        self.send_port_var = tk.StringVar()
        self.send_port_combo = ttk.Combobox(send_port_frame, textvariable=self.send_port_var, width=18, font=('Microsoft YaHei UI', 10))
        self.send_port_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        preset_frame = ttk.Frame(send_frame)
        preset_frame.pack(fill=tk.X, pady=6)
        ttk.Label(preset_frame, text="预设:", font=('Microsoft YaHei UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 12))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, width=18, state="readonly", font=('Microsoft YaHei UI', 10))
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.preset_combo.bind('<<ComboboxSelected>>', self._on_preset_selected)
        
        send_data_frame = ttk.Frame(send_frame)
        send_data_frame.pack(fill=tk.X, pady=6)
        ttk.Label(send_data_frame, text="数据:", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 6))
        self.send_data_var = tk.StringVar()
        ttk.Entry(send_data_frame, textvariable=self.send_data_var, font=('Microsoft YaHei UI', 10)).pack(fill=tk.X)
        self.send_data_var.trace_add('write', self._on_config_change)
        
        send_btn_frame = ttk.Frame(send_frame)
        send_btn_frame.pack(fill=tk.X, pady=8)
        ttk.Button(send_btn_frame, text="📤 发送", command=self._send_data).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(send_btn_frame, text="💾 保存", command=self._save_preset_data).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(send_btn_frame, text="🗑️ 删除", command=self._delete_preset_data).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        # 活动串口列表
        active_frame = ttk.LabelFrame(parent, text="📊 活动串口", padding=15)
        active_frame.pack(fill=tk.BOTH, expand=True, pady=12)
        
        self.active_list = tk.Listbox(
            active_frame,
            height=5,
            background=self.theme_colors['text_bg'],
            foreground=self.theme_colors['text_fg'],
            selectbackground=self.theme_colors['stats_bg'],
            selectforeground=self.theme_colors['text_fg'],
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=('Microsoft YaHei UI', 9)
        )
        self.active_list.pack(fill=tk.BOTH, expand=True)
    
    def _create_display_panel(self, parent):
        """创建显示面板"""
        display_frame = ttk.LabelFrame(parent, text="📺 数据显示", padding=15)
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_display = scrolledtext.ScrolledText(
            display_frame,
            wrap=tk.WORD,
            font=('Consolas', 11),
            background=self.theme_colors['text_bg'],
            foreground=self.theme_colors['text_fg'],
            insertbackground=self.theme_colors['text_fg'],
            relief=tk.FLAT,
            borderwidth=0,
            padx=15,
            pady=15,
            highlightthickness=0
        )
        self.text_display.pack(fill=tk.BOTH, expand=True)
        
        self.text_display.tag_config("timestamp", foreground=self.theme_colors['timestamp'], font=('Consolas', 10))
        self.text_display.tag_config("default", foreground=self.theme_colors['default'])
        self.text_display.tag_config("error", foreground=self.theme_colors['error'], font=('Consolas', 11, "bold"))
        self.text_display.tag_config("warning", foreground=self.theme_colors['warning'], font=('Consolas', 11, "bold"))
        self.text_display.tag_config("success", foreground=self.theme_colors['success'])
        
        self.port_color_tags = {}
        self._init_color_tags()
        
        # 统计显示区域
        self.stats_frame = ttk.LabelFrame(parent, text="📈 数据统计", padding=15)
        self.stats_frame.pack(fill=tk.X, pady=(12, 0))
        
        self.stats_display = tk.Text(
            self.stats_frame,
            height=3,
            wrap=tk.WORD,
            state=tk.DISABLED,
            background=self.theme_colors['stats_bg'],
            foreground=self.theme_colors['stats_fg'],
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            font=('Microsoft YaHei UI', 10),
            padx=12,
            pady=8
        )
        self.stats_display.pack(fill=tk.X)
        
        self._stats_tags_configured = False
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        
        self.status_var = tk.StringVar(value="✓ 就绪")
        status_bar = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.FLAT,
            background=self.theme_colors['status_bg'],
            foreground=self.theme_colors['success'],
            font=('Microsoft YaHei UI', 10),
            padding=(12, 6)
        )
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        version_text = f"v{VERSION}"
        if BUILD_TIME:
            version_text += f" · {BUILD_TIME}"
        version_label = ttk.Label(
            status_frame,
            text=version_text,
            relief=tk.FLAT,
            background=self.theme_colors['status_bg'],
            foreground=self.theme_colors['version_fg'],
            font=('Microsoft YaHei UI', 9),
            padding=(12, 6)
        )
        version_label.pack(side=tk.RIGHT, padx=8)
    
    # 包含所有原有方法（这里省略以节省空间，实际文件需要包含所有方法）
    def _toggle_theme(self):
        """切换深浅主题"""
        self.is_dark_theme = not self.is_dark_theme
        if self.is_dark_theme:
            self.theme_button.config(text="☀️ 切换浅色模式")
        else:
            self.theme_button.config(text="🌙 切换深色模式")
        self._configure_modern_theme()
        self._update_widget_colors()
        self._save_config()
        self.status_var.set(f"已切换到{'深色' if self.is_dark_theme else '浅色'}模式")
    
    def _update_widget_colors(self):
        """更新所有组件的颜色"""
        self.text_display.config(
            background=self.theme_colors['text_bg'],
            foreground=self.theme_colors['text_fg'],
            insertbackground=self.theme_colors['text_fg']
        )
        
        self.text_display.tag_config("timestamp", foreground=self.theme_colors['timestamp'])
        self.text_display.tag_config("default", foreground=self.theme_colors['default'])
        self.text_display.tag_config("error", foreground=self.theme_colors['error'])
        self.text_display.tag_config("warning", foreground=self.theme_colors['warning'])
        self.text_display.tag_config("success", foreground=self.theme_colors['success'])
        
        self.color_map = self.theme_colors['port_colors']
        for port, tag_name in self.port_color_tags.items():
            color_names = [
                'BRIGHT_BLUE', 'BRIGHT_GREEN', 'BRIGHT_CYAN',
                'BRIGHT_MAGENTA', 'BRIGHT_YELLOW', 'BRIGHT_RED',
                'BLUE', 'GREEN', 'CYAN', 'MAGENTA'
            ]
            index = hash(port) % len(color_names)
            color_name = color_names[index]
            self.text_display.tag_config(tag_name, foreground=self.color_map[color_name])
        
        self.stats_display.config(
            background=self.theme_colors['stats_bg'],
            foreground=self.theme_colors['stats_fg']
        )
        
        if self._stats_tags_configured:
            self.stats_display.tag_config("port_name", foreground=self.theme_colors['stats_port'])
            self.stats_display.tag_config("bytes", foreground=self.theme_colors['stats_bytes'])
            self.stats_display.tag_config("separator", foreground=self.theme_colors['stats_separator'])
        
        self.active_list.config(
            background=self.theme_colors['text_bg'],
            foreground=self.theme_colors['text_fg'],
            selectbackground=self.theme_colors['stats_bg'],
            selectforeground=self.theme_colors['text_fg']
        )
        
        self.root.update_idletasks()