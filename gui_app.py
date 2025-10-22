import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
import time
from serial_monitor import MultiSerialMonitor, Colors
from typing import Dict


class SerialToolGUI:
    """串口工具图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("多串口监控工具")
        self.root.geometry("1200x800")
        
        self.monitor = MultiSerialMonitor(log_dir="logs")
        self.port_configs: Dict[str, Dict] = {}
        self.config_file = "serial_tool_config.json"
        
        # 性能优化：批量更新缓冲区
        self.display_buffer = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 100  # 批量处理的最大条目数
        self.update_interval = 100  # UI更新间隔(毫秒)
        self.max_display_lines = 1000  # 最大显示行数
        self.trim_to_lines = 800  # 超过最大行数时保留的行数
        self.last_trim_time = 0  # 上次清理时间
        self.trim_interval = 5.0  # 清理间隔(秒)
        
        self._create_widgets()
        self._update_available_ports()
        self._load_config()
        self._start_ui_update_loop()
        
    def _create_widgets(self):
        """创建界面组件"""
        # 控制面板
        control_frame = ttk.LabelFrame(self.root, text="串口控制", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 第一行：串口选择和波特率
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="串口:").pack(side=tk.LEFT, padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(row1, textvariable=self.port_var, width=15)
        self.port_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row1, text="刷新", command=self._update_available_ports).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="波特率:").pack(side=tk.LEFT, padx=5)
        self.baudrate_var = tk.StringVar(value="9600")
        baudrate_combo = ttk.Combobox(row1, textvariable=self.baudrate_var, width=10,
                                      values=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600", "3000000"])
        baudrate_combo.pack(side=tk.LEFT, padx=5)
        self.baudrate_var.trace_add('write', self._on_config_change)
        
        # 第二行：关键词过滤
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="关键词 (逗号分隔):").pack(side=tk.LEFT, padx=5)
        self.keywords_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.keywords_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.keywords_var.trace_add('write', self._on_config_change)
        
        # 第三行：正则表达式
        row3 = ttk.Frame(control_frame)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Label(row3, text="正则表达式 (逗号分隔):").pack(side=tk.LEFT, padx=5)
        self.regex_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.regex_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.regex_var.trace_add('write', self._on_config_change)
        
        # 第四行：按钮
        row4 = ttk.Frame(control_frame)
        row4.pack(fill=tk.X, pady=2)
        
        ttk.Button(row4, text="启动监控", command=self._start_monitor).pack(side=tk.LEFT, padx=5)
        ttk.Button(row4, text="停止监控", command=self._stop_monitor).pack(side=tk.LEFT, padx=5)
        ttk.Button(row4, text="停止所有", command=self._stop_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(row4, text="清除显示", command=self._clear_display).pack(side=tk.LEFT, padx=5)
        
        # 活动串口列表
        active_frame = ttk.LabelFrame(self.root, text="活动串口", padding=10)
        active_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.active_list = tk.Listbox(active_frame, height=3)
        self.active_list.pack(fill=tk.BOTH, expand=True)
        
        # 发送数据面板
        send_frame = ttk.LabelFrame(self.root, text="发送数据", padding=10)
        send_frame.pack(fill=tk.X, padx=10, pady=5)
        
        send_row = ttk.Frame(send_frame)
        send_row.pack(fill=tk.X)
        
        ttk.Label(send_row, text="目标串口:").pack(side=tk.LEFT, padx=5)
        self.send_port_var = tk.StringVar()
        self.send_port_combo = ttk.Combobox(send_row, textvariable=self.send_port_var, width=15)
        self.send_port_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(send_row, text="数据:").pack(side=tk.LEFT, padx=5)
        self.send_data_var = tk.StringVar()
        ttk.Entry(send_row, textvariable=self.send_data_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.send_data_var.trace_add('write', self._on_config_change)
        
        ttk.Button(send_row, text="发送", command=self._send_data).pack(side=tk.LEFT, padx=5)
        
        # 数据显示区域
        display_frame = ttk.LabelFrame(self.root, text="数据显示", padding=10)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.text_display = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, height=20)
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
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
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
        """更新可用串口列表"""
        ports = MultiSerialMonitor.list_available_ports()
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
        self.status_var.set(f"找到 {len(ports)} 个可用串口")
        
    def _get_filter_config(self):
        """获取过滤配置"""
        keywords = [k.strip() for k in self.keywords_var.get().split(',') if k.strip()]
        regex_patterns = [r.strip() for r in self.regex_var.get().split(',') if r.strip()]
        return keywords, regex_patterns
    
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
        """批量处理显示缓冲区"""
        try:
            with self.buffer_lock:
                if not self.display_buffer:
                    # 缓冲区为空，继续循环
                    self.root.after(self.update_interval, self._process_display_buffer)
                    return
                
                # 取出所有待显示的数据（最多max_buffer_size条）
                batch = self.display_buffer[:self.max_buffer_size]
                self.display_buffer = self.display_buffer[self.max_buffer_size:]
            
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
            
            # 滚动到底部
            self.text_display.see(tk.END)
            
            # 定期清理超出的行数（避免每次都检查）
            current_time = time.time()
            if current_time - self.last_trim_time > self.trim_interval:
                self._trim_display_lines()
                self.last_trim_time = current_time
            
        except Exception as e:
            print(f"处理显示缓冲区错误: {e}")
        
        # 继续循环
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
    
    def _load_config(self):
        """从文件加载配置"""
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