import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from serial_monitor import MultiSerialMonitor
from typing import Dict


class SerialToolGUI:
    """串口工具图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("多串口监控工具")
        self.root.geometry("1200x800")
        
        self.monitor = MultiSerialMonitor(log_dir="logs")
        self.port_configs: Dict[str, Dict] = {}
        
        self._create_widgets()
        self._update_available_ports()
        
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
        
        # 第二行：关键词过滤
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="关键词 (逗号分隔):").pack(side=tk.LEFT, padx=5)
        self.keywords_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.keywords_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 第三行：正则表达式
        row3 = ttk.Frame(control_frame)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Label(row3, text="正则表达式 (逗号分隔):").pack(side=tk.LEFT, padx=5)
        self.regex_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.regex_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
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
        
        ttk.Button(send_row, text="发送", command=self._send_data).pack(side=tk.LEFT, padx=5)
        
        # 数据显示区域
        display_frame = ttk.LabelFrame(self.root, text="数据显示", padding=10)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.text_display = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, height=20)
        self.text_display.pack(fill=tk.BOTH, expand=True)
        
        # 配置颜色标签
        self.text_display.tag_config("COM1", foreground="blue")
        self.text_display.tag_config("COM2", foreground="green")
        self.text_display.tag_config("COM3", foreground="red")
        self.text_display.tag_config("COM4", foreground="purple")
        self.text_display.tag_config("default", foreground="black")
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
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
        
        def callback(port, timestamp, data):
            self._display_data(port, timestamp, data)
        
        if self.monitor.add_monitor(port, baudrate, keywords, regex_patterns, callback):
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
        """显示接收到的数据"""
        def update_ui():
            # 根据串口名称选择颜色标签
            tag = port if port in ["COM1", "COM2", "COM3", "COM4"] else "default"
            
            self.text_display.insert(tk.END, f"[{timestamp}] [{port}] {data}\n", tag)
            self.text_display.see(tk.END)
            
            # 限制显示行数
            lines = int(self.text_display.index('end-1c').split('.')[0])
            if lines > 1000:
                self.text_display.delete('1.0', '100.0')
        
        self.root.after(0, update_ui)
    
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
    
    def close(self):
        """关闭应用"""
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