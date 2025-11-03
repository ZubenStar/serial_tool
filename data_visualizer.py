"""
数据可视化模块
支持实时数据流量图表、统计图表等
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, List
import threading
import time
from collections import deque
from datetime import datetime


class DataVisualizer:
    """数据可视化管理器"""
    
    def __init__(self, parent_window, monitor):
        self.parent = parent_window
        self.monitor = monitor
        self.viz_window = None
        
        # 数据存储
        self.bandwidth_data = {}  # {port: deque([timestamp, bytes], maxlen=100)}
        self.keyword_stats = {}  # {port: {keyword: count}}
        self.data_lock = threading.Lock()
        
        # 更新控制
        self.is_running = False
        self.update_interval = 1000  # 1秒更新一次
        
    def open_visualizer_window(self):
        """打开可视化窗口"""
        if self.viz_window and tk.Toplevel.winfo_exists(self.viz_window):
            self.viz_window.lift()
            return
        
        self.viz_window = tk.Toplevel(self.parent)
        self.viz_window.title("数据可视化")
        self.viz_window.geometry("900x600")
        
        # 创建标签页
        notebook = ttk.Notebook(self.viz_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 带宽监控标签页
        bandwidth_frame = ttk.Frame(notebook)
        notebook.add(bandwidth_frame, text="📊 带宽监控")
        self._create_bandwidth_view(bandwidth_frame)
        
        # 关键词统计标签页
        keyword_frame = ttk.Frame(notebook)
        notebook.add(keyword_frame, text="📈 关键词统计")
        self._create_keyword_stats_view(keyword_frame)
        
        # 数据流量标签页
        traffic_frame = ttk.Frame(notebook)
        notebook.add(traffic_frame, text="🌊 数据流量")
        self._create_traffic_view(traffic_frame)
        
        # 启动数据更新
        self.is_running = True
        self._start_data_collection()
        
        # 窗口关闭处理
        self.viz_window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_bandwidth_view(self, parent):
        """创建带宽监控视图"""
        # 控制面板
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="实时带宽监控", font=("TkDefaultFont", 12, "bold")).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="刷新", command=self._refresh_bandwidth).pack(side=tk.RIGHT, padx=5)
        
        # Canvas绘图区域
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.bandwidth_canvas = tk.Canvas(canvas_frame, bg="white")
        self.bandwidth_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.bandwidth_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bandwidth_canvas.config(yscrollcommand=scrollbar.set)
        
        # 统计信息显示
        stats_frame = ttk.LabelFrame(parent, text="统计信息", padding=5)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.bandwidth_stats_label = ttk.Label(stats_frame, text="等待数据...")
        self.bandwidth_stats_label.pack(fill=tk.X)
    
    def _create_keyword_stats_view(self, parent):
        """创建关键词统计视图"""
        # 控制面板
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="关键词匹配统计", font=("TkDefaultFont", 12, "bold")).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="重置统计", command=self._reset_keyword_stats).pack(side=tk.RIGHT, padx=5)
        
        # 表格显示
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建Treeview
        columns = ("串口", "关键词", "匹配次数", "占比")
        self.keyword_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.keyword_tree.heading(col, text=col)
            self.keyword_tree.column(col, width=120)
        
        self.keyword_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.keyword_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.keyword_tree.config(yscrollcommand=scrollbar.set)
        
        # 图表显示区域
        chart_frame = ttk.LabelFrame(parent, text="可视化图表", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.keyword_chart_canvas = tk.Canvas(chart_frame, bg="white", height=200)
        self.keyword_chart_canvas.pack(fill=tk.BOTH, expand=True)
    
    def _create_traffic_view(self, parent):
        """创建数据流量视图"""
        # 控制面板
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="数据流量趋势", font=("TkDefaultFont", 12, "bold")).pack(side=tk.LEFT)
        
        # 时间范围选择
        ttk.Label(control_frame, text="时间范围:").pack(side=tk.LEFT, padx=(20, 5))
        self.time_range_var = tk.StringVar(value="1分钟")
        time_range_combo = ttk.Combobox(control_frame, textvariable=self.time_range_var, 
                                        values=["30秒", "1分钟", "5分钟", "10分钟"], 
                                        state="readonly", width=10)
        time_range_combo.pack(side=tk.LEFT, padx=5)
        
        # 流量图表
        chart_frame = ttk.LabelFrame(parent, text="流量曲线", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.traffic_canvas = tk.Canvas(chart_frame, bg="white")
        self.traffic_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 详细统计
        detail_frame = ttk.LabelFrame(parent, text="详细统计", padding=5)
        detail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.traffic_detail_text = tk.Text(detail_frame, height=5, wrap=tk.WORD, state=tk.DISABLED)
        self.traffic_detail_text.pack(fill=tk.X)
    
    def _start_data_collection(self):
        """启动数据收集"""
        if not self.is_running:
            return
        
        # 收集当前数据
        all_stats = self.monitor.get_all_stats()
        current_time = time.time()
        
        with self.data_lock:
            for port, stats in all_stats.items():
                if port not in self.bandwidth_data:
                    self.bandwidth_data[port] = deque(maxlen=100)
                
                bytes_count = stats.get('total_bytes', 0)
                self.bandwidth_data[port].append((current_time, bytes_count))
        
        # 更新显示
        self._update_bandwidth_display()
        self._update_keyword_display()
        self._update_traffic_display()
        
        # 继续收集
        if self.viz_window and tk.Toplevel.winfo_exists(self.viz_window):
            self.viz_window.after(self.update_interval, self._start_data_collection)
    
    def _update_bandwidth_display(self):
        """更新带宽显示"""
        try:
            self.bandwidth_canvas.delete("all")
            
            with self.data_lock:
                if not self.bandwidth_data:
                    self.bandwidth_canvas.create_text(
                        400, 200, text="无活动串口", 
                        font=("TkDefaultFont", 14), fill="gray"
                    )
                    return
                
                # 绘制每个端口的带宽条
                canvas_width = self.bandwidth_canvas.winfo_width() or 800
                canvas_height = self.bandwidth_canvas.winfo_height() or 400
                
                y_offset = 20
                bar_height = 40
                colors = ['#4285F4', '#34A853', '#FBBC04', '#EA4335', '#9C27B0', '#00BCD4']
                
                # 计算最大带宽用于缩放
                max_bandwidth = 1
                for port, data in self.bandwidth_data.items():
                    if len(data) >= 2:
                        recent_bytes = data[-1][1] - data[0][1]
                        time_span = data[-1][0] - data[0][0]
                        if time_span > 0:
                            bandwidth = recent_bytes / time_span  # bytes/s
                            max_bandwidth = max(max_bandwidth, bandwidth)
                
                stats_text = []
                for idx, (port, data) in enumerate(self.bandwidth_data.items()):
                    color = colors[idx % len(colors)]
                    
                    # 计算带宽
                    if len(data) >= 2:
                        recent_bytes = data[-1][1] - data[0][1]
                        time_span = data[-1][0] - data[0][0]
                        bandwidth = recent_bytes / time_span if time_span > 0 else 0
                    else:
                        bandwidth = 0
                    
                    # 绘制标签
                    self.bandwidth_canvas.create_text(
                        10, y_offset + bar_height // 2,
                        text=f"{port}:", anchor=tk.W,
                        font=("TkDefaultFont", 10, "bold")
                    )
                    
                    # 绘制带宽条
                    bar_width = (bandwidth / max_bandwidth) * (canvas_width - 200) if max_bandwidth > 0 else 0
                    self.bandwidth_canvas.create_rectangle(
                        100, y_offset, 100 + bar_width, y_offset + bar_height,
                        fill=color, outline=color
                    )
                    
                    # 显示数值
                    bandwidth_text = self._format_bandwidth(bandwidth)
                    self.bandwidth_canvas.create_text(
                        110 + bar_width, y_offset + bar_height // 2,
                        text=bandwidth_text, anchor=tk.W,
                        font=("TkDefaultFont", 9)
                    )
                    
                    stats_text.append(f"{port}: {bandwidth_text}")
                    y_offset += bar_height + 10
                
                # 更新统计信息
                self.bandwidth_stats_label.config(text=" | ".join(stats_text))
                
        except Exception as e:
            print(f"更新带宽显示错误: {e}")
    
    def _update_keyword_display(self):
        """更新关键词统计显示"""
        try:
            # 清空表格
            for item in self.keyword_tree.get_children():
                self.keyword_tree.delete(item)
            
            # TODO: 实现关键词统计逻辑
            # 这需要在串口监控中记录关键词匹配次数
            
        except Exception as e:
            print(f"更新关键词显示错误: {e}")
    
    def _update_traffic_display(self):
        """更新流量趋势显示"""
        try:
            self.traffic_canvas.delete("all")
            
            with self.data_lock:
                if not self.bandwidth_data:
                    return
                
                canvas_width = self.traffic_canvas.winfo_width() or 800
                canvas_height = self.traffic_canvas.winfo_height() or 400
                
                # 绘制坐标轴
                margin = 50
                chart_width = canvas_width - 2 * margin
                chart_height = canvas_height - 2 * margin
                
                # Y轴
                self.traffic_canvas.create_line(
                    margin, margin, margin, canvas_height - margin,
                    arrow=tk.FIRST
                )
                
                # X轴
                self.traffic_canvas.create_line(
                    margin, canvas_height - margin,
                    canvas_width - margin, canvas_height - margin,
                    arrow=tk.LAST
                )
                
                # 绘制标签
                self.traffic_canvas.create_text(
                    margin // 2, margin // 2,
                    text="字节/秒", angle=90
                )
                self.traffic_canvas.create_text(
                    canvas_width - margin // 2, canvas_height - margin // 2,
                    text="时间"
                )
                
                # 绘制数据线
                colors = ['#4285F4', '#34A853', '#FBBC04', '#EA4335']
                for idx, (port, data) in enumerate(self.bandwidth_data.items()):
                    if len(data) < 2:
                        continue
                    
                    color = colors[idx % len(colors)]
                    points = []
                    
                    # 计算点的坐标
                    min_time = data[0][0]
                    max_time = data[-1][0]
                    time_range = max_time - min_time if max_time > min_time else 1
                    
                    max_bytes = max(d[1] for d in data)
                    
                    for timestamp, bytes_val in data:
                        x = margin + ((timestamp - min_time) / time_range) * chart_width
                        y = canvas_height - margin - (bytes_val / max_bytes) * chart_height if max_bytes > 0 else canvas_height - margin
                        points.extend([x, y])
                    
                    # 绘制线条
                    if len(points) >= 4:
                        self.traffic_canvas.create_line(
                            *points, fill=color, width=2, smooth=True
                        )
                        
                        # 添加图例
                        legend_y = margin + idx * 20
                        self.traffic_canvas.create_line(
                            canvas_width - margin - 100, legend_y,
                            canvas_width - margin - 80, legend_y,
                            fill=color, width=2
                        )
                        self.traffic_canvas.create_text(
                            canvas_width - margin - 75, legend_y,
                            text=port, anchor=tk.W
                        )
                
        except Exception as e:
            print(f"更新流量显示错误: {e}")
    
    def _format_bandwidth(self, bytes_per_sec: float) -> str:
        """格式化带宽显示"""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.1f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    
    def _refresh_bandwidth(self):
        """刷新带宽显示"""
        self._update_bandwidth_display()
    
    def _reset_keyword_stats(self):
        """重置关键词统计"""
        with self.data_lock:
            self.keyword_stats.clear()
        self._update_keyword_display()
    
    def _on_close(self):
        """窗口关闭处理"""
        self.is_running = False
        if self.viz_window:
            self.viz_window.destroy()
            self.viz_window = None