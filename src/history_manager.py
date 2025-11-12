"""
历史记录管理模块
提供串口数据历史记录的保存、查询、过滤和删除功能
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog


class HistoryRecord:
    """单条历史记录"""
    
    def __init__(self, port: str, timestamp: str, data: str):
        self.port = port
        self.timestamp = timestamp
        self.data = data
        self.datetime_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'port': self.port,
            'timestamp': self.timestamp,
            'data': self.data
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'HistoryRecord':
        """从字典创建"""
        return HistoryRecord(
            port=data['port'],
            timestamp=data['timestamp'],
            data=data['data']
        )
    
    def matches_keyword(self, keyword: str) -> bool:
        """检查是否匹配关键词"""
        return keyword.lower() in self.data.lower()
    
    def matches_regex(self, pattern: str) -> bool:
        """检查是否匹配正则表达式"""
        try:
            return bool(re.search(pattern, self.data))
        except re.error:
            return False


class HistoryManager:
    """历史记录管理器"""
    
    def __init__(self, history_dir: str = "history"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.history_dir / "serial_history.json"
        self.records: List[HistoryRecord] = []
        self.max_records = 10000  # 最大保存记录数
        self._load_history()
    
    def _load_history(self):
        """从文件加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [HistoryRecord.from_dict(r) for r in data.get('records', [])]
            except Exception as e:
                print(f"加载历史记录失败: {e}")
                self.records = []
    
    def _save_history(self):
        """保存历史记录到文件"""
        try:
            data = {
                'records': [r.to_dict() for r in self.records],
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {e}")
    
    def add_record(self, port: str, timestamp: str, data: str):
        """添加一条历史记录"""
        record = HistoryRecord(port, timestamp, data)
        self.records.append(record)
        
        # 如果超过最大记录数，删除最旧的记录
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]
        
        # 定期保存（每100条保存一次）
        if len(self.records) % 100 == 0:
            self._save_history()
    
    def get_all_records(self) -> List[HistoryRecord]:
        """获取所有历史记录"""
        return self.records.copy()
    
    def filter_by_keyword(self, keyword: str) -> List[HistoryRecord]:
        """按关键词过滤"""
        if not keyword:
            return self.records.copy()
        return [r for r in self.records if r.matches_keyword(keyword)]
    
    def filter_by_keywords(self, keywords: List[str]) -> List[HistoryRecord]:
        """按多个关键词过滤（满足任一关键词即可）"""
        if not keywords:
            return self.records.copy()
        return [r for r in self.records if any(r.matches_keyword(kw) for kw in keywords)]
    
    def filter_by_regex(self, pattern: str) -> List[HistoryRecord]:
        """按正则表达式过滤"""
        if not pattern:
            return self.records.copy()
        return [r for r in self.records if r.matches_regex(pattern)]
    
    def filter_by_port(self, port: str) -> List[HistoryRecord]:
        """按串口过滤"""
        if not port:
            return self.records.copy()
        return [r for r in self.records if r.port == port]
    
    def filter_by_time_range(self, start_time: datetime, end_time: datetime) -> List[HistoryRecord]:
        """按时间范围过滤"""
        return [r for r in self.records if start_time <= r.datetime_obj <= end_time]
    
    def delete_by_indices(self, indices: List[int]) -> int:
        """按索引删除记录"""
        if not indices:
            return 0
        
        # 降序排序以避免索引错位
        indices_sorted = sorted(indices, reverse=True)
        deleted_count = 0
        
        for idx in indices_sorted:
            if 0 <= idx < len(self.records):
                self.records.pop(idx)
                deleted_count += 1
        
        self._save_history()
        return deleted_count
    
    def delete_by_keyword(self, keyword: str) -> int:
        """删除包含关键词的记录"""
        if not keyword:
            return 0
        
        original_count = len(self.records)
        self.records = [r for r in self.records if not r.matches_keyword(keyword)]
        deleted_count = original_count - len(self.records)
        
        if deleted_count > 0:
            self._save_history()
        
        return deleted_count
    
    def delete_by_port(self, port: str) -> int:
        """删除指定串口的所有记录"""
        if not port:
            return 0
        
        original_count = len(self.records)
        self.records = [r for r in self.records if r.port != port]
        deleted_count = original_count - len(self.records)
        
        if deleted_count > 0:
            self._save_history()
        
        return deleted_count
    
    def clear_all(self) -> int:
        """清空所有历史记录"""
        count = len(self.records)
        self.records.clear()
        self._save_history()
        return count
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        ports = set(r.port for r in self.records)
        return {
            'total_records': len(self.records),
            'ports': list(ports),
            'port_count': len(ports),
            'oldest': self.records[0].timestamp if self.records else None,
            'newest': self.records[-1].timestamp if self.records else None
        }
    
    def save_now(self):
        """立即保存历史记录"""
        self._save_history()


class HistoryWindow:
    """历史记录窗口"""
    
    def __init__(self, parent, history_manager: HistoryManager):
        self.parent = parent
        self.history_manager = history_manager
        self.window = None
        self.filtered_records: List[HistoryRecord] = []
        self.selected_indices: List[int] = []
        
    def open_window(self):
        """打开历史记录窗口"""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("📜 历史记录管理")
        self.window.geometry("1200x700")
        
        # 创建主容器
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部过滤区域
        filter_frame = ttk.LabelFrame(main_container, text="🔍 过滤条件", padding=15)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 关键词过滤
        kw_frame = ttk.Frame(filter_frame)
        kw_frame.pack(fill=tk.X, pady=5)
        ttk.Label(kw_frame, text="关键词:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.keyword_var = tk.StringVar()
        ttk.Entry(kw_frame, textvariable=self.keyword_var, width=40, font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(kw_frame, text="多个关键词用逗号分隔", font=("Microsoft YaHei UI", 9), foreground='#6c757d').pack(side=tk.LEFT)
        
        # 串口过滤
        port_frame = ttk.Frame(filter_frame)
        port_frame.pack(fill=tk.X, pady=5)
        ttk.Label(port_frame, text="串口:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.port_var = tk.StringVar()
        ports = list(set(r.port for r in self.history_manager.records))
        port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, values=["全部"] + ports, width=20, font=('Microsoft YaHei UI', 10))
        port_combo.pack(side=tk.LEFT, padx=(0, 10))
        port_combo.set("全部")
        
        # 按钮区域
        button_frame = ttk.Frame(filter_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="🔍 应用过滤", command=self._apply_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 显示全部", command=self._show_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📊 统计信息", command=self._show_statistics).pack(side=tk.LEFT, padx=5)
        
        # 中间列表区域
        list_frame = ttk.LabelFrame(main_container, text="📋 历史记录列表", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建Treeview
        columns = ("序号", "时间", "串口", "数据预览")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode=tk.EXTENDED)
        
        # 配置列
        self.tree.heading("序号", text="序号")
        self.tree.heading("时间", text="时间")
        self.tree.heading("串口", text="串口")
        self.tree.heading("数据预览", text="数据预览")
        
        self.tree.column("序号", width=60, anchor=tk.CENTER)
        self.tree.column("时间", width=180, anchor=tk.W)
        self.tree.column("串口", width=100, anchor=tk.CENTER)
        self.tree.column("数据预览", width=800, anchor=tk.W)
        
        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定双击事件查看详情
        self.tree.bind('<Double-Button-1>', self._show_detail)
        
        # 底部操作区域
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill=tk.X)
        
        # 统计标签
        self.stats_label = ttk.Label(action_frame, text="", font=('Microsoft YaHei UI', 9))
        self.stats_label.pack(side=tk.LEFT, padx=10)
        
        # 操作按钮
        button_right_frame = ttk.Frame(action_frame)
        button_right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_right_frame, text="🗑️ 删除选中", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_right_frame, text="🗑️ 删除过滤结果", command=self._delete_filtered).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_right_frame, text="🗑️ 清空全部", command=self._clear_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_right_frame, text="💾 导出", command=self._export_records).pack(side=tk.LEFT, padx=5)
        
        # 初始化显示所有记录
        self._show_all()
    
    def _apply_filter(self):
        """应用过滤条件"""
        keywords_text = self.keyword_var.get().strip()
        port = self.port_var.get().strip()
        
        # 从所有记录开始过滤
        records = self.history_manager.get_all_records()
        
        # 按关键词过滤
        if keywords_text:
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            records = [r for r in records if any(r.matches_keyword(kw) for kw in keywords)]
        
        # 按串口过滤
        if port and port != "全部":
            records = [r for r in records if r.port == port]
        
        self.filtered_records = records
        self._update_display()
    
    def _show_all(self):
        """显示所有记录"""
        self.filtered_records = self.history_manager.get_all_records()
        self._update_display()
    
    def _update_display(self):
        """更新显示"""
        # 清空现有项
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加过滤后的记录
        for idx, record in enumerate(self.filtered_records):
            # 数据预览（最多显示100个字符）
            data_preview = record.data[:100] + "..." if len(record.data) > 100 else record.data
            # 移除换行符以便在列表中显示
            data_preview = data_preview.replace('\n', ' ').replace('\r', '')
            
            self.tree.insert('', tk.END, values=(
                idx + 1,
                record.timestamp,
                record.port,
                data_preview
            ))
        
        # 更新统计信息
        total = len(self.history_manager.records)
        filtered = len(self.filtered_records)
        self.stats_label.config(text=f"总记录数: {total} | 当前显示: {filtered} 条")
    
    def _show_detail(self, event):
        """显示详细信息"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        idx = int(item['values'][0]) - 1
        
        if 0 <= idx < len(self.filtered_records):
            record = self.filtered_records[idx]
            
            # 创建详情窗口
            detail_window = tk.Toplevel(self.window)
            detail_window.title(f"记录详情 - {record.port}")
            detail_window.geometry("800x600")
            
            # 信息区域
            info_frame = ttk.Frame(detail_window, padding=15)
            info_frame.pack(fill=tk.X)
            
            ttk.Label(info_frame, text=f"串口: {record.port}", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor=tk.W, pady=2)
            ttk.Label(info_frame, text=f"时间: {record.timestamp}", font=('Microsoft YaHei UI', 10)).pack(anchor=tk.W, pady=2)
            
            # 数据显示区域
            data_frame = ttk.LabelFrame(detail_window, text="数据内容", padding=10)
            data_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
            
            text_widget = scrolledtext.ScrolledText(
                data_frame,
                wrap=tk.WORD,
                font=('Consolas', 10),
                height=25
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert('1.0', record.data)
            text_widget.config(state=tk.DISABLED)
            
            # 关闭按钮
            ttk.Button(detail_window, text="关闭", command=detail_window.destroy).pack(pady=10)
    
    def _delete_selected(self):
        """删除选中的记录"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的记录")
            return
        
        count = len(selection)
        result = messagebox.askyesno("确认删除", f"确定要删除选中的 {count} 条记录吗？")
        if not result:
            return
        
        # 获取要删除的记录在原始列表中的索引
        indices_to_delete = []
        all_records = self.history_manager.get_all_records()
        
        for sel in selection:
            item = self.tree.item(sel)
            display_idx = int(item['values'][0]) - 1
            record = self.filtered_records[display_idx]
            
            # 在原始列表中找到这条记录
            for i, r in enumerate(all_records):
                if r.port == record.port and r.timestamp == record.timestamp and r.data == record.data:
                    indices_to_delete.append(i)
                    break
        
        deleted_count = self.history_manager.delete_by_indices(indices_to_delete)
        messagebox.showinfo("成功", f"已删除 {deleted_count} 条记录")
        
        # 刷新显示
        self._apply_filter() if self.keyword_var.get() or (self.port_var.get() and self.port_var.get() != "全部") else self._show_all()
    
    def _delete_filtered(self):
        """删除当前过滤的所有记录"""
        if not self.filtered_records:
            messagebox.showwarning("警告", "当前没有可删除的记录")
            return
        
        count = len(self.filtered_records)
        result = messagebox.askyesno("确认删除", f"确定要删除当前过滤的 {count} 条记录吗？")
        if not result:
            return
        
        # 获取要删除的记录在原始列表中的索引
        indices_to_delete = []
        all_records = self.history_manager.get_all_records()
        
        for record in self.filtered_records:
            for i, r in enumerate(all_records):
                if r.port == record.port and r.timestamp == record.timestamp and r.data == record.data:
                    indices_to_delete.append(i)
                    break
        
        deleted_count = self.history_manager.delete_by_indices(indices_to_delete)
        messagebox.showinfo("成功", f"已删除 {deleted_count} 条记录")
        
        # 刷新显示
        self._show_all()
    
    def _clear_all(self):
        """清空所有记录"""
        total = len(self.history_manager.records)
        if total == 0:
            messagebox.showinfo("提示", "历史记录已为空")
            return
        
        result = messagebox.askyesno("确认清空", f"确定要清空所有 {total} 条历史记录吗？\n此操作不可恢复！")
        if not result:
            return
        
        count = self.history_manager.clear_all()
        messagebox.showinfo("成功", f"已清空 {count} 条历史记录")
        
        # 刷新显示
        self._show_all()
    
    def _show_statistics(self):
        """显示统计信息"""
        stats = self.history_manager.get_statistics()
        
        info = f"历史记录统计信息\n\n"
        info += f"总记录数: {stats['total_records']} 条\n"
        info += f"涉及串口: {stats['port_count']} 个\n"
        info += f"串口列表: {', '.join(stats['ports']) if stats['ports'] else '无'}\n"
        info += f"最早记录: {stats['oldest'] or '无'}\n"
        info += f"最新记录: {stats['newest'] or '无'}\n"
        
        messagebox.showinfo("统计信息", info)
    
    def _export_records(self):
        """导出记录到文件"""
        from tkinter import filedialog
        
        if not self.filtered_records:
            messagebox.showwarning("警告", "当前没有可导出的记录")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("JSON文件", "*.json"), ("CSV文件", "*.csv"), ("所有文件", "*.*")],
            initialfile=f"history_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if not filename:
            return
        
        try:
            ext = Path(filename).suffix.lower()
            
            if ext == '.json':
                # 导出为JSON
                data = [r.to_dict() for r in self.filtered_records]
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            elif ext == '.csv':
                # 导出为CSV
                import csv
                with open(filename, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['时间', '串口', '数据'])
                    for record in self.filtered_records:
                        writer.writerow([record.timestamp, record.port, record.data])
            
            else:
                # 导出为纯文本
                with open(filename, 'w', encoding='utf-8') as f:
                    for record in self.filtered_records:
                        f.write(f"[{record.timestamp}] [{record.port}] {record.data}\n")
            
            messagebox.showinfo("成功", f"已导出 {len(self.filtered_records)} 条记录到:\n{filename}")
        
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")