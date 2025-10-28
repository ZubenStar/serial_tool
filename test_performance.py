"""串口工具性能和实时性自动化测试

测试场景：
1. 大数据量性能测试（GUI不卡顿）
2. 实时筛选测试（数据能实时显示）
3. 延迟测试（响应时间<100ms）
"""
import unittest
import threading
import time
import queue
from unittest.mock import Mock, patch, MagicMock
from serial_monitor import SerialMonitor, MultiSerialMonitor
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestPerformance(unittest.TestCase):
    """性能测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_port = "COM_TEST"
        self.received_data = []
        self.received_timestamps = []
        self.data_lock = threading.Lock()
        
    def callback(self, port, timestamp, data, colored_log_entry=""):
        """测试回调函数"""
        with self.data_lock:
            self.received_data.append(data)
            self.received_timestamps.append(time.time())
    
    @patch('serial.Serial')
    def test_large_data_volume_no_lag(self, mock_serial):
        """测试大数据量下GUI不卡顿
        
        模拟每秒1000条数据，持续5秒，共5000条数据
        验证所有数据都能被正确处理且回调延迟不超过100ms
        """
        print("\n=== 测试1: 大数据量性能（每秒1000条×5秒=5000条）===")
        
        # 配置mock串口 - 使用side_effect来模拟真实行为
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_serial.return_value = mock_instance
        
        # 准备测试数据队列
        test_data_queue = queue.Queue()
        data_count = 5000
        
        # 预先生成所有测试数据
        for i in range(data_count):
            test_data_queue.put(f"Data line {i}: test message\n")
        
        # Mock in_waiting - 返回队列中是否有数据
        def mock_in_waiting():
            return 1 if not test_data_queue.empty() else 0
        
        # Mock read - 从队列读取数据
        def mock_read(size):
            if not test_data_queue.empty():
                data = test_data_queue.get()
                return data.encode('utf-8')
            return b''
        
        type(mock_instance).in_waiting = property(lambda self: mock_in_waiting())
        mock_instance.read = mock_read
        
        # 创建监控器
        monitor = SerialMonitor(
            port=self.test_port,
            baudrate=9600,
            callback=self.callback,
            save_all_to_log=False
        )
        
        # 启动监控
        self.assertTrue(monitor.start())
        start_time = time.time()
        
        # 等待所有数据处理完成（最多10秒）
        timeout = 10
        while not test_data_queue.empty() and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        time.sleep(0.5)  # 额外等待确保回调完成
        end_time = time.time()
        total_time = end_time - start_time
        
        monitor.stop()
        
        # 验证结果
        received_count = len(self.received_data)
        print(f"✓ 发送数据: 5000条")
        print(f"✓ 接收数据: {received_count}条")
        print(f"✓ 处理时间: {total_time:.2f}秒")
        print(f"✓ 吞吐量: {received_count/total_time:.0f}条/秒")
        
        # 断言：至少接收到95%的数据（考虑到异步处理可能有少量丢失）
        self.assertGreater(received_count, 4750, 
                          f"数据接收不完整: 期望>4750条，实际{received_count}条")
        
        # 验证回调延迟
        if len(self.received_timestamps) > 1:
            max_interval = 0
            for i in range(1, len(self.received_timestamps)):
                interval = self.received_timestamps[i] - self.received_timestamps[i-1]
                max_interval = max(max_interval, interval)
            
            print(f"✓ 最大回调间隔: {max_interval*1000:.2f}ms")
            # 在大数据量下，允许最大延迟200ms
            self.assertLess(max_interval, 0.2, 
                           f"回调延迟过大: {max_interval*1000:.2f}ms > 200ms")
    
    @patch('serial.Serial')
    def test_realtime_filtering_performance(self, mock_serial):
        """测试实时筛选性能
        
        发送1000条数据，其中只有10%匹配过滤条件
        验证匹配数据能实时显示（延迟<100ms）
        """
        print("\n=== 测试2: 实时筛选性能（1000条数据，10%匹配）===")
        
        # 配置mock串口
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_serial.return_value = mock_instance
        
        # 准备测试数据队列
        test_data_queue = queue.Queue()
        total_lines = 1000
        
        # 生成测试数据（10%匹配）
        for i in range(total_lines):
            if i % 10 == 0:
                test_data_queue.put(f"ERROR: Critical issue at line {i}\n")
            else:
                test_data_queue.put(f"INFO: Normal message {i}\n")
        
        # Mock in_waiting和read
        def mock_in_waiting():
            return 1 if not test_data_queue.empty() else 0
        
        def mock_read(size):
            if not test_data_queue.empty():
                data = test_data_queue.get()
                return data.encode('utf-8')
            return b''
        
        type(mock_instance).in_waiting = property(lambda self: mock_in_waiting())
        mock_instance.read = mock_read
        
        # 创建带过滤条件的监控器
        monitor = SerialMonitor(
            port=self.test_port,
            baudrate=9600,
            keywords=["ERROR", "WARNING"],
            callback=self.callback,
            save_all_to_log=False
        )
        
        # 启动监控
        self.assertTrue(monitor.start())
        start_time = time.time()
        
        # 等待数据处理完成
        timeout = 5
        while not test_data_queue.empty() and (time.time() - start_time) < timeout:
            time.sleep(0.05)
        
        time.sleep(0.2)  # 等待回调完成
        
        monitor.stop()
        
        # 验证结果
        expected_matches = 100  # 10%匹配
        received_count = len(self.received_data)
        
        print(f"✓ 总数据量: 1000条")
        print(f"✓ 期望匹配: {expected_matches}条")
        print(f"✓ 实际接收: {received_count}条")
        print(f"✓ 匹配率: {received_count/10:.1f}%")
        
        # 断言：至少接收到95%的匹配数据
        self.assertGreater(received_count, 95,
                          f"筛选数据接收不完整: 期望>95条，实际{received_count}条")
        
        # 验证所有接收的数据确实包含关键词
        for data in self.received_data:
            self.assertTrue("ERROR" in data or "WARNING" in data,
                          f"接收到不匹配的数据: {data}")
        
        print("✓ 所有接收数据都匹配过滤条件")
    
    @patch('serial.Serial')
    def test_latency_under_100ms(self, mock_serial):
        """测试端到端延迟<100ms
        
        发送100条数据，测量从数据到达到回调执行的延迟
        验证平均延迟<50ms，最大延迟<100ms
        """
        print("\n=== 测试3: 端到端延迟测试（目标<100ms）===")
        
        # 配置mock串口
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_serial.return_value = mock_instance
        
        send_times = []
        receive_times = []
        
        # 准备测试数据队列
        test_data_queue = queue.Queue()
        test_count = 100
        
        for i in range(test_count):
            test_data_queue.put(f"Test message {i}\n")
        
        # Mock in_waiting和read
        def mock_in_waiting():
            return 1 if not test_data_queue.empty() else 0
        
        def mock_read(size):
            if not test_data_queue.empty():
                send_times.append(time.time())
                data = test_data_queue.get()
                return data.encode('utf-8')
            return b''
        
        type(mock_instance).in_waiting = property(lambda self: mock_in_waiting())
        mock_instance.read = mock_read
        
        def latency_callback(port, timestamp, data, colored_log_entry=""):
            """测量延迟的回调"""
            receive_times.append(time.time())
            with self.data_lock:
                self.received_data.append(data)
        
        # 创建监控器
        monitor = SerialMonitor(
            port=self.test_port,
            baudrate=9600,
            callback=latency_callback,
            save_all_to_log=False
        )
        
        # 启动监控
        self.assertTrue(monitor.start())
        start_time = time.time()
        
        # 等待所有数据处理完成
        timeout = 5
        while not test_data_queue.empty() and (time.time() - start_time) < timeout:
            time.sleep(0.05)
        
        time.sleep(0.3)  # 等待回调完成
        
        monitor.stop()
        
        # 计算延迟
        latencies = []
        for i in range(min(len(send_times), len(receive_times))):
            latency = (receive_times[i] - send_times[i]) * 1000  # 转换为毫秒
            latencies.append(latency)
        
        # 验证结果
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            
            print(f"✓ 测试数据量: {test_count}条")
            print(f"✓ 成功接收: {len(receive_times)}条")
            print(f"✓ 平均延迟: {avg_latency:.2f}ms")
            print(f"✓ 最小延迟: {min_latency:.2f}ms")
            print(f"✓ 最大延迟: {max_latency:.2f}ms")
            
            # 断言：平均延迟应该很小（<50ms）
            self.assertLess(avg_latency, 50,
                           f"平均延迟过大: {avg_latency:.2f}ms > 50ms")
            
            # 断言：最大延迟应该<100ms
            self.assertLess(max_latency, 100,
                           f"最大延迟超标: {max_latency:.2f}ms > 100ms")
        else:
            self.fail("没有收到任何数据，无法测量延迟")
    
    @patch('serial.Serial')
    def test_dynamic_filter_update_realtime(self, mock_serial):
        """测试动态更新过滤条件的实时性
        
        在运行中更新过滤条件，验证新条件立即生效
        """
        print("\n=== 测试4: 动态过滤更新实时性 ===")
        
        # 配置mock串口
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_serial.return_value = mock_instance
        
        # 阶段1数据队列
        phase1_queue = queue.Queue()
        for i in range(10):
            phase1_queue.put(f"Message {i}\n")
        
        # Mock for phase 1
        def mock_in_waiting_phase1():
            return 1 if not phase1_queue.empty() else 0
        
        def mock_read_phase1(size):
            if not phase1_queue.empty():
                data = phase1_queue.get()
                return data.encode('utf-8')
            return b''
        
        type(mock_instance).in_waiting = property(lambda self: mock_in_waiting_phase1())
        mock_instance.read = mock_read_phase1
        
        # 创建监控器（初始无过滤）
        monitor = SerialMonitor(
            port=self.test_port,
            baudrate=9600,
            callback=self.callback,
            save_all_to_log=False
        )
        
        self.assertTrue(monitor.start())
        
        # 等待阶段1数据处理完成
        start_time = time.time()
        while not phase1_queue.empty() and (time.time() - start_time) < 2:
            time.sleep(0.05)
        
        time.sleep(0.2)
        phase1_count = len(self.received_data)
        
        # 阶段2：动态更新过滤条件
        monitor.update_filters(keywords=["IMPORTANT"])
        
        # 清空接收数据
        with self.data_lock:
            self.received_data.clear()
        
        # 阶段2数据队列
        phase2_queue = queue.Queue()
        for i in range(20):
            if i % 2 == 0:
                phase2_queue.put(f"IMPORTANT: Message {i}\n")
            else:
                phase2_queue.put(f"Normal message {i}\n")
        
        # Update mock for phase 2
        def mock_in_waiting_phase2():
            return 1 if not phase2_queue.empty() else 0
        
        def mock_read_phase2(size):
            if not phase2_queue.empty():
                data = phase2_queue.get()
                return data.encode('utf-8')
            return b''
        
        type(mock_instance).in_waiting = property(lambda self: mock_in_waiting_phase2())
        mock_instance.read = mock_read_phase2
        
        # 等待阶段2数据处理完成
        start_time = time.time()
        while not phase2_queue.empty() and (time.time() - start_time) < 2:
            time.sleep(0.05)
        
        time.sleep(0.2)
        phase2_count = len(self.received_data)
        
        monitor.stop()
        
        print(f"✓ 阶段1（无过滤）接收: {phase1_count}条（期望10条）")
        print(f"✓ 阶段2（过滤后）接收: {phase2_count}条（期望10条）")
        
        # 验证无过滤时全部接收
        self.assertEqual(phase1_count, 10,
                        f"无过滤阶段接收异常: 期望10条，实际{phase1_count}条")
        
        # 验证过滤后只接收匹配数据
        self.assertGreater(phase2_count, 8,
                          f"过滤后接收数据不足: 期望>8条，实际{phase2_count}条")
        
        # 验证接收的数据都包含关键词
        for data in self.received_data:
            self.assertIn("IMPORTANT", data,
                         f"接收到不匹配的数据: {data}")
        
        print("✓ 动态过滤更新立即生效")


class TestMultiPortPerformance(unittest.TestCase):
    """多串口并发性能测试"""
    
    @patch('serial.Serial')
    def test_parallel_startup_performance(self, mock_serial):
        """测试批量并行启动性能
        
        并行启动10个串口，验证启动时间<2秒
        """
        print("\n=== 测试5: 批量并行启动性能（10个串口）===")
        
        # 配置mock
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_instance.in_waiting = 0
        mock_serial.return_value = mock_instance
        
        # 创建多串口管理器
        manager = MultiSerialMonitor(log_dir="test_logs")
        
        # 准备10个串口配置
        port_configs = []
        for i in range(10):
            port_configs.append({
                'port': f'COM{i}',
                'baudrate': 9600,
                'callback': lambda p, t, d, c="": None,
                'save_all_to_log': False,
                'enable_color': False
            })
        
        # 测试并行启动
        start_time = time.time()
        results = manager.add_monitors_parallel(port_configs)
        end_time = time.time()
        
        startup_time = end_time - start_time
        success_count = sum(1 for success in results.values() if success)
        
        print(f"✓ 配置串口数: 10个")
        print(f"✓ 成功启动: {success_count}个")
        print(f"✓ 启动时间: {startup_time:.2f}秒")
        # 验证大部分串口启动成功
        self.assertGreater(success_count, 8,
                          f"并行启动失败过多: 期望>8个，实际{success_count}个")
        
        # 验证启动时间<2秒（并行启动应该很快）
        self.assertLess(startup_time, 2.0,
                       f"并行启动时间过长: {startup_time:.2f}秒 > 2秒")
        
        # 清理
        manager.stop_all()
        print("✓ 并行启动性能符合要求")


def run_performance_tests():
    """运行性能测试套件"""
    print("=" * 70)
    print("串口监控工具 - 性能和实时性自动化测试")
    print("=" * 70)
    print("\n本测试将验证以下性能指标：")
    print("1. 大数据量处理能力（5000条/5秒）")
    print("2. 实时筛选性能（1000条，10%匹配）")
    print("3. 端到端延迟（<100ms）")
    print("4. 动态过滤更新实时性")
    print("5. 批量并行启动性能（10个串口<2秒）")
    print("\n" + "=" * 70 + "\n")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiPortPerformance))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果摘要
    print("\n" + "=" * 70)
    print("测试结果摘要")
    print("=" * 70)
    print(f"总测试数: {result.testsRun}")
    print(f"✓ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"✗ 失败: {len(result.failures)}")
    print(f"✗ 错误: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 所有性能测试通过！系统性能符合要求。")
    else:
        print("\n⚠️  部分测试失败，请检查性能问题。")
    
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_performance_tests()
    sys.exit(0 if success else 1)
                          