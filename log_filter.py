"""
日志过滤工具模块
支持打开文本文件并根据关键词筛选显示包含关键词的行
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import re
from pathlib import Path
from typing import List, Set


class LogFilterWindow:
    """日志过滤窗口"""
    
    def __init__(self, parent=None, log_dir="logs"):
        """初始化日志过滤窗口"""
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("日志过滤工具")
        self.window.geometry("1000x700")
        
        self.current_file = None
        self.all_lines = []  # 存储所有行
        self.filtered_lines = []  # 存储过滤后的行
        self.log_dir = log_dir  # 应用生成的日志目录
        
        # 查询功能状态
        self.search_matches = []  # 存储所有匹配位置 [(line_index, start, end), ...]
        self.current_match_index = -1  # 当前匹配位置索引
        self.last_search_keyword = ""  # 上次搜索的关键词
        
        self._create_widgets()
        
    def _create_widgets(self):
        """创建界面组件"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # 文件操作按钮
        ttk.Button(toolbar, text="打开文件", command=self._open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self._reload_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="清除", command=self._clear_display).pack(side=tk.LEFT, padx=2)
        
        # 文件路径显示
        self.file_label = ttk.Label(toolbar, text="未打开文件", foreground="gray")
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        # 过滤控制区
        filter_frame = ttk.LabelFrame(self.window, text="过滤设置", padding=10)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 关键词输入
        keyword_frame = ttk.Frame(filter_frame)
        keyword_frame.pack(fill=tk.X, pady=2)
        ttk.Label(keyword_frame, text="关键词:", width=10).pack(side=tk.LEFT)
        self.keyword_var = tk.StringVar()
        self.keyword_entry = ttk.Entry(keyword_frame, textvariable=self.keyword_var)
        self.keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.keyword_entry.bind('<Return>', lambda e: self._find_next())
        # 添加查询按钮 - 逐个查找
        ttk.Button(keyword_frame, text="查询", command=self._find_next, width=8).pack(side=tk.LEFT, padx=2)
        
        # 过滤选项
        options_frame = ttk.Frame(filter_frame)
        options_frame.pack(fill=tk.X, pady=2)
        
        self.case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="区分大小写", 
                       variable=self.case_sensitive_var).pack(side=tk.LEFT, padx=5)
        
        self.use_regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="使用正则表达式", 
                       variable=self.use_regex_var).pack(side=tk.LEFT, padx=5)
        
        self.invert_match_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="反向匹配(排除)", 
                       variable=self.invert_match_var).pack(side=tk.LEFT, padx=5)
        
        # 过滤按钮
        btn_frame = ttk.Frame(filter_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="应用过滤", command=self._apply_filter).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="显示全部", command=self._show_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="导出结果", command=self._export_results).pack(side=tk.LEFT, padx=2)
        
        # 统计信息
        self.stats_var = tk.StringVar(value="总行数: 0 | 显示: 0")
        ttk.Label(btn_frame, textvariable=self.stats_var, foreground="blue").pack(side=tk.LEFT, padx=10)
        
        # 显示区域
        display_frame = ttk.LabelFrame(self.window, text="内容显示", padding=5)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建带行号的文本显示
        text_container = ttk.Frame(display_frame)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        # 行号显示
        self.line_numbers = tk.Text(text_container, width=6, padx=3, takefocus=0,
                                    border=0, background='#f0f0f0', state='disabled',
                                    wrap='none')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # 主文本显示区
        self.text_display = scrolledtext.ScrolledText(text_container, wrap=tk.NONE)
        self.text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置颜色标签
        self.text_display.tag_config("highlight", background="yellow")
        self.text_display.tag_config("current_match", background="orange")  # 当前匹配项用橙色
        self.text_display.tag_config("line_num", foreground="gray")
        
        # 同步滚动
        self.text_display.config(yscrollcommand=self._on_scroll)
        
        # 状态栏
        status_frame = ttk.Frame(self.window)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
    
    def _on_scroll(self, *args):
        """同步行号和文本的滚动"""
        self.line_numbers.yview_moveto(args[0])
        self.text_display.yview_moveto(args[0])
    
    def _open_file(self):
        """打开文件"""
        filetypes = [
            ("日志文件", "*.log"),
            ("文本文件", "*.txt"),
            ("所有文件", "*.*")
        ]
        
        # 设置默认目录为应用生成的logs文件夹
        default_dir = os.path.abspath(self.log_dir)
        if not os.path.exists(default_dir):
            # 如果logs目录不存在，使用当前工作目录
            default_dir = os.getcwd()
        
        filename = filedialog.askopenfilename(
            title="选择日志文件",
            filetypes=filetypes,
            initialdir=default_dir
        )
        
        if filename:
            self._load_file(filename)
            # 确保窗口在加载文件后保持在前台
            self.window.lift()
            self.window.focus_force()
    
    def _load_file(self, filename: str):
        """加载文件内容"""
        try:
            self.status_var.set(f"正在加载 {os.path.basename(filename)}...")
            self.window.update()
            
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(filename, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                messagebox.showerror("错误", "无法读取文件，不支持的编码格式")
                self.window.lift()
                self.window.focus_force()
                return
            
            # 存储文件信息
            self.current_file = filename
            self.all_lines = content.splitlines()
            
            # 显示文件名
            self.file_label.config(text=f"文件: {os.path.basename(filename)}", foreground="black")
            
            # 显示所有内容
            self._show_all()
            
            self.status_var.set(f"已加载 {len(self.all_lines)} 行")
            
            # 确保窗口在加载完成后保持激活状态
            self.window.lift()
            self.window.focus_force()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载文件失败: {str(e)}")
            self.window.lift()
            self.window.focus_force()
            self.status_var.set("加载失败")
    
    def _reload_file(self):
        """重新加载当前文件"""
        if self.current_file:
            self._load_file(self.current_file)
        else:
            messagebox.showinfo("提示", "没有打开的文件")
            self.window.lift()
            self.window.focus_force()
    
    def _find_next(self):
        """查找下一个匹配项（逐个查找）"""
        if not self.all_lines:
            messagebox.showinfo("提示", "请先打开一个文件")
            self.window.lift()
            self.window.focus_force()
            return
        
        keyword = self.keyword_var.get().strip()
        if not keyword:
            messagebox.showinfo("提示", "请输入关键词")
            self.window.lift()
            self.window.focus_force()
            return
        
        # 如果当前显示的不是全部内容（已应用过滤），先显示全部
        if len(self.filtered_lines) != len(self.all_lines):
            self._show_all()
        
        # 如果是新的搜索或关键词已改变，重新查找所有匹配
        if (self.current_match_index == -1 or
            len(self.search_matches) == 0 or
            keyword != self.last_search_keyword):
            self._build_search_matches(keyword)
            self.last_search_keyword = keyword
        
        if not self.search_matches:
            messagebox.showinfo("查询", "未找到匹配项")
            self.window.lift()
            self.window.focus_force()
            self.status_var.set("未找到匹配项")
            return
        
        # 移动到下一个匹配
        self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        self._highlight_current_match()
        
        # 更新状态
        total = len(self.search_matches)
        current = self.current_match_index + 1
        self.status_var.set(f"匹配 {current}/{total}")
    
    def _build_search_matches(self, keyword: str):
        """构建所有匹配位置列表"""
        self.search_matches = []
        self.current_match_index = -1
        
        try:
            if self.use_regex_var.get():
                # 使用正则表达式
                flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
                pattern = re.compile(keyword, flags)
                
                for line_idx, line in enumerate(self.all_lines):
                    for match in pattern.finditer(line):
                        self.search_matches.append((line_idx, match.start(), match.end()))
            else:
                # 普通文本匹配
                search_keyword = keyword if self.case_sensitive_var.get() else keyword.lower()
                
                for line_idx, line in enumerate(self.all_lines):
                    search_line = line if self.case_sensitive_var.get() else line.lower()
                    start = 0
                    while True:
                        pos = search_line.find(search_keyword, start)
                        if pos == -1:
                            break
                        self.search_matches.append((line_idx, pos, pos + len(keyword)))
                        start = pos + 1
        except re.error as e:
            messagebox.showerror("正则表达式错误", f"正则表达式语法错误: {str(e)}")
            self.window.lift()
            self.window.focus_force()
            self.search_matches = []
    
    def _highlight_current_match(self):
        """高亮显示当前匹配项"""
        if not self.search_matches or self.current_match_index < 0:
            return
        
        line_idx, start, end = self.search_matches[self.current_match_index]
        
        # 启用编辑以便添加标签
        self.text_display.config(state=tk.NORMAL)
        
        # 清除之前的高亮
        self.text_display.tag_remove("current_match", "1.0", tk.END)
        
        # 计算文本框中的位置（行号从1开始）
        text_line = line_idx + 1
        start_pos = f"{text_line}.{start}"
        end_pos = f"{text_line}.{end}"
        
        # 添加当前匹配高亮
        self.text_display.tag_add("current_match", start_pos, end_pos)
        
        # 滚动到当前匹配位置
        self.text_display.see(start_pos)
        
        # 禁用编辑
        self.text_display.config(state=tk.DISABLED)
    
    def _apply_filter(self):
        """应用过滤条件（全局过滤）"""
        if not self.all_lines:
            messagebox.showinfo("提示", "请先打开一个文件")
            self.window.lift()
            self.window.focus_force()
            return
        
        keyword = self.keyword_var.get().strip()
        if not keyword:
            messagebox.showinfo("提示", "请输入关键词")
            self.window.lift()
            self.window.focus_force()
            return
        
        self.status_var.set("正在过滤...")
        self.window.update()
        
        try:
            # 执行过滤
            self.filtered_lines = self._filter_lines(
                self.all_lines,
                keyword,
                self.case_sensitive_var.get(),
                self.use_regex_var.get(),
                self.invert_match_var.get()
            )
            
            # 显示过滤结果
            self._display_lines(self.filtered_lines, keyword)
            
            # 更新统计
            self._update_stats()
            
            self.status_var.set(f"过滤完成: 找到 {len(self.filtered_lines)} 行")
            
            # 重置查询状态
            self.search_matches = []
            self.current_match_index = -1
            self.last_search_keyword = ""
            
        except re.error as e:
            messagebox.showerror("正则表达式错误", f"正则表达式语法错误: {str(e)}")
            self.window.lift()
            self.window.focus_force()
            self.status_var.set("过滤失败")
        except Exception as e:
            messagebox.showerror("错误", f"过滤失败: {str(e)}")
            self.window.lift()
            self.window.focus_force()
            self.status_var.set("过滤失败")
    
    def _filter_lines(self, lines: List[str], keyword: str, 
                     case_sensitive: bool, use_regex: bool, 
                     invert_match: bool) -> List[tuple]:
        """
        过滤行
        返回: [(line_number, line_content), ...]
        """
        filtered = []
        
        if use_regex:
            # 使用正则表达式
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(keyword, flags)
            
            for i, line in enumerate(lines, 1):
                match = pattern.search(line)
                if (match and not invert_match) or (not match and invert_match):
                    filtered.append((i, line))
        else:
            # 普通文本匹配
            if not case_sensitive:
                keyword = keyword.lower()
            
            for i, line in enumerate(lines, 1):
                search_line = line if case_sensitive else line.lower()
                contains = keyword in search_line
                
                if (contains and not invert_match) or (not contains and invert_match):
                    filtered.append((i, line))
        
        return filtered
    
    def _show_all(self):
        """显示所有行"""
        if not self.all_lines:
            return
        
        self.filtered_lines = [(i, line) for i, line in enumerate(self.all_lines, 1)]
        self._display_lines(self.filtered_lines)
        self._update_stats()
        self.status_var.set(f"显示全部 {len(self.all_lines)} 行")
        
        # 重置查询状态
        self.search_matches = []
        self.current_match_index = -1
        self.last_search_keyword = ""
    
    def _display_lines(self, lines: List[tuple], highlight_keyword: str = None):
        """
        显示行内容
        lines: [(line_number, line_content), ...]
        """
        # 清空显示
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete('1.0', tk.END)
        
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete('1.0', tk.END)
        
        # 插入内容
        for line_num, content in lines:
            # 插入行号
            self.line_numbers.insert(tk.END, f"{line_num}\n")
            
            # 插入内容并高亮
            if highlight_keyword:
                if self.use_regex_var.get():
                    # 使用正则表达式高亮
                    self._insert_with_regex_highlight(content, highlight_keyword)
                else:
                    # 普通文本高亮
                    self._insert_with_highlight(content, highlight_keyword)
            else:
                self.text_display.insert(tk.END, content + '\n')
        
        # 禁用编辑
        self.text_display.config(state=tk.DISABLED)
        self.line_numbers.config(state=tk.DISABLED)
    
    def _insert_with_highlight(self, text: str, keyword: str):
        """插入文本并高亮关键词"""
        if not keyword:
            self.text_display.insert(tk.END, text + '\n')
            return
        
        # 处理大小写
        search_text = text if self.case_sensitive_var.get() else text.lower()
        search_keyword = keyword if self.case_sensitive_var.get() else keyword.lower()
        
        last_end = 0
        while True:
            start = search_text.find(search_keyword, last_end)
            if start == -1:
                break
            
            # 插入关键词之前的文本
            self.text_display.insert(tk.END, text[last_end:start])
            
            # 插入高亮的关键词
            end = start + len(keyword)
            self.text_display.insert(tk.END, text[start:end], "highlight")
            
            last_end = end
        
        # 插入剩余文本
        self.text_display.insert(tk.END, text[last_end:] + '\n')
    
    def _insert_with_regex_highlight(self, text: str, pattern: str):
        """使用正则表达式插入文本并高亮匹配部分"""
        if not pattern:
            self.text_display.insert(tk.END, text + '\n')
            return
        
        try:
            # 编译正则表达式
            flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
            regex = re.compile(pattern, flags)
            
            # 查找所有匹配
            matches = list(regex.finditer(text))
            
            if not matches:
                # 没有匹配，直接插入
                self.text_display.insert(tk.END, text + '\n')
                return
            
            # 有匹配，逐段插入并高亮
            last_end = 0
            for match in matches:
                start, end = match.span()
                
                # 插入匹配前的文本
                if start > last_end:
                    self.text_display.insert(tk.END, text[last_end:start])
                
                # 插入高亮的匹配文本
                self.text_display.insert(tk.END, text[start:end], "highlight")
                
                last_end = end
            
            # 插入剩余文本
            self.text_display.insert(tk.END, text[last_end:] + '\n')
            
        except re.error:
            # 正则表达式错误，直接插入文本不高亮
            self.text_display.insert(tk.END, text + '\n')
    
    def _update_stats(self):
        """更新统计信息"""
        total = len(self.all_lines)
        displayed = len(self.filtered_lines)
        self.stats_var.set(f"总行数: {total} | 显示: {displayed}")
    
    def _clear_display(self):
        """清除显示"""
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete('1.0', tk.END)
        self.text_display.config(state=tk.DISABLED)
        
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete('1.0', tk.END)
        self.line_numbers.config(state=tk.DISABLED)
        
        self.current_file = None
        self.all_lines = []
        self.filtered_lines = []
        self.file_label.config(text="未打开文件", foreground="gray")
        self._update_stats()
        self.status_var.set("已清除")
    
    def _export_results(self):
        """导出过滤结果"""
        if not self.filtered_lines:
            messagebox.showinfo("提示", "没有可导出的内容")
            self.window.lift()
            self.window.focus_force()
            return
        
        filename = filedialog.asksaveasfilename(
            title="导出过滤结果",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("日志文件", "*.log"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for line_num, content in self.filtered_lines:
                        f.write(f"{line_num}: {content}\n")
                
                messagebox.showinfo("成功", f"已导出 {len(self.filtered_lines)} 行到:\n{filename}")
                self.window.lift()
                self.window.focus_force()
                self.status_var.set(f"已导出到 {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")
                self.window.lift()
                self.window.focus_force()
    
    def run(self):
        """运行窗口（仅在独立模式下使用）"""
        self.window.mainloop()


def main():
    """独立运行日志过滤工具"""
    # 独立运行时，也使用logs目录作为默认目录
    app = LogFilterWindow(log_dir="logs")
    app.run()


if __name__ == "__main__":
    main()