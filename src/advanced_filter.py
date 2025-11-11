"""
高级过滤模块
支持逻辑组合过滤、时间范围过滤、数据长度过滤等
"""
import tkinter as tk
from tkinter import ttk, messagebox
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable


class FilterRule:
    """过滤规则类"""
    
    def __init__(self, rule_type: str, value: str, case_sensitive: bool = False):
        self.rule_type = rule_type  # 'keyword', 'regex', 'length', 'time'
        self.value = value
        self.case_sensitive = case_sensitive
        self.enabled = True
    
    def matches(self, data: str, timestamp: str = None) -> bool:
        """检查数据是否匹配规则"""
        if not self.enabled:
            return True
        
        if self.rule_type == 'keyword':
            search_data = data if self.case_sensitive else data.lower()
            search_value = self.value if self.case_sensitive else self.value.lower()
            return search_value in search_data
        
        elif self.rule_type == 'regex':
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(self.value, flags)
                return pattern.search(data) is not None
            except re.error:
                return False
        
        elif self.rule_type == 'length':
            try:
                min_len, max_len = map(int, self.value.split('-'))
                return min_len <= len(data) <= max_len
            except:
                return True
        
        elif self.rule_type == 'time' and timestamp:
            # 时间范围过滤
            try:
                data_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                start_time, end_time = self.value.split(',')
                start = datetime.strptime(start_time.strip(), "%Y-%m-%d %H:%M:%S")
                end = datetime.strptime(end_time.strip(), "%Y-%m-%d %H:%M:%S")
                return start <= data_time <= end
            except:
                return True
        
        return True


class FilterGroup:
    """过滤规则组（支持AND/OR逻辑）"""
    
    def __init__(self, logic: str = 'AND'):
        self.logic = logic  # 'AND' or 'OR'
        self.rules: List[FilterRule] = []
        self.enabled = True
    
    def add_rule(self, rule: FilterRule):
        """添加规则"""
        self.rules.append(rule)
    
    def remove_rule(self, index: int):
        """移除规则"""
        if 0 <= index < len(self.rules):
            self.rules.pop(index)
    
    def matches(self, data: str, timestamp: str = None) -> bool:
        """检查数据是否匹配规则组"""
        if not self.enabled or not self.rules:
            return True
        
        if self.logic == 'AND':
            return all(rule.matches(data, timestamp) for rule in self.rules)
        else:  # OR
            return any(rule.matches(data, timestamp) for rule in self.rules)


class AdvancedFilterWindow:
    """高级过滤窗口"""
    
    def __init__(self, parent, callback: Optional[Callable] = None):
        self.parent = parent
        self.callback = callback
        self.filter_groups: List[FilterGroup] = []
        self.window = None
        
        # 过滤模板
        self.templates: Dict[str, List[FilterGroup]] = {}
        
    def open_filter_window(self):
        """打开高级过滤窗口"""
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("高级过滤器")
        self.window.geometry("800x600")
        
        # 创建主界面
        self._create_widgets()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="高级过滤器配置", font=("TkDefaultFont", 12, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(toolbar, text="新建规则组", command=self._add_filter_group).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="保存模板", command=self._save_template).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="加载模板", command=self._load_template).pack(side=tk.RIGHT, padx=2)
        
        # 规则组列表区域
        list_frame = ttk.LabelFrame(self.window, text="过滤规则组", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建滚动区域
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.rules_container = ttk.Frame(canvas)
        
        self.rules_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.rules_container, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 底部按钮区
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="应用过滤", command=self._apply_filter).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="清除所有", command=self._clear_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="测试过滤", command=self._test_filter).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="关闭", command=self.window.destroy).pack(side=tk.RIGHT, padx=2)
    
    def _add_filter_group(self):
        """添加新的过滤规则组"""
        group = FilterGroup()
        self.filter_groups.append(group)
        
        # 创建规则组UI
        group_frame = ttk.LabelFrame(self.rules_container, text=f"规则组 {len(self.filter_groups)}", padding=10)
        group_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 逻辑选择
        logic_frame = ttk.Frame(group_frame)
        logic_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(logic_frame, text="逻辑:").pack(side=tk.LEFT)
        logic_var = tk.StringVar(value="AND")
        ttk.Radiobutton(logic_frame, text="AND (全部满足)", variable=logic_var, value="AND").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(logic_frame, text="OR (任意满足)", variable=logic_var, value="OR").pack(side=tk.LEFT, padx=5)
        
        # 规则列表
        rules_list_frame = ttk.Frame(group_frame)
        rules_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 添加规则按钮
        add_rule_frame = ttk.Frame(group_frame)
        add_rule_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(add_rule_frame, text="+ 添加规则", 
                  command=lambda: self._add_rule_to_group(group, rules_list_frame)).pack(side=tk.LEFT, padx=2)
        ttk.Button(add_rule_frame, text="删除规则组", 
                  command=lambda: self._remove_group(group, group_frame)).pack(side=tk.RIGHT, padx=2)
    
    def _add_rule_to_group(self, group: FilterGroup, parent_frame):
        """添加规则到规则组"""
        rule_frame = ttk.Frame(parent_frame)
        rule_frame.pack(fill=tk.X, pady=2)
        
        # 规则类型选择
        ttk.Label(rule_frame, text="类型:").pack(side=tk.LEFT)
        rule_type_var = tk.StringVar(value="keyword")
        rule_type_combo = ttk.Combobox(rule_frame, textvariable=rule_type_var, 
                                       values=["keyword", "regex", "length", "time"],
                                       state="readonly", width=10)
        rule_type_combo.pack(side=tk.LEFT, padx=5)
        
        # 规则值输入
        ttk.Label(rule_frame, text="值:").pack(side=tk.LEFT)
        value_var = tk.StringVar()
        value_entry = ttk.Entry(rule_frame, textvariable=value_var, width=30)
        value_entry.pack(side=tk.LEFT, padx=5)
        
        # 区分大小写
        case_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(rule_frame, text="区分大小写", variable=case_var).pack(side=tk.LEFT, padx=5)
        
        # 删除按钮
        def remove_rule():
            rule_frame.destroy()
            # TODO: 从group中移除对应的rule
        
        ttk.Button(rule_frame, text="删除", command=remove_rule).pack(side=tk.RIGHT, padx=2)
        
        # 创建规则对象
        rule = FilterRule(rule_type_var.get(), value_var.get(), case_var.get())
        group.add_rule(rule)
    
    def _remove_group(self, group: FilterGroup, frame):
        """删除规则组"""
        if group in self.filter_groups:
            self.filter_groups.remove(group)
        frame.destroy()
    
    def _apply_filter(self):
        """应用过滤器"""
        if self.callback:
            self.callback(self.filter_groups)
        messagebox.showinfo("成功", "过滤器已应用")
    
    def _clear_all(self):
        """清除所有规则"""
        self.filter_groups.clear()
        for widget in self.rules_container.winfo_children():
            widget.destroy()
        messagebox.showinfo("完成", "已清除所有规则")
    
    def _test_filter(self):
        """测试过滤器"""
        # 打开测试对话框
        test_window = tk.Toplevel(self.window)
        test_window.title("测试过滤器")
        test_window.geometry("600x400")
        
        # 输入区
        input_frame = ttk.LabelFrame(test_window, text="测试数据", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        test_text = tk.Text(input_frame, height=10, wrap=tk.WORD)
        test_text.pack(fill=tk.BOTH, expand=True)
        
        # 结果区
        result_frame = ttk.LabelFrame(test_window, text="过滤结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        result_text = tk.Text(result_frame, height=10, wrap=tk.WORD)
        result_text.pack(fill=tk.BOTH, expand=True)
        
        # 测试按钮
        def run_test():
            test_data = test_text.get("1.0", tk.END).strip().split('\n')
            result_text.delete("1.0", tk.END)
            
            matched = 0
            for line in test_data:
                if self._check_all_groups(line):
                    result_text.insert(tk.END, line + "\n")
                    matched += 1
            
            result_text.insert(tk.END, f"\n匹配: {matched}/{len(test_data)} 行")
        
        ttk.Button(test_window, text="运行测试", command=run_test).pack(pady=5)
    
    def _check_all_groups(self, data: str, timestamp: str = None) -> bool:
        """检查数据是否通过所有规则组"""
        if not self.filter_groups:
            return True
        
        # 所有规则组都必须匹配（AND关系）
        return all(group.matches(data, timestamp) for group in self.filter_groups)
    
    def _save_template(self):
        """保存过滤模板"""
        from tkinter import simpledialog
        
        name = simpledialog.askstring("保存模板", "请输入模板名称:", parent=self.window)
        if name:
            self.templates[name] = self.filter_groups.copy()
            messagebox.showinfo("成功", f"已保存模板: {name}")
    
    def _load_template(self):
        """加载过滤模板"""
        if not self.templates:
            messagebox.showinfo("提示", "没有保存的模板")
            return
        
        # 创建选择对话框
        dialog = tk.Toplevel(self.window)
        dialog.title("加载模板")
        dialog.geometry("300x200")
        
        ttk.Label(dialog, text="选择要加载的模板:").pack(pady=10)
        
        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for name in self.templates.keys():
            listbox.insert(tk.END, name)
        
        def load_selected():
            selection = listbox.curselection()
            if selection:
                name = listbox.get(selection[0])
                self.filter_groups = self.templates[name].copy()
                dialog.destroy()
                self._refresh_display()
                messagebox.showinfo("成功", f"已加载模板: {name}")
        
        ttk.Button(dialog, text="加载", command=load_selected).pack(pady=5)
    
    def _refresh_display(self):
        """刷新显示"""
        # 清除现有显示
        for widget in self.rules_container.winfo_children():
            widget.destroy()
        
        # 重新创建规则组显示
        for group in self.filter_groups:
            self._add_filter_group()


class ColorMarkingRule:
    """颜色标记规则"""
    
    def __init__(self, pattern: str, color: str, pattern_type: str = 'keyword'):
        self.pattern = pattern
        self.color = color
        self.pattern_type = pattern_type  # 'keyword' or 'regex'
        self.enabled = True
    
    def matches(self, text: str) -> bool:
        """检查文本是否匹配规则"""
        if not self.enabled:
            return False
        
        if self.pattern_type == 'keyword':
            return self.pattern in text
        else:  # regex
            try:
                return re.search(self.pattern, text) is not None
            except re.error:
                return False


class ColorMarkingManager:
    """颜色标记管理器"""
    
    def __init__(self):
        self.rules: List[ColorMarkingRule] = []
        self.default_colors = [
            '#FF5555',  # 红色 - 错误
            '#FFAA00',  # 橙色 - 警告
            '#55FF55',  # 绿色 - 成功
            '#5555FF',  # 蓝色 - 信息
            '#FF55FF',  # 紫色 - 调试
        ]
    
    def add_rule(self, pattern: str, color: str, pattern_type: str = 'keyword'):
        """添加颜色标记规则"""
        rule = ColorMarkingRule(pattern, color, pattern_type)
        self.rules.append(rule)
    
    def remove_rule(self, index: int):
        """删除规则"""
        if 0 <= index < len(self.rules):
            self.rules.pop(index)
    
    def get_color_for_text(self, text: str) -> Optional[str]:
        """获取文本应该使用的颜色"""
        for rule in self.rules:
            if rule.matches(text):
                return rule.color
        return None
    
    def save_rules(self, filepath: str):
        """保存规则到文件"""
        import json
        rules_data = [
            {
                'pattern': rule.pattern,
                'color': rule.color,
                'pattern_type': rule.pattern_type,
                'enabled': rule.enabled
            }
            for rule in self.rules
        ]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, ensure_ascii=False, indent=2)
    
    def load_rules(self, filepath: str):
        """从文件加载规则"""
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            self.rules.clear()
            for data in rules_data:
                rule = ColorMarkingRule(
                    data['pattern'],
                    data['color'],
                    data.get('pattern_type', 'keyword')
                )
                rule.enabled = data.get('enabled', True)
                self.rules.append(rule)
        except Exception as e:
            print(f"加载颜色标记规则失败: {e}")