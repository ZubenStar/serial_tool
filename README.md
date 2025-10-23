# 多串口监控工具

一个功能强大的串口监控工具，支持同时监控多个串口、关键词过滤、正则表达式匹配和日志保存。

## 功能特性

✅ **多串口同时监控** - 可以同时监控多个COM口
✅ **批量快速启动** - 🚀 并行打开多个串口，显著提升启动速度
✅ **关键词过滤** - 支持多个关键词过滤，只显示包含关键词的数据
✅ **正则表达式支持** - 支持多个正则表达式模式匹配
✅ **智能日志保存** - 日志文件保存**所有原始数据**，过滤条件仅影响显示和回调
✅ **图形界面和命令行** - 提供GUI和CLI两种使用方式
✅ **实时数据显示** - 实时显示串口接收到的数据
✅ **数据发送** - 支持向指定串口发送数据
✅ **数据Dump功能** - 📦 支持dump原始二进制数据到文件（适用于耳机等音频设备）
✅ **配置记忆功能** - 自动保存和恢复上次使用的配置（波特率、关键词、正则表达式、发送数据）
✅ **批量配置保存** - 保存常用的多串口配置，一键快速启动

## 安装依赖

```bash
pip install -r requirements.txt
```

## 下载预编译版本（推荐）

**无需安装Python！** 直接下载exe文件即可使用：

👉 [前往Releases页面下载最新版本](../../releases)

下载后解压即用，无需任何配置！

## 打包成exe文件

### 方式1：GitHub自动构建（推荐）

项目配置了自动构建和发布流程，只需创建标签即可自动生成exe：

```bash
# 创建版本标签
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions会自动：
- 构建Windows exe文件
- 创建Release发布
- 上传打包好的ZIP文件

详细说明请查看 [发布指南](RELEASE_GUIDE.md)

### 方式2：本地手动打包

如果您想要本地打包：

```bash
# 1. 安装打包依赖
pip install pyinstaller

# 2. 运行打包脚本
python build_exe.py

# 3. 在dist目录获取exe文件
```

**打包后的特点：**
- ✅ 单个exe文件，无需Python环境
- ✅ 双击即可运行
- ✅ 配置自动保存在exe同目录下
- ✅ 日志自动保存在exe同目录的logs文件夹

## 使用方法

### 方法1: 图形界面（推荐）

```bash
python gui_app.py
```

**GUI功能说明:**
1. 选择串口和波特率
2. 设置关键词过滤（多个关键词用逗号分隔）
3. 设置正则表达式（多个表达式用逗号分隔）
4. 点击"启动监控"开始监控
5. 可以同时启动多个串口监控
6. 在"发送数据"区域可以向指定串口发送数据
7. **Dump数据功能** - 在"📦 Dump数据"区域可以dump原始二进制数据
   - 选择要dump的串口
   - 点击"▶ 开始Dump"开始保存原始二进制数据
   - 点击"⏹ 停止Dump"停止保存
   - 数据保存到 `dumps/` 目录，文件名格式：`{串口名}_{时间戳}.bin`
8. 所有数据实时显示在显示区域
9. 日志自动保存到 `logs/` 目录
10. **配置自动保存** - 您的设置会自动保存，下次打开时自动恢复

**批量快速启动功能:**
1. 配置好串口参数后，点击"添加到批量配置"
2. 重复步骤1添加多个串口配置
3. 点击"快速启动批量配置"即可**并行启动所有串口**
4. 相比逐个启动，批量启动可**显著减少等待时间**
5. 批量配置会自动保存到 `serial_tool_batch_configs.json`
6. 下次打开程序时，批量配置自动恢复，直接点击"快速启动"即可

### 方法2: 命令行

**列出可用串口:**
```bash
python cli_app.py --list-ports
```

**监控单个串口:**
```bash
python cli_app.py --ports COM1 --baudrate 9600
```

**监控多个串口:**
```bash
python cli_app.py --ports COM1 COM2 COM3 --baudrate 115200
```

**使用关键词过滤:**
```bash
python cli_app.py --ports COM1 --keywords ERROR WARNING CRITICAL
```

**使用正则表达式过滤:**
```bash
python cli_app.py --ports COM1 --regex "Error:\s\d+" "Temperature:\s[\d.]+"
```

**组合使用:**
```bash
python cli_app.py --ports COM1 COM2 \
    --baudrate 115200 \
    --keywords ERROR WARNING \
    --regex "0x[0-9A-F]+" \
    --log-dir ./my_logs
```

## 命令行参数

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--ports` | `-p` | 串口列表（必需） | `COM1 COM2` |
| `--baudrate` | `-b` | 波特率（默认9600） | `115200` |
| `--keywords` | `-k` | 关键词过滤列表 | `ERROR WARNING` |
| `--regex` | `-r` | 正则表达式列表 | `"Error:\s\d+"` |
| `--log-dir` | `-l` | 日志目录（默认logs） | `./my_logs` |
| `--list-ports` | - | 列出可用串口 | - |

## 项目结构

```
serial_tool/
├── .github/
│   └── workflows/
│       └── build-release.yml     # GitHub Actions自动构建配置
├── serial_monitor.py             # 核心串口监控类
├── gui_app.py                   # 图形界面应用
├── cli_app.py                   # 命令行应用
├── build_exe.py                 # 本地打包脚本
├── requirements.txt             # 依赖包
├── README.md                    # 说明文档
├── RELEASE_GUIDE.md             # 发布指南
├── serial_tool_config.json      # GUI配置文件（自动生成）
└── logs/                        # 日志保存目录（自动创建）
```

## 核心类说明

### SerialMonitor
单个串口监控类，负责一个串口的读取、过滤和日志保存。

**主要方法:**
- `start()` - 启动串口监控
- `stop()` - 停止串口监控
- `send(data)` - 向串口发送数据

### MultiSerialMonitor
多串口管理器，可以同时管理多个串口监控。

**主要方法:**
- `add_monitor()` - 添加单个串口监控
- `add_monitors_parallel()` - 🚀 **并行添加多个串口监控（快速启动）**
- `remove_monitor()` - 移除串口监控
- `send()` - 向指定串口发送数据
- `stop_all()` - 停止所有串口监控
- `list_available_ports()` - 列出系统可用串口

## 重要说明

### 关于日志保存和过滤

**关键特性：即使启用了过滤功能，日志文件也会保存所有原始数据！**

- **日志文件** (`logs/` 目录)：保存**所有**接收到的串口数据（完整记录）
- **屏幕显示**：只显示匹配过滤条件的数据
- **回调函数**：只对匹配过滤条件的数据触发

这样设计的好处：
1. 不会丢失任何数据，所有原始数据都保存在日志中
2. 界面只显示关心的数据，不会被无关信息淹没
3. 后续可以回溯查看完整日志

**示例：**
```bash
# 只在屏幕上显示包含"ERROR"的行，但日志文件保存所有数据
python cli_app.py --ports COM1 --keywords ERROR
```

如果你想让日志文件也只保存过滤后的数据，可以在代码中设置 `save_all_to_log=False`：
```python
monitor.add_monitor(
    port="COM1",
    keywords=["ERROR"],
    save_all_to_log=False  # 日志也只保存匹配的数据
)
```

## 使用示例

### 示例1: 监控Arduino输出

```bash
# 监控Arduino的调试输出，过滤包含"Temperature"或"Humidity"的行
python cli_app.py --ports COM3 --baudrate 9600 --keywords Temperature Humidity
```

### 示例2: 监控多个设备

```bash
# 同时监控3个设备
python cli_app.py --ports COM1 COM2 COM3 --baudrate 115200
```

### 示例3: 使用正则表达式

```bash
# 匹配十六进制数据和温度读数
python cli_app.py --ports COM1 \
    --regex "0x[0-9A-Fa-f]+" "Temp:\s*[\d.]+°C"
```

### 示例4: Python代码中使用

```python
from serial_monitor import MultiSerialMonitor

def my_callback(port, timestamp, data):
    print(f"[{port}] {data}")

# 创建监控器
monitor = MultiSerialMonitor(log_dir="my_logs")

# 添加串口监控
monitor.add_monitor(
    port="COM1",
    baudrate=115200,
    keywords=["ERROR", "WARNING"],
    regex_patterns=[r"\d{4}-\d{2}-\d{2}"],
    callback=my_callback
)

# 发送数据
monitor.send("COM1", "Hello\n")

# 停止监控
monitor.stop_all()
```

### 示例5: 批量快速启动多个串口

```python
from serial_monitor import MultiSerialMonitor

def my_callback(port, timestamp, data, colored_log_entry=""):
    print(f"[{port}] {data}")

# 创建监控器
monitor = MultiSerialMonitor(log_dir="logs")

# 准备多个串口配置
batch_configs = [
    {
        'port': 'COM3',
        'baudrate': 115200,
        'keywords': ['ERROR', 'WARNING'],
        'callback': my_callback,
        'enable_color': True
    },
    {
        'port': 'COM4',
        'baudrate': 115200,
        'callback': my_callback,
        'enable_color': True
    },
    {
        'port': 'COM5',
        'baudrate': 9600,
        'callback': my_callback,
        'enable_color': True
    }
]

# 并行快速启动（比逐个启动快得多！）
results = monitor.add_monitors_parallel(batch_configs)

# 查看启动结果
for port, success in results.items():
    print(f"{port}: {'成功' if success else '失败'}")

# 停止所有监控
monitor.stop_all()
```

查看完整示例: [`example_batch_usage.py`](example_batch_usage.py)

### 示例6: 使用Dump功能保存原始二进制数据

```python
from serial_monitor import MultiSerialMonitor
import time

def my_callback(port, timestamp, data, colored_log_entry=""):
    print(f"[{port}] {data}")

# 创建监控器
monitor = MultiSerialMonitor(log_dir="logs")

# 添加串口监控
monitor.add_monitor(
    port='COM3',
    baudrate=115200,
    callback=my_callback,
    enable_color=True
)

# 开始dump原始二进制数据（适用于音频、图像等二进制数据流）
monitor.start_dump('COM3')
print("正在dump数据...")

# dump 10秒
time.sleep(10)

# 停止dump
monitor.stop_dump('COM3')
print("Dump完成")

# 查看统计信息
stats = monitor.get_all_stats()
if 'COM3' in stats:
    print(f"总接收: {stats['COM3']['total_bytes']} 字节")
    print(f"已dump: {stats['COM3']['dumped_bytes']} 字节")
    print(f"文件: {stats['COM3']['dump_file']}")

# 停止监控
monitor.stop_all()
```

查看完整示例: [`example_dump_usage.py`](example_dump_usage.py)

**Dump功能说明：**
- 保存的是**原始二进制数据**，不做任何编码转换
- 适用于耳机音频数据、图像数据等二进制流
- **智能标记检测**：自动识别 `[audio dump]` 等标记，只dump标记后的二进制数据
- 数据格式：根据设备协议，可能包含头部信息 + 二进制数据
- 可以随时开始/停止dump，不影响串口监控
- dump文件保存在 `dumps/` 目录

**协议格式识别：**
```
[2025-10-23 16:17:13.xxx] [COM5] [trace]正常日志消息
[2025-10-23 16:17:13.xxx] [COM5] [trace][audio dump]<二进制音频数据>
[2025-10-23 16:17:13.xxx] [COM5] 其他正常日志
```
当检测到 `[audio dump]` 标记时，会自动提取并保存标记后的二进制数据。

## 日志格式

日志文件保存在 `logs/` 目录，文件名格式：`{串口名}_{时间戳}.log`

示例日志内容：
```
[2025-10-21 14:00:01.123] [COM1] Temperature: 25.5°C
[2025-10-21 14:00:02.456] [COM1] Humidity: 60%
[2025-10-21 14:00:03.789] [COM1] ERROR: Sensor timeout
```

## Dump文件格式

Dump文件保存在 `dumps/` 目录，文件名格式：`{串口名}_{时间戳}.bin`

示例文件名：
```
dumps/COM3_20251023_161234.bin
dumps/COM4_20251023_161235.bin
```

**注意：**
- Dump文件包含**原始二进制数据**，可能包含设备特定的协议头
- 需要根据具体设备的协议来解析dump文件
- 建议使用十六进制编辑器（如HxD）查看dump文件内容

## 配置记忆功能

GUI版本会自动保存您的配置到 `serial_tool_config.json` 文件，包括：
- 波特率设置
- 关键词过滤条件
- 正则表达式模式
- 发送数据框的内容

配置会在以下情况自动保存：
- 修改任何配置项时实时保存
- 关闭应用程序时保存

下次启动应用时，会自动恢复上次的配置，让您无需重复输入！

### 批量配置功能

GUI版本还支持批量串口配置保存到 `serial_tool_batch_configs.json` 文件：
- 保存多个常用串口的配置
- 一键快速启动所有配置的串口
- 使用并行启动技术，大幅提升多串口打开速度

**使用方法：**
1. 配置好一个串口的参数（端口、波特率、过滤条件）
2. 点击"添加到批量配置"按钮
3. 重复1-2步骤添加更多串口
4. 点击"快速启动批量配置"即可并行启动所有串口
5. 批量配置会自动保存，下次直接点击"快速启动"即可

**性能优势：**
- 传统方式：串行启动3个串口约需 3-6 秒
- 批量方式：并行启动3个串口约需 1-2 秒
- **速度提升：2-3倍**

## 注意事项

1. **权限问题**: 在Linux/Mac上可能需要串口访问权限
   ```bash
   sudo usermod -a -G dialout $USER  # Linux
   ```

2. **串口被占用**: 确保串口没有被其他程序占用

3. **波特率匹配**: 确保设置的波特率与设备匹配

4. **编码问题**: 工具自动尝试UTF-8和GBK解码

5. **配置文件**: GUI配置保存在 `serial_tool_config.json`，可手动删除以重置配置

## 常见问题

**Q: 找不到串口?**  
A: 运行 `python cli_app.py --list-ports` 查看可用串口

**Q: 无法打开串口?**  
A: 检查串口是否被其他程序占用，或检查权限设置

**Q: 数据显示乱码?**  
A: 检查波特率设置是否正确，工具会自动尝试多种编码

**Q: 日志文件太大?**  
A: 使用关键词或正则表达式过滤，只记录需要的数据

## 系统要求

### 源码运行
- Python 3.7+
- pyserial 3.5+
- tkinter（GUI版本需要，通常Python自带）

### exe版本（打包后）
- Windows 7/10/11（64位）
- 无需Python环境
- 无需安装任何依赖

## Windows系统

串口名称示例: `COM1`, `COM2`, `COM3`...

## Linux系统

串口名称示例: `/dev/ttyUSB0`, `/dev/ttyACM0`, `/dev/ttyS0`...

## Mac系统

串口名称示例: `/dev/cu.usbserial`, `/dev/tty.usbserial`...

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！