"""
批量串口快速启动示例

演示如何使用批量启动功能快速打开多个串口
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from serial_monitor import MultiSerialMonitor
import time

def example_callback(port, timestamp, data, colored_log_entry=""):
    """回调函数示例"""
    print(f"[{timestamp}] {port}: {data}")

def main():
    print("=" * 60)
    print("批量串口快速启动示例")
    print("=" * 60)
    
    monitor = MultiSerialMonitor(log_dir="logs")
    
    # 配置要启动的多个串口
    # 请根据你的实际串口修改以下配置
    batch_configs = [
        {
            'port': 'COM3',  # 修改为你的实际串口
            'baudrate': 115200,
            'keywords': [],
            'regex_patterns': [],
            'callback': example_callback,
            'enable_color': True
        },
        {
            'port': 'COM4',  # 修改为你的实际串口
            'baudrate': 115200,
            'keywords': [],
            'regex_patterns': [],
            'callback': example_callback,
            'enable_color': True
        },
        {
            'port': 'COM5',  # 修改为你的实际串口
            'baudrate': 9600,
            'keywords': [],
            'regex_patterns': [],
            'callback': example_callback,
            'enable_color': True
        }
    ]
    
    print("\n方法1: 传统串行启动（逐个打开）")
    print("-" * 60)
    start_time = time.time()
    
    # 传统方式：逐个启动（较慢）
    # for config in batch_configs:
    #     monitor.add_monitor(**config)
    
    # serial_duration = time.time() - start_time
    # print(f"串行启动耗时: {serial_duration:.2f} 秒")
    
    print("\n方法2: 并行快速启动（同时打开多个）")
    print("-" * 60)
    start_time = time.time()
    
    # 新方式：并行启动（更快！）
    results = monitor.add_monitors_parallel(batch_configs)
    
    parallel_duration = time.time() - start_time
    print(f"并行启动耗时: {parallel_duration:.2f} 秒")
    
    # 显示启动结果
    print("\n启动结果:")
    print("-" * 60)
    success_count = 0
    for port, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {port}: {status}")
        if success:
            success_count += 1
    
    print(f"\n总计: 成功 {success_count}/{len(batch_configs)} 个串口")
    
    if success_count > 0:
        print("\n活动串口列表:")
        print("-" * 60)
        for port in monitor.get_active_ports():
            print(f"  - {port}")
        
        print("\n串口监控运行中... (按 Ctrl+C 停止)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n正在停止所有串口...")
    
    monitor.stop_all()
    print("所有串口已停止")

if __name__ == "__main__":
    # 首先列出可用串口
    print("系统可用串口:")
    available_ports = MultiSerialMonitor.list_available_ports()
    if available_ports:
        for port in available_ports:
            print(f"  - {port}")
    else:
        print("  未找到可用串口")
    
    print("\n提示: 请修改 batch_configs 中的串口号为你的实际串口")
    print("然后运行此脚本\n")
    
    # 取消下面的注释来运行示例
    # main()