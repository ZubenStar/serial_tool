"""串口工具测试脚本"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from serial_monitor import SerialMonitor, MultiSerialMonitor
import threading
import time


class TestSerialMonitor(unittest.TestCase):
    """SerialMonitor类测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_port = "COM1"
        self.test_baudrate = 9600
        
    def test_init(self):
        """测试初始化"""
        monitor = SerialMonitor(
            port=self.test_port,
            baudrate=self.test_baudrate,
            keywords=["ERROR"],
            regex_patterns=[r"\d+"]
        )
        
        self.assertEqual(monitor.port, self.test_port)
        self.assertEqual(monitor.baudrate, self.test_baudrate)
        self.assertEqual(monitor.keywords, ["ERROR"])
        self.assertEqual(len(monitor.regex_patterns), 1)
        self.assertFalse(monitor.is_running)
        
    def test_matches_filter_no_filter(self):
        """测试无过滤条件时匹配所有数据"""
        monitor = SerialMonitor(port=self.test_port)
        
        self.assertTrue(monitor._matches_filter("any data"))
        self.assertTrue(monitor._matches_filter("another data"))
        
    def test_matches_filter_keywords(self):
        """测试关键词过滤"""
        monitor = SerialMonitor(
            port=self.test_port,
            keywords=["ERROR", "WARNING"]
        )
        
        self.assertTrue(monitor._matches_filter("ERROR: something wrong"))
        self.assertTrue(monitor._matches_filter("WARNING: check this"))
        self.assertFalse(monitor._matches_filter("INFO: normal message"))
        
    def test_matches_filter_regex(self):
        """测试正则表达式过滤"""
        monitor = SerialMonitor(
            port=self.test_port,
            regex_patterns=[r"Temperature:\s*\d+", r"0x[0-9A-F]+"]
        )
        
        self.assertTrue(monitor._matches_filter("Temperature: 25"))
        self.assertTrue(monitor._matches_filter("Data: 0xABCD"))
        self.assertFalse(monitor._matches_filter("Normal message"))
        
    def test_matches_filter_combined(self):
        """测试组合过滤"""
        monitor = SerialMonitor(
            port=self.test_port,
            keywords=["ERROR"],
            regex_patterns=[r"\d{4}-\d{2}-\d{2}"]
        )
        
        self.assertTrue(monitor._matches_filter("ERROR: failed"))
        self.assertTrue(monitor._matches_filter("Date: 2025-10-21"))
        self.assertFalse(monitor._matches_filter("Normal message"))


class TestMultiSerialMonitor(unittest.TestCase):
    """MultiSerialMonitor类测试"""
    
    def setUp(self):
        """测试前准备"""
        self.monitor = MultiSerialMonitor(log_dir="test_logs")
        
    def test_init(self):
        """测试初始化"""
        self.assertEqual(len(self.monitor.monitors), 0)
        self.assertEqual(self.monitor.log_dir, "test_logs")
        
    @patch('serial_monitor.SerialMonitor.start')
    def test_add_monitor_success(self, mock_start):
        """测试添加串口成功"""
        mock_start.return_value = True
        
        result = self.monitor.add_monitor(
            port="COM1",
            baudrate=9600
        )
        
        self.assertTrue(result)
        self.assertIn("COM1", self.monitor.monitors)
        
    @patch('serial_monitor.SerialMonitor.start')
    def test_add_monitor_duplicate(self, mock_start):
        """测试添加重复串口"""
        mock_start.return_value = True
        
        self.monitor.add_monitor(port="COM1")
        result = self.monitor.add_monitor(port="COM1")
        
        self.assertFalse(result)
        
    @patch('serial_monitor.SerialMonitor.start')
    @patch('serial_monitor.SerialMonitor.stop')
    def test_remove_monitor(self, mock_stop, mock_start):
        """测试移除串口"""
        mock_start.return_value = True
        
        self.monitor.add_monitor(port="COM1")
        result = self.monitor.remove_monitor("COM1")
        
        self.assertTrue(result)
        self.assertNotIn("COM1", self.monitor.monitors)
        
    def test_remove_monitor_not_exists(self):
        """测试移除不存在的串口"""
        result = self.monitor.remove_monitor("COM99")
        self.assertFalse(result)
        
    @patch('serial_monitor.SerialMonitor.start')
    @patch('serial_monitor.SerialMonitor.stop')
    def test_stop_all(self, mock_stop, mock_start):
        """测试停止所有串口"""
        mock_start.return_value = True
        
        self.monitor.add_monitor(port="COM1")
        self.monitor.add_monitor(port="COM2")
        
        self.monitor.stop_all()
        
        self.assertEqual(len(self.monitor.monitors), 0)
        
    @patch('serial_monitor.SerialMonitor.start')
    def test_get_active_ports(self, mock_start):
        """测试获取活动串口列表"""
        mock_start.return_value = True
        
        self.monitor.add_monitor(port="COM1")
        self.monitor.add_monitor(port="COM2")
        
        active_ports = self.monitor.get_active_ports()
        
        self.assertEqual(len(active_ports), 2)
        self.assertIn("COM1", active_ports)
        self.assertIn("COM2", active_ports)
        
    @patch('serial.tools.list_ports.comports')
    def test_list_available_ports(self, mock_comports):
        """测试列出可用串口"""
        mock_port1 = Mock()
        mock_port1.device = "COM1"
        mock_port2 = Mock()
        mock_port2.device = "COM2"
        
        mock_comports.return_value = [mock_port1, mock_port2]
        
        ports = MultiSerialMonitor.list_available_ports()
        
        self.assertEqual(len(ports), 2)
        self.assertIn("COM1", ports)
        self.assertIn("COM2", ports)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    @patch('serial.Serial')
    def test_callback_execution(self, mock_serial):
        """测试回调函数执行"""
        callback_called = threading.Event()
        received_data = []
        
        def test_callback(port, timestamp, data):
            received_data.append((port, timestamp, data))
            callback_called.set()
        
        # 模拟串口
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_instance.in_waiting = 0
        mock_serial.return_value = mock_instance
        
        monitor = SerialMonitor(
            port="COM1",
            baudrate=9600,
            callback=test_callback
        )
        
        # 这个测试主要验证结构正确性
        self.assertIsNotNone(monitor.callback)


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("运行串口监控工具测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestSerialMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiSerialMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "=" * 60)
    print(f"测试完成: 运行 {result.testsRun} 个测试")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)