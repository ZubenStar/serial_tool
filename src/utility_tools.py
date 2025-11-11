"""
实用工具模块
包含波特率计算器、校验和计算器、进制转换器等实用工具
"""
import tkinter as tk
from tkinter import ttk, messagebox
import re


class UtilityToolsWindow:
    """实用工具窗口"""
    
    def __init__(self, parent):
        self.parent = parent
        self.window = None
    
    def open_window(self):
        """打开实用工具窗口"""
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("实用工具箱")
        self.window.geometry("700x600")
        
        # 创建标签页
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 波特率计算器
        baudrate_frame = ttk.Frame(notebook)
        notebook.add(baudrate_frame, text="⚙️ 波特率计算器")
        self._create_baudrate_calculator(baudrate_frame)
        
        # 进制转换器
        converter_frame = ttk.Frame(notebook)
        notebook.add(converter_frame, text="🔢 进制转换器")
        self._create_number_converter(converter_frame)
        
        # 数据生成器
        generator_frame = ttk.Frame(notebook)
        notebook.add(generator_frame, text="📝 数据生成器")
        self._create_data_generator(generator_frame)
        
        # 时间工具
        timer_frame = ttk.Frame(notebook)
        notebook.add(timer_frame, text="⏱️ 定时器")
        self._create_timer_tool(timer_frame)
    
    def _create_baudrate_calculator(self, parent):
        """创建波特率计算器"""
        info_label = ttk.Label(parent, text="波特率计算器 - 计算串口通信参数", 
                               font=("TkDefaultFont", 11, "bold"))
        info_label.pack(pady=10)
        
        # 输入区
        input_frame = ttk.LabelFrame(parent, text="输入参数", padding=15)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 时钟频率
        clock_frame = ttk.Frame(input_frame)
        clock_frame.pack(fill=tk.X, pady=5)
        ttk.Label(clock_frame, text="时钟频率 (Hz):").pack(side=tk.LEFT)
        self.clock_freq_var = tk.StringVar(value="16000000")
        ttk.Entry(clock_frame, textvariable=self.clock_freq_var, width=15).pack(side=tk.LEFT, padx=5)
        
        # 目标波特率
        baud_frame = ttk.Frame(input_frame)
        baud_frame.pack(fill=tk.X, pady=5)
        ttk.Label(baud_frame, text="目标波特率:").pack(side=tk.LEFT)
        self.target_baud_var = tk.StringVar(value="9600")
        ttk.Combobox(baud_frame, textvariable=self.target_baud_var,
                    values=["300", "1200", "2400", "4800", "9600", "19200", "38400", 
                           "57600", "115200", "230400", "460800", "921600"],
                    width=12).pack(side=tk.LEFT, padx=5)
        
        # 计算按钮
        ttk.Button(input_frame, text="计算", command=self._calculate_baudrate).pack(pady=10)
        
        # 结果区
        result_frame = ttk.LabelFrame(parent, text="计算结果", padding=15)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.baudrate_result = tk.Text(result_frame, height=15, wrap=tk.WORD)
        self.baudrate_result.pack(fill=tk.BOTH, expand=True)
    
    def _create_number_converter(self, parent):
        """创建进制转换器"""
        info_label = ttk.Label(parent, text="进制转换器 - HEX/DEC/BIN/ASCII互转", 
                               font=("TkDefaultFont", 11, "bold"))
        info_label.pack(pady=10)
        
        # 输入区
        input_frame = ttk.LabelFrame(parent, text="输入", padding=15)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 输入类型选择
        type_frame = ttk.Frame(input_frame)
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(type_frame, text="输入类型:").pack(side=tk.LEFT)
        self.input_type_var = tk.StringVar(value="HEX")
        for type_name in ["HEX", "DEC", "BIN", "ASCII"]:
            ttk.Radiobutton(type_frame, text=type_name, variable=self.input_type_var, 
                           value=type_name).pack(side=tk.LEFT, padx=5)
        
        # 输入框
        ttk.Label(input_frame, text="输入值:").pack(anchor=tk.W, pady=(5, 2))
        self.converter_input = tk.Text(input_frame, height=3, wrap=tk.WORD)
        self.converter_input.pack(fill=tk.X, pady=5)
        
        # 转换按钮
        ttk.Button(input_frame, text="转换", command=self._convert_number).pack(pady=5)
        
        # 结果区
        result_frame = ttk.LabelFrame(parent, text="转换结果", padding=15)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.converter_result = tk.Text(result_frame, height=10, wrap=tk.WORD)
        self.converter_result.pack(fill=tk.BOTH, expand=True)
    
    def _create_data_generator(self, parent):
        """创建数据生成器"""
        info_label = ttk.Label(parent, text="测试数据生成器", 
                               font=("TkDefaultFont", 11, "bold"))
        info_label.pack(pady=10)
        
        # 配置区
        config_frame = ttk.LabelFrame(parent, text="生成配置", padding=15)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 数据类型
        type_frame = ttk.Frame(config_frame)
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(type_frame, text="数据类型:").pack(side=tk.LEFT)
        self.gen_type_var = tk.StringVar(value="random")
        ttk.Radiobutton(type_frame, text="随机数据", variable=self.gen_type_var, 
                       value="random").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="递增序列", variable=self.gen_type_var, 
                       value="sequence").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="固定模式", variable=self.gen_type_var, 
                       value="pattern").pack(side=tk.LEFT, padx=5)
        
        # 数量和长度
        param_frame = ttk.Frame(config_frame)
        param_frame.pack(fill=tk.X, pady=5)
        ttk.Label(param_frame, text="生成数量:").pack(side=tk.LEFT)
        self.gen_count_var = tk.StringVar(value="100")
        ttk.Entry(param_frame, textvariable=self.gen_count_var, width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(param_frame, text="数据长度:").pack(side=tk.LEFT, padx=(20, 0))
        self.gen_length_var = tk.StringVar(value="16")
        ttk.Entry(param_frame, textvariable=self.gen_length_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # 生成按钮
        ttk.Button(config_frame, text="生成数据", command=self._generate_data).pack(pady=10)
        
        # 结果区
        result_frame = ttk.LabelFrame(parent, text="生成的数据", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.generator_result = tk.Text(result_frame, height=12, wrap=tk.WORD)
        self.generator_result.pack(fill=tk.BOTH, expand=True)
        
        # 操作按钮
        btn_frame = ttk.Frame(result_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="复制", command=self._copy_generated_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="清除", command=lambda: self.generator_result.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=2)
    
    def _create_timer_tool(self, parent):
        """创建定时器工具"""
        info_label = ttk.Label(parent, text="精确定时器", 
                               font=("TkDefaultFont", 11, "bold"))
        info_label.pack(pady=10)
        
        # 秒表区
        stopwatch_frame = ttk.LabelFrame(parent, text="秒表", padding=15)
        stopwatch_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stopwatch_time_var = tk.StringVar(value="00:00:00.000")
        time_label = ttk.Label(stopwatch_frame, textvariable=self.stopwatch_time_var, 
                              font=("TkDefaultFont", 20, "bold"))
        time_label.pack(pady=10)
        
        btn_frame = ttk.Frame(stopwatch_frame)
        btn_frame.pack(fill=tk.X)
        
        self.stopwatch_start_btn = ttk.Button(btn_frame, text="开始", command=self._start_stopwatch)
        self.stopwatch_start_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.stopwatch_stop_btn = ttk.Button(btn_frame, text="停止", command=self._stop_stopwatch, state=tk.DISABLED)
        self.stopwatch_stop_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        ttk.Button(btn_frame, text="重置", command=self._reset_stopwatch).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # 倒计时区
        countdown_frame = ttk.LabelFrame(parent, text="倒计时", padding=15)
        countdown_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 时间设置
        time_set_frame = ttk.Frame(countdown_frame)
        time_set_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(time_set_frame, text="分钟:").pack(side=tk.LEFT)
        self.countdown_min_var = tk.StringVar(value="5")
        ttk.Entry(time_set_frame, textvariable=self.countdown_min_var, width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(time_set_frame, text="秒:").pack(side=tk.LEFT, padx=(10, 0))
        self.countdown_sec_var = tk.StringVar(value="0")
        ttk.Entry(time_set_frame, textvariable=self.countdown_sec_var, width=5).pack(side=tk.LEFT, padx=5)
        
        self.countdown_time_var = tk.StringVar(value="05:00")
        countdown_label = ttk.Label(countdown_frame, textvariable=self.countdown_time_var, 
                                    font=("TkDefaultFont", 18, "bold"))
        countdown_label.pack(pady=10)
        
        countdown_btn_frame = ttk.Frame(countdown_frame)
        countdown_btn_frame.pack(fill=tk.X)
        
        self.countdown_start_btn = ttk.Button(countdown_btn_frame, text="开始", 
                                             command=self._start_countdown)
        self.countdown_start_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.countdown_stop_btn = ttk.Button(countdown_btn_frame, text="停止", 
                                            command=self._stop_countdown, state=tk.DISABLED)
        self.countdown_stop_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # 定时器状态
        self.stopwatch_running = False
        self.stopwatch_start_time = 0
        self.stopwatch_elapsed = 0
        
        self.countdown_running = False
        self.countdown_remaining = 0
    
    def _calculate_baudrate(self):
        """计算波特率参数"""
        try:
            clock_freq = float(self.clock_freq_var.get())
            target_baud = float(self.target_baud_var.get())
            
            # UART波特率计算公式：BaudRate = ClockFreq / (16 * Divisor)
            divisor = clock_freq / (16 * target_baud)
            actual_baud = clock_freq / (16 * round(divisor))
            error_percent = abs((actual_baud - target_baud) / target_baud) * 100
            
            self.baudrate_result.delete("1.0", tk.END)
            self.baudrate_result.insert(tk.END, "波特率计算结果:\n")
            self.baudrate_result.insert(tk.END, "="*40 + "\n\n")
            self.baudrate_result.insert(tk.END, f"时钟频率: {clock_freq:,.0f} Hz\n")
            self.baudrate_result.insert(tk.END, f"目标波特率: {target_baud:,.0f} bps\n\n")
            self.baudrate_result.insert(tk.END, f"计算的分频器: {divisor:.2f}\n")
            self.baudrate_result.insert(tk.END, f"实际分频器: {round(divisor)}\n")
            self.baudrate_result.insert(tk.END, f"实际波特率: {actual_baud:,.2f} bps\n")
            self.baudrate_result.insert(tk.END, f"误差: {error_percent:.4f}%\n\n")
            
            if error_percent < 1:
                self.baudrate_result.insert(tk.END, "✓ 误差在可接受范围内\n", "success")
            elif error_percent < 3:
                self.baudrate_result.insert(tk.END, "⚠ 误差较大，可能影响通信\n", "warning")
            else:
                self.baudrate_result.insert(tk.END, "✗ 误差过大，建议调整时钟频率\n", "error")
            
            # 配置标签颜色
            self.baudrate_result.tag_config("success", foreground="green")
            self.baudrate_result.tag_config("warning", foreground="orange")
            self.baudrate_result.tag_config("error", foreground="red")
            
        except Exception as e:
            messagebox.showerror("错误", f"计算失败: {str(e)}")
    
    def _convert_number(self):
        """转换进制"""
        try:
            input_text = self.converter_input.get("1.0", tk.END).strip()
            input_type = self.input_type_var.get()
            
            self.converter_result.delete("1.0", tk.END)
            
            if input_type == "HEX":
                # 十六进制输入
                hex_str = input_text.replace(" ", "").replace("0x", "")
                value = int(hex_str, 16)
                
                self.converter_result.insert(tk.END, f"十六进制: 0x{hex_str.upper()}\n")
                self.converter_result.insert(tk.END, f"十进制: {value}\n")
                self.converter_result.insert(tk.END, f"二进制: {bin(value)}\n")
                
                # 尝试转换为ASCII
                try:
                    bytes_data = bytes.fromhex(hex_str)
                    ascii_str = bytes_data.decode('ascii', errors='replace')
                    self.converter_result.insert(tk.END, f"ASCII: {ascii_str}\n")
                except:
                    self.converter_result.insert(tk.END, "ASCII: (无法转换)\n")
            
            elif input_type == "DEC":
                # 十进制输入
                value = int(input_text)
                
                self.converter_result.insert(tk.END, f"十进制: {value}\n")
                self.converter_result.insert(tk.END, f"十六进制: 0x{value:X}\n")
                self.converter_result.insert(tk.END, f"二进制: {bin(value)}\n")
                self.converter_result.insert(tk.END, f"ASCII: {chr(value) if 0 <= value <= 127 else '(无效)'}\n")
            
            elif input_type == "BIN":
                # 二进制输入
                bin_str = input_text.replace(" ", "").replace("0b", "")
                value = int(bin_str, 2)
                
                self.converter_result.insert(tk.END, f"二进制: {bin_str}\n")
                self.converter_result.insert(tk.END, f"十进制: {value}\n")
                self.converter_result.insert(tk.END, f"十六进制: 0x{value:X}\n")
                self.converter_result.insert(tk.END, f"ASCII: {chr(value) if 0 <= value <= 127 else '(无效)'}\n")
            
            elif input_type == "ASCII":
                # ASCII输入
                ascii_str = input_text
                
                self.converter_result.insert(tk.END, f"ASCII: {ascii_str}\n")
                self.converter_result.insert(tk.END, f"十六进制: {ascii_str.encode().hex().upper()}\n")
                
                dec_values = [str(ord(c)) for c in ascii_str]
                self.converter_result.insert(tk.END, f"十进制: {' '.join(dec_values)}\n")
                
                bin_values = [bin(ord(c)) for c in ascii_str]
                self.converter_result.insert(tk.END, f"二进制: {' '.join(bin_values)}\n")
            
        except Exception as e:
            messagebox.showerror("错误", f"转换失败: {str(e)}")
    
    def _generate_data(self):
        """生成测试数据"""
        try:
            count = int(self.gen_count_var.get())
            length = int(self.gen_length_var.get())
            gen_type = self.gen_type_var.get()
            
            self.generator_result.delete("1.0", tk.END)
            
            import random
            
            if gen_type == "random":
                # 随机数据
                for i in range(count):
                    data = ''.join(random.choices('0123456789ABCDEF', k=length))
                    self.generator_result.insert(tk.END, f"{data}\n")
            
            elif gen_type == "sequence":
                # 递增序列
                for i in range(count):
                    data = f"{i:0{length}X}"[:length]
                    self.generator_result.insert(tk.END, f"{data}\n")
            
            elif gen_type == "pattern":
                # 固定模式
                pattern = "AA55"
                for i in range(count):
                    data = (pattern * (length // len(pattern) + 1))[:length]
                    self.generator_result.insert(tk.END, f"{data}\n")
            
            self.generator_result.insert(tk.END, f"\n已生成 {count} 条数据\n")
            
        except Exception as e:
            messagebox.showerror("错误", f"生成失败: {str(e)}")
    
    def _copy_generated_data(self):
        """复制生成的数据到剪贴板"""
        data = self.generator_result.get("1.0", tk.END)
        self.window.clipboard_clear()
        self.window.clipboard_append(data)
        messagebox.showinfo("成功", "数据已复制到剪贴板")
    
    def _start_stopwatch(self):
        """开始秒表"""
        import time
        self.stopwatch_running = True
        self.stopwatch_start_time = time.time() - self.stopwatch_elapsed
        self.stopwatch_start_btn.config(state=tk.DISABLED)
        self.stopwatch_stop_btn.config(state=tk.NORMAL)
        self._update_stopwatch()
    
    def _stop_stopwatch(self):
        """停止秒表"""
        self.stopwatch_running = False
        self.stopwatch_start_btn.config(state=tk.NORMAL)
        self.stopwatch_stop_btn.config(state=tk.DISABLED)
    
    def _reset_stopwatch(self):
        """重置秒表"""
        self.stopwatch_running = False
        self.stopwatch_elapsed = 0
        self.stopwatch_time_var.set("00:00:00.000")
        self.stopwatch_start_btn.config(state=tk.NORMAL)
        self.stopwatch_stop_btn.config(state=tk.DISABLED)
    
    def _update_stopwatch(self):
        """更新秒表显示"""
        if self.stopwatch_running:
            import time
            self.stopwatch_elapsed = time.time() - self.stopwatch_start_time
            
            hours = int(self.stopwatch_elapsed // 3600)
            minutes = int((self.stopwatch_elapsed % 3600) // 60)
            seconds = int(self.stopwatch_elapsed % 60)
            milliseconds = int((self.stopwatch_elapsed % 1) * 1000)
            
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.stopwatch_time_var.set(time_str)
            
            if self.window:
                self.window.after(10, self._update_stopwatch)
    
    def _start_countdown(self):
        """开始倒计时"""
        try:
            minutes = int(self.countdown_min_var.get())
            seconds = int(self.countdown_sec_var.get())
            
            self.countdown_remaining = minutes * 60 + seconds
            self.countdown_running = True
            self.countdown_start_btn.config(state=tk.DISABLED)
            self.countdown_stop_btn.config(state=tk.NORMAL)
            
            self._update_countdown()
        except:
            messagebox.showerror("错误", "请输入有效的时间")
    
    def _stop_countdown(self):
        """停止倒计时"""
        self.countdown_running = False
        self.countdown_start_btn.config(state=tk.NORMAL)
        self.countdown_stop_btn.config(state=tk.DISABLED)
    
    def _update_countdown(self):
        """更新倒计时显示"""
        if self.countdown_running and self.countdown_remaining > 0:
            minutes = self.countdown_remaining // 60
            seconds = self.countdown_remaining % 60
            
            time_str = f"{minutes:02d}:{seconds:02d}"
            self.countdown_time_var.set(time_str)
            
            self.countdown_remaining -= 1
            
            if self.window:
                self.window.after(1000, self._update_countdown)
        elif self.countdown_running and self.countdown_remaining <= 0:
            self.countdown_time_var.set("00:00")
            self.countdown_running = False
            self.countdown_start_btn.config(state=tk.NORMAL)
            self.countdown_stop_btn.config(state=tk.DISABLED)
            messagebox.showinfo("倒计时", "时间到!")