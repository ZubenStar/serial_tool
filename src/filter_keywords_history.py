"""
过滤关键词历史记录管理模块
提供过滤关键词的保存、查询和删除功能
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import tkinter as tk
from tkinter import ttk, messagebox


class FilterKeywordsHistory:
    """过滤关键词历史记录管理器"""
    
    def __init__(self, history_file: str = "filter_keywords_history.json"):
        self.history_file = Path(history_file)
        self.keywords_history: List[Dict[str, Any]] = []
        self.max_history = 100  # 最多保存100条历史记录
        self._load_history()
    
    def _load_history(self):
        """从文件加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.keywords_history = data.get('history', [])
            except Exception as e:
                print(f"加载过滤关键词历史失败: {e}")
                self.keywords_history = []
    
    def _save_history(self):
        """保存历史记录到文件"""
        try:
            data = {
                'history': self.keywords_history,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存过滤关键词历史失败: {e}")
    
    def add_keywords(self, keywords: str):
        """添加关键词到历史记录"""
        keywords = keywords.strip()
        if not keywords:
            return
        
        # 检查是否已存在
        for item in self.keywords_history:
            if item['keywords'] == keywords:
                # 更新使用时间和次数
                item['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                item['use_count'] = item.get('use_count', 1) + 1
                self._save_history()
                return
        
        # 添加新记录
        record = {
            'keywords': keywords,
            'added_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'last_used': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'use_count': 1
        }
        
        self.keywords_history.insert(0, record)
        
        # 限制历史记录数量
        if len(self.keywords_history) > self.max_history:
            self.keywords_history = self.keywords_history[:self.max_history]
        
        self._save_history()
    
    def get_all_history(self) -> List[Dict[str, Any]]:
        """获取所有历史记录"""
        return self.keywords_history.copy()
    
    def filter_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """按关键词过滤历史记录"""
        if not keyword:
            return self.keywords_history.copy()
        keyword = keyword.lower()
        return [item for item in self.keywords_history if keyword in item['keywords'].lower()]
    
    def delete_by_indices(self, indices: List[int]) -> int:
        """按索引删除记录"""
        if not indices:
            return 0
        
        # 降序排序以避免索引错位
        indices_sorted = sorted(indices, reverse=True)
        deleted_count = 0
        
        for idx in indices_sorted:
            if 0 <= idx < len(self.keywords_history):
                self.keywords_history.pop(idx)
                deleted_count += 1
        
        self._save_history()
        return deleted_count
    
    def clear_all(self) -> int:
        """清空所有历史记录"""
        count = len(self.keywords_history)
        self.keywords_history.clear()
        self._save_history()
        return count


class FilterKeywordsHistoryWindow:
    """过滤关键词历史记录窗口"""
    
    def __init__(self, parent: tk.Misc, history_manager: FilterKeywordsHistory, keywords_var: tk.StringVar):
        self.parent = parent
        self.history_manager = history_manager
        self.keywords_var = keywords_var  # 主界面的关键词输入框变量
        self.window = None
        self.filtered_records: List[Dict[str, Any]] = []
    
    def open_window(self):
        """打开历史记录窗口"""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("🔍 过滤关键词历史记录")
        self.window.geometry("900x600")
        
        # 创建主容器
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部搜索区域
        search_frame = ttk.LabelFrame(main_container, text="🔎 搜索", padding=15)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_input_frame, text="搜索:", font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.search_var = tk.StringVar()
        ttk.Entry(search_input_frame, textvariable=self.search_var, width=40, font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(search_input_frame, text="🔍 搜索", command=self._apply_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_input_frame, text="🔄 显示全部", command=self._show_all).pack(side=tk.LEFT, padx=5)
        
        # 中间列表区域
        list_frame = ttk.LabelFrame(main_container, text="📋 历史记录列表", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建Treeview
        columns = ("序号", "关键词", "使用次数", "最后使用时间", "添加时间")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode=tk.EXTENDED)
        
        # 配置列
        self.tree.heading("序号", text="序号")
        self.tree.heading("关键词", text="关键词")
        self.tree.heading("使用次数", text="使用次数")
        self.tree.heading("最后使用时间", text="最后使用时间")
        self.tree.heading("添加时间", text="添加时间")
        
        self.tree.column("序号", width=60, anchor=tk.CENTER)
        self.tree.column("关键词", width=350, anchor=tk.W)
        self.tree.column("使用次数", width=100, anchor=tk.CENTER)
        self.tree.column("最后使用时间", width=150, anchor=tk.CENTER)
        self.tree.column("添加时间", width=150, anchor=tk.CENTER)
        
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
        
        # 绑定双击事件应用关键词
        self.tree.bind('<Double-Button-1>', self._apply_keywords)
        
        # 底部操作区域
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill=tk.X)
        
        # 统计标签
        self.stats_label = ttk.Label(action_frame, text="", font=('Microsoft YaHei UI', 9))
        self.stats_label.pack(side=tk.LEFT, padx=10)
        
        # 操作按钮
        button_right_frame = ttk.Frame(action_frame)
        button_right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_right_frame, text="✅ 应用选中", command=self._apply_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_right_frame, text="🗑️ 删除选中", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_right_frame, text="🗑️ 清空全部", command=self._clear_all).pack(side=tk.LEFT, padx=5)
        
        # 初始化显示所有记录
        self._show_all()
    
    def _apply_filter(self):
        """应用过滤"""
        search_text = self.search_var.get().strip()
        self.filtered_records = self.history_manager.filter_by_keyword(search_text)
        self._update_display()
    
    def _show_all(self):
        """显示所有记录"""
        self.filtered_records = self.history_manager.get_all_history()
        self._update_display()
    
    def _update_display(self):
        """更新显示"""
        # 清空现有项
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加过滤后的记录
        for idx, record in enumerate(self.filtered_records):
            self.tree.insert('', tk.END, values=(
                idx + 1,
                record['keywords'],
                record.get('use_count', 1),
                record['last_used'],
                record['added_time']
            ))
        
        # 更新统计信息
        total = len(self.history_manager.keywords_history)
        filtered = len(self.filtered_records)
        self.stats_label.config(text=f"总记录数: {total} | 当前显示: {filtered} 条")
    
    def _apply_keywords(self, event: Any) -> None:
        """双击应用关键词到主界面"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        idx = int(item['values'][0]) - 1
        
        if 0 <= idx < len(self.filtered_records):
            record = self.filtered_records[idx]
            # 应用到主界面
            self.keywords_var.set(record['keywords'])
            messagebox.showinfo("成功", f"已应用关键词:\n{record['keywords']}")
    
    def _apply_selected(self):
        """应用选中的关键词"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要应用的记录")
            return
        
        item = self.tree.item(selection[0])
        idx = int(item['values'][0]) - 1
        
        if 0 <= idx < len(self.filtered_records):
            record = self.filtered_records[idx]
            # 应用到主界面
            self.keywords_var.set(record['keywords'])
            messagebox.showinfo("成功", f"已应用关键词:\n{record['keywords']}")
    
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
        all_records = self.history_manager.get_all_history()
        
        for sel in selection:
            item = self.tree.item(sel)
            display_idx = int(item['values'][0]) - 1
            record = self.filtered_records[display_idx]
            
            # 在原始列表中找到这条记录
            for i, r in enumerate(all_records):
                if r['keywords'] == record['keywords'] and r['added_time'] == record['added_time']:
                    indices_to_delete.append(i)
                    break
        
        deleted_count = self.history_manager.delete_by_indices(indices_to_delete)
        messagebox.showinfo("成功", f"已删除 {deleted_count} 条记录")
        
        # 刷新显示
        self._apply_filter() if self.search_var.get() else self._show_all()
    
    def _clear_all(self):
        """清空所有记录"""
        total = len(self.history_manager.keywords_history)
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