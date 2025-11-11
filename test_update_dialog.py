"""
测试更新对话框显示
直接模拟有新版本的情况
"""
import tkinter as tk
from tkinter import ttk, scrolledtext


def show_update_dialog():
    """显示更新对话框测试"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 模拟更新信息
    update_info = {
        'version': '99.0.0',
        'name': '重大更新 v99.0.0',
        'description': '这是一个测试更新\n\n更新内容:\n- 新功能1\n- 新功能2\n- Bug修复',
        'download_url': 'https://github.com/test/serial_tool/releases/tag/v99.0.0',
        'assets': [
            {
                'name': 'serial_tool_v99.0.0.exe',
                'download_url': 'https://example.com/serial_tool.exe',
                'size': 15728640
            }
        ]
    }
    
    summary = f"""发现新版本: {update_info['version']}
版本名称: {update_info['name']}

当前版本: 3.1.0

更新内容:
{update_info['description']}

下载地址: {update_info['download_url']}

可用下载:
  • serial_tool_v99.0.0.exe (15.00 MB)"""
    
    # 创建对话框
    dialog = tk.Toplevel(root)
    dialog.title("发现新版本 🎉")
    dialog.geometry("650x550")
    dialog.resizable(False, False)
    
    # 居中显示
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (650 // 2)
    y = (dialog.winfo_screenheight() // 2) - (550 // 2)
    dialog.geometry(f"650x550+{x}+{y}")
    
    # 摘要信息
    text_frame = ttk.Frame(dialog, padding=15)
    text_frame.pack(fill=tk.BOTH, expand=False)
    
    text_widget = scrolledtext.ScrolledText(
        text_frame,
        wrap=tk.WORD,
        font=('Microsoft YaHei UI', 10),
        relief=tk.FLAT,
        padx=10,
        pady=10,
        height=18  # 增加高度以显示更多内容
    )
    text_widget.pack(fill=tk.BOTH, expand=False)
    text_widget.insert('1.0', summary)
    text_widget.config(state=tk.DISABLED)
    
    # 分隔线
    separator = ttk.Separator(dialog, orient='horizontal')
    separator.pack(fill=tk.X, padx=15, pady=10)
    
    # 提示标签
    tip_label = ttk.Label(
        dialog, 
        text="💡 选择更新方式：",
        font=('Microsoft YaHei UI', 10, 'bold')
    )
    tip_label.pack(pady=(5, 10))
    
    # 按钮区域
    btn_frame = ttk.Frame(dialog, padding=15)
    btn_frame.pack(fill=tk.X)
    
    def on_download():
        print("用户选择：自动下载")
        dialog.destroy()
        root.quit()
    
    def on_browser():
        print("用户选择：浏览器打开")
        dialog.destroy()
        root.quit()
    
    def on_cancel():
        print("用户选择：稍后提醒")
        dialog.destroy()
        root.quit()
    
    # 按钮样式 - 使用较大的按钮
    download_btn = ttk.Button(btn_frame, text="🔽 自动下载", command=on_download)
    download_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    
    browser_btn = ttk.Button(btn_frame, text="🌐 浏览器打开", command=on_browser)
    browser_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    
    cancel_btn = ttk.Button(btn_frame, text="⏰ 稍后提醒", command=on_cancel)
    cancel_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    
    # 添加说明文字
    desc_frame = ttk.Frame(dialog, padding=(15, 5, 15, 10))
    desc_frame.pack(fill=tk.X)
    
    desc_text = "• 自动下载：后台下载更新文件到本地\n• 浏览器打开：在浏览器中查看和下载\n• 稍后提醒：关闭此窗口，稍后再更新"
    desc_label = ttk.Label(
        desc_frame,
        text=desc_text,
        font=('Microsoft YaHei UI', 9),
        foreground='#858585',
        justify=tk.LEFT
    )
    desc_label.pack(anchor=tk.W)
    
    print("=" * 60)
    print("更新对话框测试")
    print("=" * 60)
    print("如果你看到一个包含三个按钮的对话框，说明界面正常")
    print("三个按钮应该是：")
    print("  1. 🔽 自动下载")
    print("  2. 🌐 浏览器打开")
    print("  3. ⏰ 稍后提醒")
    print("=" * 60)
    
    root.mainloop()


if __name__ == "__main__":
    show_update_dialog()