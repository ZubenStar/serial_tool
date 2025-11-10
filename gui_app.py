import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
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

# 读取版本信息 - 优化：缓存版本号
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
    """串口工具图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"多串口监控工具 v{VERSION}")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # 主题状态：默认深色主题
        self.is_dark_theme = True
        
        # 配置现代化主题
        self._configure_modern_theme()
        
        # 设置默认全屏
        self.root.state('zoomed')
        
        # 延迟初始化monitor
        monitor_mod = get_monitor_module()
        self.monitor = monitor_mod['MultiSerialMonitor'](log_dir="logs")
        self.port_configs: Dict[str, Dict] = {}
        self.config_file = "serial_tool_config.json"  # 统一配置文件
        self.batch_port_configs: List[Dict] = []  # 批量串口配置列表
        self.preset_data_list: List[Dict] = []  # 预设数据列表
        
        # 性能优化：批量更新缓冲区 - 激进的实时显示策略
        self.display_buffer = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 100  # 批量处理的最大条目数
        self.update_interval = 16  # UI更新间隔(毫秒) - 约60fps，减少CPU压力
        self.batch_threshold = 50  # 超过此值才批量处理
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
    
    def _configure_modern_theme(self):
        """配置现代化主题样式 - 支持深浅切换"""
        if self.is_dark_theme:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
    
    def _apply_light_theme(self):
        """应用浅色主题 - 现代清新护眼设计"""
        # 设置清新的背景色
        self.root.configure(bg='#f8f9fa')
        
        # 配置ttk样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置Frame样式 - 现代简洁
        style.configure('TFrame', background='#f8f9fa')
        style.configure('TLabelframe', background='#ffffff', borderwidth=1, relief='solid')
        style.configure('TLabelframe.Label', background='#ffffff', foreground='#495057',
                       font=('Microsoft YaHei UI', 11, 'bold'))
        
        # 配置Button样式 - 现代蓝色调
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
        
        # 配置Combobox样式 - 现代边框
        style.configure('TCombobox',
                       fieldbackground='#ffffff',
                       background='#ffffff',
                       foreground='#495057',
                       borderwidth=1,
                       relief='solid')
        style.map('TCombobox',
                 foreground=[('readonly', '#495057')])
        
        # 配置Label样式 - 清晰文字
        style.configure('TLabel', background='#f8f9fa', foreground='#495057',
                       font=('Microsoft YaHei UI', 10))
        
        # 配置Entry样式 - 现代边框
        style.configure('TEntry',
                       fieldbackground='#ffffff',
                       foreground='#495057',
                       borderwidth=1,
                       relief='solid')
        
        # 存储浅色主题配色 - 现代清新
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
        """应用深色主题 - 现代深色设计"""
        # 设置现代深色背景
        self.root.configure(bg='#1e1e1e')
        
        # 配置ttk样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置Frame样式 - 现代深色
        style.configure('TFrame', background='#1e1e1e')
        style.configure('TLabelframe', background='#2d2d2d', borderwidth=1, relief='solid')
        style.configure('TLabelframe.Label', background='#2d2d2d', foreground='#d4d4d4',
                       font=('Microsoft YaHei UI', 11, 'bold'))
        
        # 配置Button样式 - 现代蓝色调
        style.configure('TButton',
                       background='#0e639c',
                       foreground='#ffffff',
                       borderwidth=0,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=(14, 10))
        style.map('TButton',
                 background=[('active', '#1177bb'), ('pressed', '#1e88cf')],
                 foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])
        
        # 配置Combobox样式 - 现代深色
        style.configure('TCombobox',
                       fieldbackground='#2d2d2d',
                       background='#2d2d2d',
                       foreground='#d4d4d4',
                       borderwidth=1,
                       relief='solid')
        style.map('TCombobox',
                 foreground=[('readonly', '#d4d4d4')])
        
        # 配置Label样式 - 现代深色
        style.configure('TLabel', background='#1e1e1e', foreground='#d4d4d4',
                       font=('Microsoft YaHei UI', 10))
        
        # 配置Entry样式 - 现代深色
        style.configure('TEntry',
                       fieldbackground='#2d2d2d',
                       foreground='#d4d4d4',
                       borderwidth=1,
                       relief='solid')
        
        # 存储深色主题配色 - 现代深色
        self.theme_colors = {
            'bg': '#1e1e1e',
            'text_bg': '#2d2d2d',
            'text_fg': '#d4d4d4',
            'stats_bg': '#252526',
            'stats_fg': '#cccccc',
            'status_bg': '#2d2d2d',
            'status_fg': '#4ec9b0',
            'version_fg': '#858585',
            'timestamp': '#858585',
            'default': '#d4d4d4',
            'error': '#f48771',
            'warning': '#dcdcaa',
            'success': '#4ec9b0',
            'port_colors': {
                'BRIGHT_BLUE': '#569cd6',
                'BRIGHT_GREEN': '#4ec9b0',
                'BRIGHT_CYAN': '#4fc1ff',
                'BRIGHT_MAGENTA': '#c586c0',
                'BRIGHT_YELLOW': '#dcdcaa',
                'BRIGHT_RED': '#f48771',
                'BLUE': '#3f8dd6',
                'GREEN': '#3fa9a0',
                'CYAN': '#3fb1ef',
                'MAGENTA': '#b576b0',
            },
            'stats_port': '#569cd6',
            'stats_bytes': '#4ec9b0',
            'stats_separator': '#858585'
        }
    
    def _delayed_init(self):
        """延迟初始化非关键组件"""
        self._update_available_ports()
        self._start_stats_update_loop()
        
    def _create_widgets(self):
        """创建界面组件 - 优化的左右布局，带滚动条"""
        # 创建主容器框架
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # 优化：使用after延迟初始化统计显示，减少启动时间
        self._stats_display_created = False
        
        # 左侧面板容器 - 带滚动条
        left_container = ttk.Frame(main_container, width=460)
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 15))
        left_container.pack_propagate(False)
        
        # 创建Canvas和Scrollbar
        self.left_canvas = tk.Canvas(
            left_container,
            background=self.theme_colors['bg'],
            highlightthickness=0,
            bd=0
        )
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=self.left_canvas.yview)
        left_panel = ttk.Frame(self.left_canvas)
        
        # 配置滚动
        left_panel.bind(
            "<Configure>",
            lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))
        )
        
        canvas_window = self.left_canvas.create_window((0, 0), window=left_panel, anchor="nw")
        
        # 绑定宽度调整
        def _configure_canvas_width(event):
            self.left_canvas.itemconfig(canvas_window, width=event.width)
        self.left_canvas.bind("<Configure>", _configure_canvas_width)
        
        self.left_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局Canvas和Scrollbar - 移除padding
        scrollbar.pack(side="right", fill="y")
        self.left_canvas.pack(side="left", fill="both", expand=True)
        
        # 鼠标滚轮绑定
        def _on_mousewheel(event):
            self.left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 右侧数据显示区域
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))
        
        # === 左侧面板内容 ===
        # 串口控制区 - 紧凑布局
        control_frame = ttk.LabelFrame(left_panel, text="🔌 串口控制", padding=15)
        control_frame.pack(fill=tk.X, pady=(0, 8))
        
        # 串口选择
        port_frame = ttk.Frame(control_frame)
        port_frame.pack(fill=tk.X, pady=5)
        ttk.Label(port_frame, text="串口:", font=('Microsoft YaHei UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, width=16, font=('Microsoft YaHei UI', 10))
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        ttk.Button(port_frame, text="🔄", command=self._update_available_ports, width=5).pack(side=tk.LEFT)
        
        # 波特率
        baud_frame = ttk.Frame(control_frame)
        baud_frame.pack(fill=tk.X, pady=5)
        ttk.Label(baud_frame, text="波特率:", font=('Microsoft YaHei UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        self.baudrate_var = tk.StringVar(value="115200")
        baudrate_combo = ttk.Combobox(baud_frame, textvariable=self.baudrate_var, width=16,
                                      font=('Microsoft YaHei UI', 10),
                                      values=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600", "3000000"])
        baudrate_combo.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.baudrate_var.trace_add('write', self._on_config_change)
        
        # 波特率修改按钮行
        baudrate_btn_frame = ttk.Frame(control_frame)
        baudrate_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(baudrate_btn_frame, text="🔧 修改当前", command=self._change_current_baudrate).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(baudrate_btn_frame, text="🔧 修改全部", command=self._change_all_baudrates).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        # 关键词过滤
        kw_frame = ttk.Frame(control_frame)
        kw_frame.pack(fill=tk.X, pady=8)
        ttk.Label(kw_frame, text="🔍 关键词过滤", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 6))
        self.keywords_var = tk.StringVar()
        ttk.Entry(kw_frame, textvariable=self.keywords_var, font=('Microsoft YaHei UI', 10)).pack(fill=tk.X, pady=2)
        self.keywords_var.trace_add('write', self._on_config_change)
        ttk.Label(kw_frame, text="多个关键词用逗号分隔", font=("Microsoft YaHei UI", 9), foreground='#6c757d').pack(anchor=tk.W, pady=(4, 0))
        
        # 正则表达式
        regex_frame = ttk.Frame(control_frame)
        regex_frame.pack(fill=tk.X, pady=8)
        ttk.Label(regex_frame, text="📋 正则表达式", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 6))
        self.regex_var = tk.StringVar()
        ttk.Entry(regex_frame, textvariable=self.regex_var, font=('Microsoft YaHei UI', 10)).pack(fill=tk.X, pady=2)
        self.regex_var.trace_add('write', self._on_config_change)
        ttk.Label(regex_frame, text="多个正则式用逗号分隔", font=("Microsoft YaHei UI", 9), foreground='#6c757d').pack(anchor=tk.W, pady=(4, 0))
        
        # 实时应用过滤按钮
        filter_apply_frame = ttk.Frame(control_frame)
        filter_apply_frame.pack(fill=tk.X, pady=10)
        ttk.Button(filter_apply_frame, text="✨ 实时应用过滤", command=self._apply_filters_realtime).pack(fill=tk.X)
        ttk.Label(filter_apply_frame, text="无需重启串口即可生效", font=("Microsoft YaHei UI", 9), foreground='#6c757d').pack(anchor=tk.W, pady=(6, 0))
        
        # 控制按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=12)
        ttk.Button(btn_frame, text="▶️ 启动", command=self._start_monitor).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="⏸️ 停止", command=self._stop_monitor).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        btn_frame2 = ttk.Frame(control_frame)
        btn_frame2.pack(fill=tk.X, pady=4)
        ttk.Button(btn_frame2, text="⏹️ 全部停止", command=self._stop_all).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(btn_frame2, text="🗑️ 清屏", command=self._clear_display).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        # 主题切换按钮
        theme_frame = ttk.Frame(control_frame)
        theme_frame.pack(fill=tk.X, pady=12)
        self.theme_button = ttk.Button(theme_frame, text="🌙 切换深色模式", command=self._toggle_theme)
        self.theme_button.pack(fill=tk.X)
        
        # 批量操作区
        batch_frame = ttk.LabelFrame(left_panel, text="⚡ 批量操作", padding=15)
        batch_frame.pack(fill=tk.X, pady=8)
        
        ttk.Button(batch_frame, text="➕ 添加到批量", command=self._add_to_batch).pack(fill=tk.X, pady=5)
        ttk.Button(batch_frame, text="🚀 启动全部", command=self._start_batch).pack(fill=tk.X, pady=5)
        
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(batch_btn_frame, text="👁️ 查看", command=self._show_batch_configs).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(batch_btn_frame, text="🗑️ 清空", command=self._clear_batch).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        
        # 高级工具按钮区
        tools_frame = ttk.LabelFrame(left_panel, text="🛠️ 高级工具", padding=15)
        tools_frame.pack(fill=tk.X, pady=8)
        
        # 工具按钮
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
        
        # 发送数据区 - 紧凑布局
        send_frame = ttk.LabelFrame(left_panel, text="📤 发送数据", padding=12)
        send_frame.pack(fill=tk.X, pady=8)
        
        send_port_frame = ttk.Frame(send_frame)
        send_port_frame.pack(fill=tk.X, pady=3)
        ttk.Label(send_port_frame, text="目标:", font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 8))
        self.send_port_var = tk.StringVar()
        self.send_port_combo = ttk.Combobox(send_port_frame, textvariable=self.send_port_var, width=14, font=('Microsoft YaHei UI', 9))
        self.send_port_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 预设数据选择
        preset_frame = ttk.Frame(send_frame)
        preset_frame.pack(fill=tk.X, pady=3)
        ttk.Label(preset_frame, text="预设:", font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 8))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, width=14, state="readonly", font=('Microsoft YaHei UI', 9))
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.preset_combo.bind('<<ComboboxSelected>>', self._on_preset_selected)
        
        send_data_frame = ttk.Frame(send_frame)
        send_data_frame.pack(fill=tk.X, pady=3)
        ttk.Label(send_data_frame, text="数据:", font=('Microsoft YaHei UI', 9, 'bold')).pack(anchor=tk.W, pady=(0, 3))
        self.send_data_var = tk.StringVar()
        ttk.Entry(send_data_frame, textvariable=self.send_data_var, font=('Microsoft YaHei UI', 9)).pack(fill=tk.X)
        self.send_data_var.trace_add('write', self._on_config_change)
        
        # 按钮行：发送、保存预设、删除预设
        send_btn_frame = ttk.Frame(send_frame)
        send_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(send_btn_frame, text="📤 发送", command=self._send_data).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        ttk.Button(send_btn_frame, text="💾 保存", command=self._save_preset_data).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        ttk.Button(send_btn_frame, text="🗑️ 删除", command=self._delete_preset_data).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        
        # === 右侧数据显示区 ===
        display_frame = ttk.LabelFrame(right_panel, text="📺 数据显示", padding=12)
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        # 使用柔和的文本显示区域
        self.text_display = scrolledtext.ScrolledText(
            display_frame,
            wrap=tk.WORD,
            font=('Consolas', 11),
            background=self.theme_colors['text_bg'],
            foreground=self.theme_colors['text_fg'],
            insertbackground=self.theme_colors['text_fg'],
            relief=tk.FLAT,
            borderwidth=0,
            padx=12,
            pady=12,
            highlightthickness=0
        )
        self.text_display.pack(fill=tk.BOTH, expand=True)
        
        # 配置柔和的颜色标签
        self.text_display.tag_config("timestamp", foreground=self.theme_colors['timestamp'], font=('Consolas', 9))
        self.text_display.tag_config("default", foreground=self.theme_colors['default'])
        self.text_display.tag_config("error", foreground=self.theme_colors['error'], font=('Consolas', 10, "bold"))
        self.text_display.tag_config("warning", foreground=self.theme_colors['warning'], font=('Consolas', 10, "bold"))
        self.text_display.tag_config("success", foreground=self.theme_colors['success'])
        
        # 动态端口颜色映射
        self.port_color_tags = {}
        self._init_color_tags()
        
        # 底部信息区域容器
        bottom_info_frame = ttk.Frame(right_panel)
        bottom_info_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 活动串口列表 - 左侧
        active_frame = ttk.LabelFrame(bottom_info_frame, text="📊 活动串口", padding=10)
        active_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.active_list = tk.Listbox(
            active_frame,
            height=3,
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
        
        # 数据统计显示区域 - 右侧
        self.stats_frame = ttk.LabelFrame(bottom_info_frame, text="📈 数据统计", padding=10)
        self.stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 使用Text widget来显示统计信息，支持多行 - 柔和样式
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
            padx=10,
            pady=5
        )
        self.stats_display.pack(fill=tk.BOTH, expand=True)
        
        # 优化：延迟配置颜色标签
        self._stats_tags_configured = False
        
        # 状态栏 - 使用tk.Label以支持背景色切换
        self.status_frame = tk.Frame(self.root, background=self.theme_colors['bg'])
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        self.status_var = tk.StringVar(value="✓ 就绪")
        self.status_bar = tk.Label(
            self.status_frame,
            textvariable=self.status_var,
            relief=tk.FLAT,
            background=self.theme_colors['status_bg'],
            foreground=self.theme_colors['success'],
            font=('Microsoft YaHei UI', 10),
            padx=10,
            pady=5
        )
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 版本信息标签 - 柔和的样式
        version_text = f"v{VERSION}"
        if BUILD_TIME:
            version_text += f" · {BUILD_TIME}"
        self.version_label = tk.Label(
            self.status_frame,
            text=version_text,
            relief=tk.FLAT,
            background=self.theme_colors['status_bg'],
            foreground=self.theme_colors['version_fg'],
            font=('Microsoft YaHei UI', 8),
            padx=10,
            pady=5
        )
        self.version_label.pack(side=tk.RIGHT, padx=5)
    
    def _toggle_theme(self):
        """切换深浅主题"""
        self.is_dark_theme = not self.is_dark_theme
        
        # 更新按钮文本
        if self.is_dark_theme:
            self.theme_button.config(text="☀️ 切换浅色模式")
        else:
            self.theme_button.config(text="🌙 切换深色模式")
        
        # 重新应用主题
        self._configure_modern_theme()
        
        # 更新所有组件的颜色
        self._update_widget_colors()
        
        # 保存主题设置到配置
        self._save_config()
        
        self.status_var.set(f"已切换到{'深色' if self.is_dark_theme else '浅色'}模式")
    
    def _update_widget_colors(self):
        """更新所有组件的颜色"""
        # 更新Canvas背景色
        if hasattr(self, 'left_canvas'):
            self.left_canvas.config(background=self.theme_colors['bg'])
        
        # 更新状态栏背景色
        if hasattr(self, 'status_frame'):
            self.status_frame.config(background=self.theme_colors['bg'])
        if hasattr(self, 'status_bar'):
            self.status_bar.config(
                background=self.theme_colors['status_bg'],
                foreground=self.theme_colors['success']
            )
        if hasattr(self, 'version_label'):
            self.version_label.config(
                background=self.theme_colors['status_bg'],
                foreground=self.theme_colors['version_fg']
            )
        
        # 更新文本显示区域
        self.text_display.config(
            background=self.theme_colors['text_bg'],
            foreground=self.theme_colors['text_fg'],
            insertbackground=self.theme_colors['text_fg']
        )
        
        # 重新配置文本标签颜色
        self.text_display.tag_config("timestamp", foreground=self.theme_colors['timestamp'])
        self.text_display.tag_config("default", foreground=self.theme_colors['default'])
        self.text_display.tag_config("error", foreground=self.theme_colors['error'])
        self.text_display.tag_config("warning", foreground=self.theme_colors['warning'])
        self.text_display.tag_config("success", foreground=self.theme_colors['success'])
        
        # 更新端口颜色
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
        
        # 更新统计显示区域
        self.stats_display.config(
            background=self.theme_colors['stats_bg'],
            foreground=self.theme_colors['stats_fg']
        )
        
        # 重新配置统计标签（如果已配置）
        if self._stats_tags_configured:
            self.stats_display.tag_config("port_name", foreground=self.theme_colors['stats_port'])
            self.stats_display.tag_config("bytes", foreground=self.theme_colors['stats_bytes'])
            self.stats_display.tag_config("separator", foreground=self.theme_colors['stats_separator'])
        
        # 更新Listbox颜色
        self.active_list.config(
            background=self.theme_colors['text_bg'],
            foreground=self.theme_colors['text_fg'],
            selectbackground=self.theme_colors['stats_bg'],
            selectforeground=self.theme_colors['text_fg']
        )
        
        # 强制刷新显示
        self.root.update_idletasks()
    
    def _init_color_tags(self):
        """初始化颜色标签映射"""
        # 从主题配色中获取端口颜色
        self.color_map = self.theme_colors['port_colors']
    
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
    
    def _is_garbled_text(self, text: str) -> bool:
        """检测文本是否为乱码
        
        检测规则：
        1. 包含过多的控制字符或不可打印字符
        2. 包含过多的替换字符（�）
        3. 编码检测失败
        """
        if not text:
            return False
        
        # 计算不可打印字符的比例
        printable_chars = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
        total_chars = len(text)
        
        # 如果不可打印字符超过30%，认为是乱码
        if total_chars > 0 and (printable_chars / total_chars) < 0.7:
            return True
        
        # 检查是否包含过多的替换字符（�）
        replacement_count = text.count('�')
        if replacement_count > 0 and (replacement_count / total_chars) > 0.1:
            return True
        
        # 检查是否包含过多的连续控制字符
        control_char_count = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
        if control_char_count > 0 and (control_char_count / total_chars) > 0.3:
            return True
        
        return False
    
    def _display_data(self, port, timestamp, data):
        """显示接收到的数据（使用缓冲区批量处理）"""
        # 检测并过滤乱码
        if self._is_garbled_text(data):
            # 乱码数据不显示，只记录到日志
            return
        
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
        """批量处理显示缓冲区（激进策略：只要有数据就显示）"""
        try:
            with self.buffer_lock:
                buffer_size = len(self.display_buffer)
                
                if buffer_size == 0:
                    # 缓冲区为空，快速轮询
                    self.root.after(self.update_interval, self._process_display_buffer)
                    return
                
                # 激进策略：只要有数据就全部显示，除非数据量特别大才分批
                if buffer_size >= self.batch_threshold:
                    # 数据量大：分批处理防止UI卡顿
                    batch = self.display_buffer[:self.batch_threshold]
                    self.display_buffer = self.display_buffer[self.batch_threshold:]
                else:
                    # 所有其他情况：立即全部显示
                    batch = self.display_buffer[:buffer_size]
                    self.display_buffer = []
            
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
        
        # 继续快速循环
        self.root.after(self.update_interval, self._process_display_buffer)
    
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
    
    def _save_preset_data(self):
        """保存当前数据为预设"""
        data = self.send_data_var.get().strip()
        
        if not data:
            messagebox.showwarning("警告", "请输入要保存的数据")
            return
        
        # 弹出对话框让用户输入预设名称
        from tkinter import simpledialog
        name = simpledialog.askstring("保存预设", "请输入预设名称:", parent=self.root)
        
        if not name:
            return
        
        name = name.strip()
        if not name:
            messagebox.showwarning("警告", "预设名称不能为空")
            return
        
        # 检查是否已存在同名预设
        for preset in self.preset_data_list:
            if preset['name'] == name:
                result = messagebox.askyesno("确认", f"预设 '{name}' 已存在，是否覆盖？")
                if result:
                    preset['data'] = data
                    self._save_preset_data_to_file()
                    self._update_preset_combo()
                    self.status_var.set(f"已更新预设: {name}")
                return
        
        # 添加新预设
        self.preset_data_list.append({
            'name': name,
            'data': data
        })
        self._save_preset_data_to_file()
        self._update_preset_combo()
        self.status_var.set(f"已保存预设: {name}")
    
    def _delete_preset_data(self):
        """删除选中的预设"""
        name = self.preset_var.get()
        
        if not name:
            messagebox.showwarning("警告", "请选择要删除的预设")
            return
        
        result = messagebox.askyesno("确认", f"确定要删除预设 '{name}' 吗？")
        if not result:
            return
        
        # 删除预设
        self.preset_data_list = [p for p in self.preset_data_list if p['name'] != name]
        self._save_preset_data_to_file()
        self._update_preset_combo()
        self.preset_var.set("")
        self.status_var.set(f"已删除预设: {name}")
    
    def _on_preset_selected(self, event):
        """预设被选中时的回调"""
        name = self.preset_var.get()
        
        if not name:
            return
        
        # 查找对应的预设数据
        for preset in self.preset_data_list:
            if preset['name'] == name:
                self.send_data_var.set(preset['data'])
                self.status_var.set(f"已加载预设: {name}")
                return
    
    def _update_preset_combo(self):
        """更新预设下拉列表"""
        names = [p['name'] for p in self.preset_data_list]
        self.preset_combo['values'] = names
    
    def _save_preset_data_to_file(self):
        """保存预设数据到统一配置文件"""
        self._save_config()
    
    def _add_to_batch(self):
        """将当前活动串口配置添加到批量配置列表"""
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("警告", "请选择串口")
            return
        
        # 优先使用活动串口的实际配置
        active_ports = self.monitor.get_active_ports()
        if port in active_ports and port in self.port_configs:
            # 使用活动串口的实际运行配置
            active_config = self.port_configs[port]
            baudrate = active_config.get('baudrate', 9600)
            keywords = active_config.get('keywords', [])
            regex_patterns = active_config.get('regex', [])
            config_source = "活动配置"
        else:
            # 串口未运行，使用UI输入的配置
            try:
                baudrate = int(self.baudrate_var.get())
            except ValueError:
                messagebox.showerror("错误", "波特率必须是数字")
                return
            
            keywords, regex_patterns = self._get_filter_config()
            config_source = "UI配置"
        
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
        self.status_var.set(f"已添加 {port} ({config_source}) 到批量配置 (共{len(self.batch_port_configs)}个)")
    
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
            msg = f"批量启动完成: 成功{success_count}个，失败{len(failed_ports)}个 | 失败串口: {', '.join(failed_ports)}"
            self.status_var.set(msg)
        else:
            self.status_var.set(f"批量启动成功: 已启动{success_count}个串口")
    
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
        """保存配置到统一配置文件"""
        config = {
            'default_settings': {
                'baudrate': self.baudrate_var.get(),
                'keywords': self.keywords_var.get(),
                'regex': self.regex_var.get(),
                'send_data': self.send_data_var.get()
            },
            'theme': {
                'is_dark': self.is_dark_theme
            },
            'preset_data': self.preset_data_list,
            'batch_configs': self.batch_port_configs
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _save_batch_configs(self):
        """保存批量配置到统一配置文件"""
        self._save_config()
    
    def _load_config(self):
        """从统一配置文件加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 加载默认设置
                default_settings = config.get('default_settings', {})
                if 'baudrate' in default_settings:
                    self.baudrate_var.set(default_settings['baudrate'])
                if 'keywords' in default_settings:
                    self.keywords_var.set(default_settings['keywords'])
                if 'regex' in default_settings:
                    self.regex_var.set(default_settings['regex'])
                if 'send_data' in default_settings:
                    self.send_data_var.set(default_settings['send_data'])
                
                # 加载主题设置
                theme_settings = config.get('theme', {})
                if 'is_dark' in theme_settings:
                    self.is_dark_theme = theme_settings['is_dark']
                    # 更新主题按钮文本
                    if hasattr(self, 'theme_button'):
                        if self.is_dark_theme:
                            self.theme_button.config(text="☀️ 浅色模式")
                        else:
                            self.theme_button.config(text="🌙 深色模式")
                
                # 加载预设数据
                self.preset_data_list = config.get('preset_data', [])
                self._update_preset_combo()
                
                # 加载批量配置
                self.batch_port_configs = config.get('batch_configs', [])
                
                # 更新状态栏
                status_parts = ["已加载配置"]
                if self.batch_port_configs:
                    status_parts.append(f"{len(self.batch_port_configs)}个批量串口")
                if self.preset_data_list:
                    status_parts.append(f"{len(self.preset_data_list)}个预设")
                self.status_var.set(" | ".join(status_parts))
                    
            except Exception as e:
                print(f"加载配置失败: {e}")
                self.status_var.set("配置加载失败")
    
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
                self.stats_display.tag_config("port_name", foreground=self.theme_colors['stats_port'], font=("Microsoft YaHei UI", 9, "bold"))
                self.stats_display.tag_config("bytes", foreground=self.theme_colors['stats_bytes'], font=("Microsoft YaHei UI", 9, "bold"))
                self.stats_display.tag_config("separator", foreground=self.theme_colors['stats_separator'])
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
    
    def _open_log_filter(self):
        """打开日志过滤工具"""
        try:
            # 传递应用的日志目录到日志过滤窗口
            LogFilterWindow(self.root, log_dir=self.monitor.log_dir)
            self.status_var.set("已打开日志过滤工具")
        except ImportError as e:
            messagebox.showerror("错误", f"无法导入日志过滤模块: {str(e)}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("错误", f"无法打开日志过滤工具: {str(e)}\n\n详细信息:\n{error_details}")
    
    def _open_visualizer(self):
        """打开数据可视化工具"""
        try:
            from data_visualizer import DataVisualizer
            visualizer = DataVisualizer(self.root, self.monitor)
            visualizer.open_visualizer_window()
            self.status_var.set("已打开数据可视化工具")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开数据可视化工具: {str(e)}")
    
    def _open_analyzer(self):
        """打开数据分析工具"""
        try:
            from data_analyzer import DataAnalyzerWindow
            analyzer = DataAnalyzerWindow(self.root)
            analyzer.open_analyzer_window()
            self.status_var.set("已打开数据分析工具")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开数据分析工具: {str(e)}")
    
    def _open_recorder(self):
        """打开录制回放工具"""
        try:
            from recorder_player import RecorderPlayerWindow
            recorder = RecorderPlayerWindow(self.root, self.monitor)
            recorder.open_window()
            self.status_var.set("已打开录制回放工具")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开录制回放工具: {str(e)}")
    
    def _open_automation(self):
        """打开自动化测试工具"""
        try:
            from automation_tester import AutomationTesterWindow
            automation = AutomationTesterWindow(self.root, self.monitor)
            automation.open_window()
            self.status_var.set("已打开自动化测试工具")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开自动化测试工具: {str(e)}")
    
    def _open_utilities(self):
        """打开实用工具箱"""
        try:
            from utility_tools import UtilityToolsWindow
            utilities = UtilityToolsWindow(self.root)
            utilities.open_window()
            self.status_var.set("已打开实用工具箱")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开实用工具箱: {str(e)}")
    
    def _change_current_baudrate(self):
        """修改当前选中串口的波特率"""
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("警告", "请选择要修改波特率的串口")
            return
        
        # 检查串口是否在运行
        active_ports = self.monitor.get_active_ports()
        if port not in active_ports:
            messagebox.showwarning("警告", f"串口 {port} 未在监控中，无法修改波特率")
            return
        
        try:
            new_baudrate = int(self.baudrate_var.get())
        except ValueError:
            messagebox.showerror("错误", "波特率必须是数字")
            return
        
        # 获取当前波特率
        current_baudrate = self.port_configs.get(port, {}).get('baudrate', 'N/A')
        
        # 确认对话框
        result = messagebox.askyesno(
            "确认修改波特率",
            f"确定要将串口 {port} 的波特率\n从 {current_baudrate} 修改为 {new_baudrate} 吗？\n\n此操作不会中断串口连接"
        )
        
        if not result:
            return
        
        # 执行修改
        if self.monitor.change_baudrate(port, new_baudrate):
            # 更新本地配置
            if port in self.port_configs:
                self.port_configs[port]['baudrate'] = new_baudrate
            
            # 更新活动串口列表显示
            self._update_active_list()
            
            messagebox.showinfo("成功", f"串口 {port} 的波特率已成功修改为 {new_baudrate}")
            self.status_var.set(f"已修改 {port} 波特率: {current_baudrate} → {new_baudrate}")
        else:
            messagebox.showerror("失败", f"修改串口 {port} 的波特率失败")
    
    def _change_all_baudrates(self):
        """修改所有活动串口的波特率"""
        active_ports = self.monitor.get_active_ports()
        
        if not active_ports:
            messagebox.showwarning("警告", "当前没有活动的串口监控")
            return
        
        try:
            new_baudrate = int(self.baudrate_var.get())
        except ValueError:
            messagebox.showerror("错误", "波特率必须是数字")
            return
        
        # 确认对话框
        port_list = '\n'.join([f"  • {port} ({self.port_configs.get(port, {}).get('baudrate', 'N/A')} bps)" for port in active_ports])
        result = messagebox.askyesno(
            "确认批量修改波特率",
            f"确定要将以下 {len(active_ports)} 个串口的波特率\n全部修改为 {new_baudrate} 吗？\n\n{port_list}\n\n此操作不会中断串口连接"
        )
        
        if not result:
            return
        
        # 执行批量修改
        results = self.monitor.change_all_baudrates(new_baudrate)
        
        # 统计结果
        success_count = sum(1 for success in results.values() if success)
        failed_ports = [port for port, success in results.items() if not success]
        
        # 更新本地配置
        for port, success in results.items():
            if success and port in self.port_configs:
                self.port_configs[port]['baudrate'] = new_baudrate
        
        # 更新活动串口列表显示
        self._update_active_list()
        
        # 显示结果
        if failed_ports:
            msg = f"批量修改完成:\n成功: {success_count} 个\n失败: {len(failed_ports)} 个\n\n失败串口: {', '.join(failed_ports)}"
            messagebox.showwarning("部分成功", msg)
            self.status_var.set(f"批量修改波特率: 成功{success_count}个, 失败{len(failed_ports)}个")
        else:
            messagebox.showinfo("成功", f"已成功将所有 {success_count} 个串口的波特率修改为 {new_baudrate}")
            self.status_var.set(f"已批量修改 {success_count} 个串口的波特率为 {new_baudrate}")
    
    def close(self):
        """关闭应用，确保资源正确清理"""
        try:
            # 保存配置
            self._save_config()
        except Exception as e:
            print(f"保存配置时出错: {e}")
        
        try:
            # 停止所有串口监控
            self.monitor.stop_all()
        except Exception as e:
            print(f"停止串口监控时出错: {e}")
        
        try:
            # 销毁窗口
            self.root.destroy()
        except Exception as e:
            print(f"关闭窗口时出错: {e}")


def main():
    root = tk.Tk()
    app = SerialToolGUI(root)
    
    def on_closing():
        app.close()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()