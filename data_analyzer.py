"""
数据分析工具模块
支持协议解析、数据完整性检查、错误率统计等
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import re
import json
from typing import Dict, List, Optional, Tuple
from collections import Counter
import binascii


class ProtocolParser:
    """协议解析器基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    def can_parse(self, data: str) -> bool:
        """判断是否可以解析该数据"""
        raise NotImplementedError
    
    def parse(self, data: str) -> Dict:
        """解析数据"""
        raise NotImplementedError


class JSONParser(ProtocolParser):
    """JSON协议解析器"""
    
    def __init__(self):
        super().__init__("JSON")
    
    def can_parse(self, data: str) -> bool:
        """判断是否为JSON格式"""
        try:
            json.loads(data)
            return True
        except:
            return False
    
    def parse(self, data: str) -> Dict:
        """解析JSON数据"""
        try:
            parsed = json.loads(data)
            return {
                'success': True,
                'type': 'JSON',
                'data': parsed,
                'formatted': json.dumps(parsed, indent=2, ensure_ascii=False)
            }
        except Exception as e:
            return {
                'success': False,
                'type': 'JSON',
                'error': str(e)
            }


class HexParser(ProtocolParser):
    """十六进制数据解析器"""
    
    def __init__(self):
        super().__init__("HEX")
    
    def can_parse(self, data: str) -> bool:
        """判断是否为十六进制格式"""
        # 检查是否包含十六进制模式
        hex_pattern = r'^([0-9A-Fa-f]{2}\s*)+$'
        return bool(re.match(hex_pattern, data.strip()))
    
    def parse(self, data: str) -> Dict:
        """解析十六进制数据"""
        try:
            # 移除空格并转换为字节
            hex_str = data.replace(' ', '').replace('\n', '')
            bytes_data = bytes.fromhex(hex_str)
            
            # 尝试转换为ASCII
            try:
                ascii_str = bytes_data.decode('ascii', errors='ignore')
            except:
                ascii_str = "无法转换为ASCII"
            
            return {
                'success': True,
                'type': 'HEX',
                'hex': hex_str,
                'bytes': list(bytes_data),
                'ascii': ascii_str,
                'length': len(bytes_data)
            }
        except Exception as e:
            return {
                'success': False,
                'type': 'HEX',
                'error': str(e)
            }


class ModbusParser(ProtocolParser):
    """Modbus协议解析器"""
    
    def __init__(self):
        super().__init__("Modbus")
    
    def can_parse(self, data: str) -> bool:
        """判断是否为Modbus格式"""
        # 简单检查：Modbus数据通常是十六进制格式，且有特定的功能码
        if not re.match(r'^([0-9A-Fa-f]{2}\s*)+$', data.strip()):
            return False
        
        try:
            hex_str = data.replace(' ', '')
            if len(hex_str) < 8:  # 最小Modbus帧长度
                return False
            
            # 检查功能码（第二个字节）
            func_code = int(hex_str[2:4], 16)
            return func_code in [1, 2, 3, 4, 5, 6, 15, 16]
        except:
            return False
    
    def parse(self, data: str) -> Dict:
        """解析Modbus数据"""
        try:
            hex_str = data.replace(' ', '')
            bytes_data = bytes.fromhex(hex_str)
            
            if len(bytes_data) < 4:
                return {'success': False, 'error': '数据长度不足'}
            
            slave_id = bytes_data[0]
            func_code = bytes_data[1]
            
            func_names = {
                1: 'Read Coils',
                2: 'Read Discrete Inputs',
                3: 'Read Holding Registers',
                4: 'Read Input Registers',
                5: 'Write Single Coil',
                6: 'Write Single Register',
                15: 'Write Multiple Coils',
                16: 'Write Multiple Registers'
            }
            
            return {
                'success': True,
                'type': 'Modbus',
                'slave_id': slave_id,
                'function_code': func_code,
                'function_name': func_names.get(func_code, 'Unknown'),
                'data_bytes': list(bytes_data[2:]),
                'raw_hex': hex_str
            }
        except Exception as e:
            return {
                'success': False,
                'type': 'Modbus',
                'error': str(e)
            }


class ChecksumValidator:
    """校验和验证器"""
    
    @staticmethod
    def calculate_crc16(data: bytes) -> int:
        """计算CRC16校验和"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    @staticmethod
    def calculate_xor(data: bytes) -> int:
        """计算XOR校验和"""
        result = 0
        for byte in data:
            result ^= byte
        return result
    
    @staticmethod
    def calculate_sum(data: bytes) -> int:
        """计算字节和"""
        return sum(data) & 0xFF
    
    @staticmethod
    def verify_checksum(data: str, method: str = 'CRC16') -> Dict:
        """验证校验和"""
        try:
            # 移除空格并转换为字节
            hex_str = data.replace(' ', '').replace('\n', '')
            bytes_data = bytes.fromhex(hex_str)
            
            if len(bytes_data) < 3:
                return {'success': False, 'error': '数据长度不足'}
            
            # 分离数据和校验和（假设最后2字节是校验和）
            data_part = bytes_data[:-2]
            checksum_received = int.from_bytes(bytes_data[-2:], byteorder='little')
            
            # 计算校验和
            if method == 'CRC16':
                checksum_calculated = ChecksumValidator.calculate_crc16(data_part)
            elif method == 'XOR':
                checksum_calculated = ChecksumValidator.calculate_xor(data_part)
            else:  # SUM
                checksum_calculated = ChecksumValidator.calculate_sum(data_part)
            
            return {
                'success': True,
                'method': method,
                'calculated': hex(checksum_calculated),
                'received': hex(checksum_received),
                'valid': checksum_calculated == checksum_received
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class DataAnalyzerWindow:
    """数据分析工具窗口"""
    
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        
        # 协议解析器列表
        self.parsers = [
            JSONParser(),
            HexParser(),
            ModbusParser()
        ]
        
        # 统计数据
        self.total_packets = 0
        self.error_packets = 0
        self.protocol_stats = Counter()
    
    def open_analyzer_window(self):
        """打开数据分析窗口"""
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("数据分析工具")
        self.window.geometry("900x700")
        
        # 创建标签页
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 协议解析标签页
        parser_frame = ttk.Frame(notebook)
        notebook.add(parser_frame, text="🔍 协议解析")
        self._create_parser_view(parser_frame)
        
        # 校验和验证标签页
        checksum_frame = ttk.Frame(notebook)
        notebook.add(checksum_frame, text="✓ 校验和验证")
        self._create_checksum_view(checksum_frame)
        
        # 数据统计标签页
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="📊 数据统计")
        self._create_stats_view(stats_frame)
        
        # 错误分析标签页
        error_frame = ttk.Frame(notebook)
        notebook.add(error_frame, text="⚠️ 错误分析")
        self._create_error_analysis_view(error_frame)
    
    def _create_parser_view(self, parent):
        """创建协议解析视图"""
        # 输入区
        input_frame = ttk.LabelFrame(parent, text="数据输入", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.parser_input = scrolledtext.ScrolledText(input_frame, height=8, wrap=tk.WORD)
        self.parser_input.pack(fill=tk.BOTH, expand=True)
        
        # 控制按钮
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="自动识别", command=self._auto_parse).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="解析为JSON", command=lambda: self._parse_as('JSON')).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="解析为HEX", command=lambda: self._parse_as('HEX')).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="解析为Modbus", command=lambda: self._parse_as('Modbus')).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="清除", command=lambda: self.parser_output.delete("1.0", tk.END)).pack(side=tk.RIGHT, padx=2)
        
        # 输出区
        output_frame = ttk.LabelFrame(parent, text="解析结果", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.parser_output = scrolledtext.ScrolledText(output_frame, height=15, wrap=tk.WORD)
        self.parser_output.pack(fill=tk.BOTH, expand=True)
    
    def _create_checksum_view(self, parent):
        """创建校验和验证视图"""
        # 输入区
        input_frame = ttk.LabelFrame(parent, text="数据输入 (十六进制)", padding=10)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.checksum_input = tk.Text(input_frame, height=5, wrap=tk.WORD)
        self.checksum_input.pack(fill=tk.X)
        
        # 控制区
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="校验方法:").pack(side=tk.LEFT)
        self.checksum_method = tk.StringVar(value="CRC16")
        ttk.Radiobutton(control_frame, text="CRC16", variable=self.checksum_method, value="CRC16").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(control_frame, text="XOR", variable=self.checksum_method, value="XOR").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(control_frame, text="SUM", variable=self.checksum_method, value="SUM").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="验证", command=self._verify_checksum).pack(side=tk.RIGHT, padx=2)
        ttk.Button(control_frame, text="计算", command=self._calculate_checksum).pack(side=tk.RIGHT, padx=2)
        
        # 结果区
        result_frame = ttk.LabelFrame(parent, text="验证结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.checksum_output = scrolledtext.ScrolledText(result_frame, height=10, wrap=tk.WORD)
        self.checksum_output.pack(fill=tk.BOTH, expand=True)
    
    def _create_stats_view(self, parent):
        """创建数据统计视图"""
        # 统计信息显示
        info_frame = ttk.LabelFrame(parent, text="总体统计", padding=10)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_total_label = ttk.Label(info_frame, text="总数据包: 0")
        self.stats_total_label.pack(anchor=tk.W)
        
        self.stats_error_label = ttk.Label(info_frame, text="错误数据包: 0")
        self.stats_error_label.pack(anchor=tk.W)
        
        self.stats_error_rate_label = ttk.Label(info_frame, text="错误率: 0.00%")
        self.stats_error_rate_label.pack(anchor=tk.W)
        
        # 协议分布
        protocol_frame = ttk.LabelFrame(parent, text="协议分布", padding=10)
        protocol_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.protocol_canvas = tk.Canvas(protocol_frame, bg="white", height=300)
        self.protocol_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 控制按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="刷新统计", command=self._refresh_stats).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="重置统计", command=self._reset_stats).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="导出报告", command=self._export_stats_report).pack(side=tk.RIGHT, padx=2)
    
    def _create_error_analysis_view(self, parent):
        """创建错误分析视图"""
        # 错误列表
        list_frame = ttk.LabelFrame(parent, text="错误记录", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("时间", "类型", "描述", "数据")
        self.error_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.error_tree.heading(col, text=col)
            self.error_tree.column(col, width=150)
        
        self.error_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.error_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.error_tree.config(yscrollcommand=scrollbar.set)
        
        # 详细信息
        detail_frame = ttk.LabelFrame(parent, text="错误详情", padding=10)
        detail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.error_detail_text = scrolledtext.ScrolledText(detail_frame, height=8, wrap=tk.WORD)
        self.error_detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 绑定选择事件
        self.error_tree.bind('<<TreeviewSelect>>', self._on_error_selected)
    
    def _auto_parse(self):
        """自动识别协议并解析"""
        data = self.parser_input.get("1.0", tk.END).strip()
        if not data:
            messagebox.showwarning("警告", "请输入数据")
            return
        
        self.parser_output.delete("1.0", tk.END)
        
        # 尝试所有解析器
        parsed = False
        for parser in self.parsers:
            if parser.can_parse(data):
                result = parser.parse(data)
                self._display_parse_result(result)
                parsed = True
                break
        
        if not parsed:
            self.parser_output.insert(tk.END, "未能识别数据格式\n")
            self.parser_output.insert(tk.END, f"原始数据: {data}\n")
    
    def _parse_as(self, parser_type: str):
        """使用指定解析器解析"""
        data = self.parser_input.get("1.0", tk.END).strip()
        if not data:
            messagebox.showwarning("警告", "请输入数据")
            return
        
        self.parser_output.delete("1.0", tk.END)
        
        # 找到对应的解析器
        parser = next((p for p in self.parsers if p.name == parser_type), None)
        if parser:
            result = parser.parse(data)
            self._display_parse_result(result)
        else:
            self.parser_output.insert(tk.END, f"未找到 {parser_type} 解析器\n")
    
    def _display_parse_result(self, result: Dict):
        """显示解析结果"""
        if result['success']:
            self.parser_output.insert(tk.END, f"协议类型: {result['type']}\n\n")
            
            for key, value in result.items():
                if key not in ['success', 'type']:
                    self.parser_output.insert(tk.END, f"{key}: {value}\n")
        else:
            self.parser_output.insert(tk.END, f"解析失败: {result.get('error', '未知错误')}\n")
    
    def _verify_checksum(self):
        """验证校验和"""
        data = self.checksum_input.get("1.0", tk.END).strip()
        if not data:
            messagebox.showwarning("警告", "请输入数据")
            return
        
        method = self.checksum_method.get()
        result = ChecksumValidator.verify_checksum(data, method)
        
        self.checksum_output.delete("1.0", tk.END)
        
        if result['success']:
            self.checksum_output.insert(tk.END, f"校验方法: {result['method']}\n")
            self.checksum_output.insert(tk.END, f"计算值: {result['calculated']}\n")
            self.checksum_output.insert(tk.END, f"接收值: {result['received']}\n")
            self.checksum_output.insert(tk.END, f"验证结果: {'✓ 通过' if result['valid'] else '✗ 失败'}\n")
        else:
            self.checksum_output.insert(tk.END, f"验证失败: {result.get('error', '未知错误')}\n")
    
    def _calculate_checksum(self):
        """计算校验和"""
        data = self.checksum_input.get("1.0", tk.END).strip()
        if not data:
            messagebox.showwarning("警告", "请输入数据")
            return
        
        try:
            hex_str = data.replace(' ', '').replace('\n', '')
            bytes_data = bytes.fromhex(hex_str)
            
            method = self.checksum_method.get()
            
            if method == 'CRC16':
                checksum = ChecksumValidator.calculate_crc16(bytes_data)
            elif method == 'XOR':
                checksum = ChecksumValidator.calculate_xor(bytes_data)
            else:  # SUM
                checksum = ChecksumValidator.calculate_sum(bytes_data)
            
            self.checksum_output.delete("1.0", tk.END)
            self.checksum_output.insert(tk.END, f"校验方法: {method}\n")
            self.checksum_output.insert(tk.END, f"计算结果: {hex(checksum)} ({checksum})\n")
            self.checksum_output.insert(tk.END, f"完整数据: {hex_str} {hex(checksum)[2:].upper().zfill(4)}\n")
        except Exception as e:
            messagebox.showerror("错误", f"计算失败: {str(e)}")
    
    def _refresh_stats(self):
        """刷新统计信息"""
        # 更新标签
        self.stats_total_label.config(text=f"总数据包: {self.total_packets}")
        self.stats_error_label.config(text=f"错误数据包: {self.error_packets}")
        
        error_rate = (self.error_packets / self.total_packets * 100) if self.total_packets > 0 else 0
        self.stats_error_rate_label.config(text=f"错误率: {error_rate:.2f}%")
        
        # 绘制协议分布图
        self._draw_protocol_distribution()
    
    def _reset_stats(self):
        """重置统计"""
        self.total_packets = 0
        self.error_packets = 0
        self.protocol_stats.clear()
        self._refresh_stats()
    
    def _draw_protocol_distribution(self):
        """绘制协议分布图"""
        self.protocol_canvas.delete("all")
        
        if not self.protocol_stats:
            self.protocol_canvas.create_text(
                200, 150, text="暂无数据",
                font=("TkDefaultFont", 14), fill="gray"
            )
            return
        
        # 绘制简单的条形图
        canvas_width = self.protocol_canvas.winfo_width() or 600
        canvas_height = self.protocol_canvas.winfo_height() or 300
        
        protocols = list(self.protocol_stats.items())
        max_count = max(count for _, count in protocols) if protocols else 1
        
        bar_width = 60
        spacing = 20
        start_x = 50
        
        colors = ['#4285F4', '#34A853', '#FBBC04', '#EA4335', '#9C27B0']
        
        for idx, (protocol, count) in enumerate(protocols):
            x = start_x + idx * (bar_width + spacing)
            bar_height = (count / max_count) * (canvas_height - 100)
            y = canvas_height - 50 - bar_height
            
            color = colors[idx % len(colors)]
            
            # 绘制条形
            self.protocol_canvas.create_rectangle(
                x, y, x + bar_width, canvas_height - 50,
                fill=color, outline=color
            )
            
            # 标签
            self.protocol_canvas.create_text(
                x + bar_width // 2, canvas_height - 30,
                text=protocol, angle=0
            )
            
            # 数值
            self.protocol_canvas.create_text(
                x + bar_width // 2, y - 10,
                text=str(count)
            )
    
    def _export_stats_report(self):
        """导出统计报告"""
        from tkinter import filedialog
        from datetime import datetime
        
        filename = filedialog.asksaveasfilename(
            title="导出统计报告",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("数据分析统计报告\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    f.write(f"总数据包: {self.total_packets}\n")
                    f.write(f"错误数据包: {self.error_packets}\n")
                    error_rate = (self.error_packets / self.total_packets * 100) if self.total_packets > 0 else 0
                    f.write(f"错误率: {error_rate:.2f}%\n\n")
                    
                    f.write("协议分布:\n")
                    for protocol, count in self.protocol_stats.items():
                        percentage = (count / self.total_packets * 100) if self.total_packets > 0 else 0
                        f.write(f"  {protocol}: {count} ({percentage:.1f}%)\n")
                
                messagebox.showinfo("成功", f"统计报告已导出到:\n{filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def _on_error_selected(self, event):
        """错误项被选中时"""
        selection = self.error_tree.selection()
        if selection:
            item = self.error_tree.item(selection[0])
            values = item['values']
            
            self.error_detail_text.delete("1.0", tk.END)
            self.error_detail_text.insert(tk.END, f"时间: {values[0]}\n")
            self.error_detail_text.insert(tk.END, f"类型: {values[1]}\n")
            self.error_detail_text.insert(tk.END, f"描述: {values[2]}\n")
            self.error_detail_text.insert(tk.END, f"数据: {values[3]}\n")
    
    def add_packet_stats(self, packet_type: str, is_error: bool = False):
        """添加数据包统计"""
        self.total_packets += 1
        if is_error:
            self.error_packets += 1
        self.protocol_stats[packet_type] += 1