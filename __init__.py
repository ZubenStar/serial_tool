"""多串口监控工具

一个功能强大的串口监控工具，支持：
- 同时监控多个串口
- 关键词过滤
- 正则表达式匹配
- 自动日志保存
- 图形界面和命令行两种使用方式
"""

from .serial_monitor import SerialMonitor, MultiSerialMonitor

__version__ = "1.0.0"
__all__ = ["SerialMonitor", "MultiSerialMonitor"]