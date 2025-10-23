"""
串口数据Dump功能使用示例

此示例演示如何使用dump功能保存原始二进制数据
适用于耳机数据等需要保存原始二进制流的场景
"""

from serial_monitor import MultiSerialMonitor
import time

def data_callback(port, timestamp, data, colored_log_entry=""):
    """数据接收回调函数"""
    print(f"[{timestamp}] [{port}] {data}")

def main():
    print("=" * 60)
    print("串口数据Dump功能示例")
    print("=" * 60)
    
    # 创建监控器
    monitor = MultiSerialMonitor(log_dir="logs")
    
    # 配置串口参数 (请根据实际情况修改)
    PORT = "COM3"  # 修改为你的串口
    BAUDRATE = 115200
    
    print(f"\n1. 添加串口监控: {PORT} @ {BAUDRATE} bps")
    
    # 添加串口监控（默认不启用dump）
    success = monitor.add_monitor(
        port=PORT,
        baudrate=BAUDRATE,
        callback=data_callback,
        enable_color=True
    )
    
    if not success:
        print(f"❌ 无法打开串口 {PORT}")
        print("\n可用串口列表:")
        for port in MultiSerialMonitor.list_available_ports():
            print(f"  - {port}")
        return
    
    print(f"✓ 串口 {PORT} 已启动")
    
    # 等待一段时间，让数据开始流入
    print("\n2. 等待2秒，接收普通数据...")
    time.sleep(2)
    
    # 开始dump数据
    print("\n3. 开始dump原始二进制数据...")
    if monitor.start_dump(PORT):
        print(f"✓ 开始dump {PORT} 的数据")
        print(f"   保存位置: dumps/{PORT}_*.bin")
    
    # 继续接收数据并dump
    print("\n4. 正在dump数据中，持续10秒...")
    print("   所有原始二进制数据将保存到 .bin 文件")
    
    for i in range(10):
        time.sleep(1)
        # 获取统计信息
        stats = monitor.get_all_stats()
        if PORT in stats:
            port_stats = stats[PORT]
            total_bytes = port_stats.get('total_bytes', 0)
            dumped_bytes = port_stats.get('dumped_bytes', 0)
            print(f"   [{i+1}/10] 总接收: {total_bytes} 字节, 已dump: {dumped_bytes} 字节")
    
    # 停止dump
    print("\n5. 停止dump...")
    if monitor.stop_dump(PORT):
        print(f"✓ 已停止dump {PORT}")
        
        # 显示最终统计
        stats = monitor.get_all_stats()
        if PORT in stats:
            port_stats = stats[PORT]
            print(f"\n最终统计:")
            print(f"  - 总接收字节: {port_stats.get('total_bytes', 0)}")
            print(f"  - Dump字节: {port_stats.get('dumped_bytes', 0)}")
            print(f"  - Dump文件: {port_stats.get('dump_file', 'N/A')}")
    
    # 继续接收数据但不dump
    print("\n6. 继续接收数据（不dump），持续3秒...")
    time.sleep(3)
    
    # 停止监控
    print("\n7. 停止串口监控...")
    monitor.stop_all()
    print("✓ 所有串口已停止")
    
    print("\n" + "=" * 60)
    print("示例完成！")
    print(f"请检查 dumps/ 目录查看保存的二进制文件")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()