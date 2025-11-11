"""
录制和回放模块
支持串口会话录制、回放和导出
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class SerialRecording:
    """串口录制数据类"""
    
    def __init__(self, port: str):
        self.port = port
        self.start_time = time.time()
        self.events: List[Dict] = []
        self.metadata = {
            'port': port,
            'start_time': datetime.now().isoformat(),
            'baudrate': None,
            'keywords': [],
            'regex_patterns': []
        }
    
    def add_event(self, event_type: str, data: str, timestamp: float = None):
        """添加事件"""
        if timestamp is None:
            timestamp = time.time()
        
        relative_time = timestamp - self.start_time
        
        self.events.append({
            'type': event_type,  # 'receive' or 'send'
            'data': data,
            'timestamp': timestamp,
            'relative_time': relative_time
        })
    
    def save_to_file(self, filepath: str):
        """保存录制到文件"""
        recording_data = {
            'metadata': self.metadata,
            'events': self.events
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(recording_data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_from_file(filepath: str) -> 'SerialRecording':
        """从文件加载录制"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        recording = SerialRecording(data['metadata']['port'])
        recording.metadata = data['metadata']
        recording.events = data['events']
        
        if recording.events:
            recording.start_time = recording.events[0]['timestamp']
        
        return recording


class RecorderManager:
    """录制管理器"""
    
    def __init__(self):
        self.recordings: Dict[str, SerialRecording] = {}
        self.active_ports: Dict[str, bool] = {}
    
    def start_recording(self, port: str, baudrate: int, keywords: List[str] = None, 
                       regex_patterns: List[str] = None):
        """开始录制"""
        if port in self.recordings:
            return False
        
        recording = SerialRecording(port)
        recording.metadata['baudrate'] = baudrate
        recording.metadata['keywords'] = keywords or []
        recording.metadata['regex_patterns'] = regex_patterns or []
        
        self.recordings[port] = recording
        self.active_ports[port] = True
        return True
    
    def stop_recording(self, port: str) -> Optional[SerialRecording]:
        """停止录制"""
        if port not in self.recordings:
            return None
        
        self.active_ports[port] = False
        return self.recordings.pop(port)
    
    def record_event(self, port: str, event_type: str, data: str):
        """记录事件"""
        if port in self.recordings and self.active_ports.get(port, False):
            self.recordings[port].add_event(event_type, data)
    
    def is_recording(self, port: str) -> bool:
        """检查是否正在录制"""
        return port in self.recordings and self.active_ports.get(port, False)


class RecorderPlayerWindow:
    """录制回放窗口"""
    
    def __init__(self, parent, monitor):
        self.parent = parent
        self.monitor = monitor
        self.window = None
        
        self.recorder = RecorderManager()
        self.current_playback: Optional[SerialRecording] = None
        self.playback_running = False
        self.playback_speed = 1.0
    
    def open_window(self):
        """打开录制回放窗口"""
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("录制与回放")
        self.window.geometry("800x600")
        
        # 创建标签页
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 录制标签页
        record_frame = ttk.Frame(notebook)
        notebook.add(record_frame, text="🔴 录制")
        self._create_record_view(record_frame)
        
        # 回放标签页
        playback_frame = ttk.Frame(notebook)
        notebook.add(playback_frame, text="▶️ 回放")
        self._create_playback_view(playback_frame)
        
        # 管理标签页
        manage_frame = ttk.Frame(notebook)
        notebook.add(manage_frame, text="📁 管理")
        self._create_manage_view(manage_frame)
    
    def _create_record_view(self, parent):
        """创建录制视图"""
        # 状态显示
        status_frame = ttk.LabelFrame(parent, text="录制状态", padding=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.record_status_label = ttk.Label(status_frame, text="未开始录制", foreground="gray")
        self.record_status_label.pack(anchor=tk.W)
        
        # 录制列表
        list_frame = ttk.LabelFrame(parent, text="正在录制", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("串口", "开始时间", "事件数", "持续时间")
        self.record_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.record_tree.heading(col, text=col)
            self.record_tree.column(col, width=150)
        
        self.record_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.record_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.record_tree.config(yscrollcommand=scrollbar.set)
        
        # 控制按钮
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="开始录制选中串口", command=self._start_record).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="停止录制", command=self._stop_record).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="保存录制", command=self._save_recording).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="刷新", command=self._refresh_record_list).pack(side=tk.RIGHT, padx=2)
    
    def _create_playback_view(self, parent):
        """创建回放视图"""
        # 文件选择
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="录制文件:").pack(side=tk.LEFT)
        self.playback_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.playback_file_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(file_frame, text="浏览...", command=self._browse_playback_file).pack(side=tk.LEFT)
        
        # 回放信息
        info_frame = ttk.LabelFrame(parent, text="录制信息", padding=10)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.playback_info_text = tk.Text(info_frame, height=5, wrap=tk.WORD, state=tk.DISABLED)
        self.playback_info_text.pack(fill=tk.X)
        
        # 回放控制
        control_frame = ttk.LabelFrame(parent, text="回放控制", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 速度控制
        speed_frame = ttk.Frame(control_frame)
        speed_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(speed_frame, text="回放速度:").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_slider = ttk.Scale(speed_frame, from_=0.1, to=5.0, variable=self.speed_var, orient=tk.HORIZONTAL)
        speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.pack(side=tk.LEFT)
        
        self.speed_var.trace_add('write', lambda *args: self.speed_label.config(text=f"{self.speed_var.get():.1f}x"))
        
        # 进度条
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT)
        self.playback_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.playback_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress_label = ttk.Label(progress_frame, text="0/0")
        self.progress_label.pack(side=tk.LEFT)
        
        # 控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.play_button = ttk.Button(button_frame, text="▶ 播放", command=self._start_playback)
        self.play_button.pack(side=tk.LEFT, padx=2)
        
        self.pause_button = ttk.Button(button_frame, text="⏸ 暂停", command=self._pause_playback, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(button_frame, text="⏹ 停止", command=self._stop_playback).pack(side=tk.LEFT, padx=2)
        
        # 事件列表
        event_frame = ttk.LabelFrame(parent, text="事件列表", padding=10)
        event_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("时间", "类型", "数据")
        self.event_tree = ttk.Treeview(event_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.event_tree.heading(col, text=col)
            if col == "数据":
                self.event_tree.column(col, width=400)
            else:
                self.event_tree.column(col, width=100)
        
        self.event_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(event_frame, orient=tk.VERTICAL, command=self.event_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.event_tree.config(yscrollcommand=scrollbar.set)
    
    def _create_manage_view(self, parent):
        """创建管理视图"""
        # 录制文件列表
        list_frame = ttk.LabelFrame(parent, text="已保存的录制", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("文件名", "串口", "时间", "事件数")
        self.manage_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.manage_tree.heading(col, text=col)
            self.manage_tree.column(col, width=150)
        
        self.manage_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.manage_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.manage_tree.config(yscrollcommand=scrollbar.set)
        
        # 操作按钮
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="加载", command=self._load_selected_recording).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="删除", command=self._delete_recording).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="导出CSV", command=self._export_to_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="刷新列表", command=self._refresh_manage_list).pack(side=tk.RIGHT, padx=2)
        
        # 初始加载
        self._refresh_manage_list()
    
    def _start_record(self):
        """开始录制"""
        active_ports = self.monitor.get_active_ports()
        
        if not active_ports:
            messagebox.showwarning("警告", "没有活动的串口")
            return
        
        # 让用户选择要录制的串口
        if len(active_ports) == 1:
            port = active_ports[0]
        else:
            # 创建选择对话框
            dialog = tk.Toplevel(self.window)
            dialog.title("选择串口")
            dialog.geometry("300x200")
            
            ttk.Label(dialog, text="选择要录制的串口:").pack(pady=10)
            
            listbox = tk.Listbox(dialog)
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            for p in active_ports:
                listbox.insert(tk.END, p)
            
            selected_port = [None]
            
            def on_select():
                selection = listbox.curselection()
                if selection:
                    selected_port[0] = listbox.get(selection[0])
                    dialog.destroy()
            
            ttk.Button(dialog, text="确定", command=on_select).pack(pady=5)
            
            dialog.wait_window()
            port = selected_port[0]
            
            if not port:
                return
        
        # 开始录制
        if self.recorder.start_recording(port, 9600):  # TODO: 获取实际波特率
            self.record_status_label.config(text=f"正在录制: {port}", foreground="red")
            self._refresh_record_list()
            messagebox.showinfo("成功", f"已开始录制 {port}")
        else:
            messagebox.showerror("错误", f"无法开始录制 {port}")
    
    def _stop_record(self):
        """停止录制"""
        selection = self.record_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要停止的录制")
            return
        
        item = self.record_tree.item(selection[0])
        port = item['values'][0]
        
        recording = self.recorder.stop_recording(port)
        if recording:
            self.record_status_label.config(text="录制已停止", foreground="gray")
            self._refresh_record_list()
            
            # 询问是否保存
            if messagebox.askyesno("保存录制", "是否保存此录制？"):
                self._save_recording_object(recording)
    
    def _save_recording(self):
        """保存录制"""
        selection = self.record_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要保存的录制")
            return
        
        item = self.record_tree.item(selection[0])
        port = item['values'][0]
        
        if port in self.recorder.recordings:
            self._save_recording_object(self.recorder.recordings[port])
    
    def _save_recording_object(self, recording: SerialRecording):
        """保存录制对象到文件"""
        default_name = f"{recording.port}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filename = filedialog.asksaveasfilename(
            title="保存录制",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                recording.save_to_file(filename)
                messagebox.showinfo("成功", f"录制已保存到:\n{filename}")
                self._refresh_manage_list()
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def _refresh_record_list(self):
        """刷新录制列表"""
        # 清空列表
        for item in self.record_tree.get_children():
            self.record_tree.delete(item)
        
        # 添加录制项
        for port, recording in self.recorder.recordings.items():
            if self.recorder.is_recording(port):
                start_time = datetime.fromtimestamp(recording.start_time).strftime('%H:%M:%S')
                event_count = len(recording.events)
                duration = time.time() - recording.start_time
                duration_str = f"{int(duration)}秒"
                
                self.record_tree.insert('', tk.END, values=(port, start_time, event_count, duration_str))
    
    def _browse_playback_file(self):
        """浏览回放文件"""
        filename = filedialog.askopenfilename(
            title="选择录制文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            self.playback_file_var.set(filename)
            self._load_playback_file(filename)
    
    def _load_playback_file(self, filepath: str):
        """加载回放文件"""
        try:
            self.current_playback = SerialRecording.load_from_file(filepath)
            
            # 显示信息
            self.playback_info_text.config(state=tk.NORMAL)
            self.playback_info_text.delete("1.0", tk.END)
            
            metadata = self.current_playback.metadata
            self.playback_info_text.insert(tk.END, f"串口: {metadata['port']}\n")
            self.playback_info_text.insert(tk.END, f"开始时间: {metadata['start_time']}\n")
            self.playback_info_text.insert(tk.END, f"波特率: {metadata.get('baudrate', 'N/A')}\n")
            self.playback_info_text.insert(tk.END, f"事件数: {len(self.current_playback.events)}\n")
            
            self.playback_info_text.config(state=tk.DISABLED)
            
            # 显示事件列表
            for item in self.event_tree.get_children():
                self.event_tree.delete(item)
            
            for event in self.current_playback.events:
                event_time = f"{event['relative_time']:.3f}s"
                event_type = "接收" if event['type'] == 'receive' else "发送"
                data_preview = event['data'][:50] + "..." if len(event['data']) > 50 else event['data']
                
                self.event_tree.insert('', tk.END, values=(event_time, event_type, data_preview))
            
            # 更新进度
            total_events = len(self.current_playback.events)
            self.playback_progress['maximum'] = total_events
            self.playback_progress['value'] = 0
            self.progress_label.config(text=f"0/{total_events}")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载失败: {str(e)}")
    
    def _start_playback(self):
        """开始回放"""
        if not self.current_playback:
            messagebox.showwarning("警告", "请先加载录制文件")
            return
        
        self.playback_running = True
        self.play_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        
        # 在后台线程中回放
        import threading
        threading.Thread(target=self._playback_thread, daemon=True).start()
    
    def _playback_thread(self):
        """回放线程"""
        events = self.current_playback.events
        speed = self.speed_var.get()
        
        for idx, event in enumerate(events):
            if not self.playback_running:
                break
            
            # 等待到事件时间
            if idx > 0:
                time_diff = event['relative_time'] - events[idx-1]['relative_time']
                time.sleep(time_diff / speed)
            
            # 更新进度
            self.window.after(0, lambda i=idx+1: self._update_playback_progress(i, len(events)))
            
            # TODO: 实际发送数据到串口或显示
            print(f"[回放] {event['type']}: {event['data']}")
        
        self.window.after(0, self._playback_finished)
    
    def _update_playback_progress(self, current: int, total: int):
        """更新回放进度"""
        self.playback_progress['value'] = current
        self.progress_label.config(text=f"{current}/{total}")
    
    def _pause_playback(self):
        """暂停回放"""
        self.playback_running = False
        self.play_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
    
    def _stop_playback(self):
        """停止回放"""
        self.playback_running = False
        self._playback_finished()
    
    def _playback_finished(self):
        """回放完成"""
        self.playback_running = False
        self.play_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        messagebox.showinfo("完成", "回放已完成")
    
    def _refresh_manage_list(self):
        """刷新管理列表"""
        # 清空列表
        for item in self.manage_tree.get_children():
            self.manage_tree.delete(item)
        
        # 扫描录制文件
        recordings_dir = Path("recordings")
        if not recordings_dir.exists():
            recordings_dir.mkdir()
            return
        
        for file_path in recordings_dir.glob("*.json"):
            try:
                recording = SerialRecording.load_from_file(str(file_path))
                
                filename = file_path.name
                port = recording.metadata['port']
                start_time = recording.metadata['start_time']
                event_count = len(recording.events)
                
                self.manage_tree.insert('', tk.END, values=(filename, port, start_time, event_count))
            except:
                pass
    
    def _load_selected_recording(self):
        """加载选中的录制"""
        selection = self.manage_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要加载的录制")
            return
        
        item = self.manage_tree.item(selection[0])
        filename = item['values'][0]
        
        filepath = Path("recordings") / filename
        if filepath.exists():
            self.playback_file_var.set(str(filepath))
            self._load_playback_file(str(filepath))
    
    def _delete_recording(self):
        """删除录制"""
        selection = self.manage_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的录制")
            return
        
        item = self.manage_tree.item(selection[0])
        filename = item['values'][0]
        
        if messagebox.askyesno("确认", f"确定要删除 {filename} 吗？"):
            filepath = Path("recordings") / filename
            if filepath.exists():
                filepath.unlink()
                self._refresh_manage_list()
                messagebox.showinfo("成功", "录制已删除")
    
    def _export_to_csv(self):
        """导出为CSV"""
        selection = self.manage_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要导出的录制")
            return
        
        item = self.manage_tree.item(selection[0])
        filename = item['values'][0]
        
        filepath = Path("recordings") / filename
        if not filepath.exists():
            return
        
        try:
            recording = SerialRecording.load_from_file(str(filepath))
            
            csv_filename = filedialog.asksaveasfilename(
                title="导出为CSV",
                defaultextension=".csv",
                initialfile=filename.replace('.json', '.csv'),
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if csv_filename:
                import csv
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['时间(秒)', '类型', '数据'])
                    
                    for event in recording.events:
                        writer.writerow([
                            f"{event['relative_time']:.3f}",
                            event['type'],
                            event['data']
                        ])
                
                messagebox.showinfo("成功", f"已导出到:\n{csv_filename}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def record_receive_event(self, port: str, data: str):
        """记录接收事件（供外部调用）"""
        self.recorder.record_event(port, 'receive', data)
    
    def record_send_event(self, port: str, data: str):
        """记录发送事件（供外部调用）"""
        self.recorder.record_event(port, 'send', data)