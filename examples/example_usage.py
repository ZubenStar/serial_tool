"""串口监控工具使用示例"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from serial_monitor import MultiSerialMonitor, SerialMonitor
import time


def example1_basic():
    """示例1: 基础使用 - 监控单个串口"""
    print("=" * 60)
    print("示例1: 基础使用 - 监控单个串口")
    print("=" * 60)
    
    def callback(port, timestamp, data):
        print(f"收到数据 [{port}]: {data}")
    
    monitor = SerialMonitor(
        port="COM1",  # 根据实际情况修改
        baudrate=9600,
        callback=callback
    )
    
    if monitor.start():
        print("串口已启动，监控10秒...")
        time.sleep(10)
        monitor.stop()
        print(f"日志已保存到: {monitor.log_file}")
    else:
        print("启动失败，请检查串口是否可用")


def example2_multi_ports():
    """示例2: 同时监控多个串口"""
    print("\n" + "=" * 60)
    print("示例2: 同时监控多个串口")
    print("=" * 60)
    
    def callback(port, timestamp, data):
        print(f"[{timestamp}] {port}: {data}")
    
    monitor = MultiSerialMonitor(log_dir="logs")
    
    # 添加多个串口
    ports = ["COM1", "COM2", "COM3"]  # 根据实际情况修改
    for port in ports:
        monitor.add_monitor(
            port=port,
            baudrate=115200,
            callback=callback
        )
    
    print(f"已启动 {len(monitor.get_active_ports())} 个串口")
    print("监控10秒...")
    time.sleep(10)
    
    monitor.stop_all()
    print("已停止所有串口")


def example3_keyword_filter():
    """示例3: 使用关键词过滤"""
    print("\n" + "=" * 60)
    print("示例3: 使用关键词过滤")
    print("=" * 60)
    
    def callback(port, timestamp, data):
        print(f"匹配到关键词 [{port}]: {data}")
    
    monitor = MultiSerialMonitor(log_dir="logs")
    
    # 只记录包含这些关键词的数据
    keywords = ["ERROR", "WARNING", "CRITICAL", "Temperature"]
    
    monitor.add_monitor(
        port="COM1",  # 根据实际情况修改
        baudrate=9600,
        keywords=keywords,
        callback=callback
    )
    
    print(f"关键词过滤: {keywords}")
    print("只会显示和记录包含这些关键词的数据")
    print("监控10秒...")
    time.sleep(10)
    
    monitor.stop_all()


def example4_regex_filter():
    """示例4: 使用正则表达式过滤"""
    print("\n" + "=" * 60)
    print("示例4: 使用正则表达式过滤")
    print("=" * 60)
    
    def callback(port, timestamp, data):
        print(f"匹配到模式 [{port}]: {data}")
    
    monitor = MultiSerialMonitor(log_dir="logs")
    
    # 正则表达式模式
    patterns = [
        r"Temperature:\s*[\d.]+",  # 匹配温度数据
        r"0x[0-9A-Fa-f]+",         # 匹配十六进制数
        r"\d{4}-\d{2}-\d{2}",      # 匹配日期格式
    ]
    
    monitor.add_monitor(
        port="COM1",  # 根据实际情况修改
        baudrate=9600,
        regex_patterns=patterns,
        callback=callback
    )
    
    print(f"正则表达式过滤: {patterns}")
    print("只会显示和记录匹配这些模式的数据")
    print("监控10秒...")
    time.sleep(10)
    
    monitor.stop_all()


def example5_send_data():
    """示例5: 发送数据到串口"""
    print("\n" + "=" * 60)
    print("示例5: 发送数据到串口")
    print("=" * 60)
    
    def callback(port, timestamp, data):
        print(f"收到响应 [{port}]: {data}")
    
    monitor = MultiSerialMonitor(log_dir="logs")
    
    monitor.add_monitor(
        port="COM1",  # 根据实际情况修改
        baudrate=9600,
        callback=callback
    )
    
    print("发送命令到串口...")
    
    # 发送一些命令
    commands = [
        "AT\r\n",
        "AT+VERSION?\r\n",
        "AT+STATUS?\r\n",
    ]
    
    for cmd in commands:
        print(f"发送: {cmd.strip()}")
        monitor.send("COM1", cmd)
        time.sleep(1)
    
    print("等待响应...")
    time.sleep(5)
    
    monitor.stop_all()


def example6_combined_filters():
    """示例6: 组合使用关键词和正则表达式"""
    print("\n" + "=" * 60)
    print("示例6: 组合使用关键词和正则表达式")
    print("=" * 60)
    
    def callback(port, timestamp, data):
        print(f"✓ [{port}] {data}")
    
    monitor = MultiSerialMonitor(log_dir="logs")
    
    # 同时使用关键词和正则表达式
    # 只要满足其中一个条件就会被记录
    keywords = ["ERROR", "WARNING"]
    patterns = [r"Temperature:\s*[\d.]+", r"Humidity:\s*[\d.]+"]
    
    monitor.add_monitor(
        port="COM1",  # 根据实际情况修改
        baudrate=9600,
        keywords=keywords,
        regex_patterns=patterns,
        callback=callback
    )
    
    print(f"关键词: {keywords}")
    print(f"正则表达式: {patterns}")
    print("满足任一条件的数据都会被记录")
    print("监控10秒...")
    time.sleep(10)
    
    monitor.stop_all()


def example7_list_ports():
    """示例7: 列出可用串口"""
    print("\n" + "=" * 60)
    print("示例7: 列出可用串口")
    print("=" * 60)
    
    ports = MultiSerialMonitor.list_available_ports()
    
    if ports:
        print(f"找到 {len(ports)} 个可用串口:")
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port}")
    else:
        print("未找到可用串口")


def main():
    """主函数 - 选择要运行的示例"""
    print("\n串口监控工具 - 使用示例")
    print("=" * 60)
    print("请选择要运行的示例:")
    print("1. 基础使用 - 监控单个串口")
    print("2. 同时监控多个串口")
    print("3. 使用关键词过滤")
    print("4. 使用正则表达式过滤")
    print("5. 发送数据到串口")
    print("6. 组合使用关键词和正则表达式")
    print("7. 列出可用串口")
    print("0. 退出")
    print("=" * 60)
    
    try:
        choice = input("\n请输入选项 (0-7): ").strip()
        
        if choice == "1":
            example1_basic()
        elif choice == "2":
            example2_multi_ports()
        elif choice == "3":
            example3_keyword_filter()
        elif choice == "4":
            example4_regex_filter()
        elif choice == "5":
            example5_send_data()
        elif choice == "6":
            example6_combined_filters()
        elif choice == "7":
            example7_list_ports()
        elif choice == "0":
            print("退出")
        else:
            print("无效选项")
    
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n错误: {e}")
        print("请确保:")
        print("1. 已安装 pyserial (pip install pyserial)")
        print("2. 串口名称正确 (Windows: COM1, Linux: /dev/ttyUSB0)")
        print("3. 串口未被其他程序占用")


if __name__ == "__main__":
    main()