"""命令行版本的串口监控工具"""
import argparse
import sys
import time
from serial_monitor import MultiSerialMonitor


def print_header():
    """打印程序头部信息"""
    print("=" * 60)
    print("         多串口监控工具 - 命令行版本")
    print("=" * 60)
    print()


def data_callback(port: str, timestamp: str, data: str, colored_log_entry: str = ""):
    """数据接收回调函数"""
    # 优先使用带颜色的日志条目
    if colored_log_entry:
        print(colored_log_entry)
    else:
        print(f"[{timestamp}] [{port}] {data}")


def main():
    parser = argparse.ArgumentParser(description='多串口监控工具')
    parser.add_argument('--ports', '-p', nargs='+',
                       help='串口列表，例如: COM1 COM2 或 /dev/ttyUSB0')
    parser.add_argument('--baudrate', '-b', type=int, default=9600,
                       help='波特率 (默认: 9600)')
    parser.add_argument('--keywords', '-k', nargs='*', default=[],
                       help='关键词过滤列表')
    parser.add_argument('--regex', '-r', nargs='*', default=[],
                       help='正则表达式过滤列表')
    parser.add_argument('--log-dir', '-l', default='logs',
                       help='日志保存目录 (默认: logs)')
    parser.add_argument('--list-ports', action='store_true',
                       help='列出可用串口')
    
    args = parser.parse_args()
    
    # 如果不是列出串口，则ports参数必需
    if not args.list_ports and not args.ports:
        parser.error("需要提供 --ports 参数，或使用 --list-ports 列出可用串口")
    
    # 列出可用串口
    if args.list_ports:
        print_header()
        print("可用串口:")
        ports = MultiSerialMonitor.list_available_ports()
        if ports:
            for i, port in enumerate(ports, 1):
                print(f"  {i}. {port}")
        else:
            print("  未找到可用串口")
        print()
        return
    
    print_header()
    
    # 创建监控器
    monitor = MultiSerialMonitor(log_dir=args.log_dir)
    
    # 显示配置信息
    print("配置信息:")
    print(f"  波特率: {args.baudrate}")
    print(f"  日志目录: {args.log_dir}")
    if args.keywords:
        print(f"  关键词过滤: {', '.join(args.keywords)}")
    if args.regex:
        print(f"  正则表达式: {', '.join(args.regex)}")
    print()
    
    # 启动串口监控
    print("正在启动串口监控...")
    success_count = 0
    for port in args.ports:
        if monitor.add_monitor(
            port=port,
            baudrate=args.baudrate,
            keywords=args.keywords if args.keywords else None,
            regex_patterns=args.regex if args.regex else None,
            callback=data_callback
        ):
            success_count += 1
        else:
            print(f"警告: 无法启动串口 {port}")
    
    if success_count == 0:
        print("错误: 没有成功启动任何串口")
        sys.exit(1)
    
    print(f"\n成功启动 {success_count} 个串口")
    print("=" * 60)
    print("开始监控... (按 Ctrl+C 停止)")
    print("=" * 60)
    print()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n正在停止...")
        monitor.stop_all()
        print("已停止所有串口监控")
        print(f"日志已保存到: {args.log_dir}/")


if __name__ == "__main__":
    main()