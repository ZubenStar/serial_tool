# 多串口监控工具

一个功能强大的串口监控工具，支持同时监控多个串口、关键词过滤、正则表达式匹配和日志保存。

## 📁 项目结构

```
serial_tool/
├── src/                              # 源代码目录
│   ├── serial_monitor.py            # 核心串口监控类
│   ├── gui_app.py                   # 图形界面应用
│   ├── cli_app.py                   # 命令行应用
│   ├── filter_keywords_history.py   # 🔍 关键词历史管理模块
│   ├── data_visualizer.py           # 📊 数据可视化模块
│   ├── advanced_filter.py           # 🔍 高级过滤模块
│   ├── data_analyzer.py             # 🔧 数据分析工具
│   ├── recorder_player.py           # 🎬 录制回放模块
│   ├── automation_tester.py         # 🤖 自动化测试模块
│   ├── utility_tools.py             # 🛠️ 实用工具箱
│   ├── log_filter.py                # 日志过滤工具
│   └── update_checker.py            # 更新检查器
├── tests/                            # 测试目录
│   ├── test_serial.py               # 单元测试
│   ├── test_performance.py          # 性能测试
│   ├── test_update_checker.py       # 更新检查器测试
│   └── test_update_dialog.py        # 更新对话框测试
├── examples/                         # 示例代码目录
│   ├── example_usage.py             # 基本使用示例
│   └── example_batch_usage.py       # 批量启动示例
├── docs/                             # 文档目录
│   ├── README.md                    # 主文档（本文件）
│   ├── GUI_LAYOUT.md                # GUI布局说明
│   ├── RELEASE_GUIDE.md             # 发布指南
│   └── UPDATE_CHECKER_GUIDE.md      # 更新检查器指南
├── scripts/                          # 构建和工具脚本
│   ├── build_exe.py                 # 本地打包脚本
│   ├── serial_tool.spec             # PyInstaller配置
│   └── hook-serial_monitor.py       # PyInstaller钩子
├── logs/                             # 日志保存目录（自动创建）
├── recordings/                       # 录制文件目录
├── .github/                          # GitHub配置
│   └── workflows/
│       └── build-release.yml        # 自动构建配置
├── requirements.txt                  # 依赖包列表
├── VERSION                           # 版本号文件
└── .gitignore                        # Git忽略配置
```

## 🎯 最新优化 (v1.0.0+)

### 性能优化
- ⚡ **UI更新频率**: 从10ms优化至16ms（约60fps），显著降低CPU占用
- 🔧 **回调节流**: 调整至10ms，在实时性和性能间取得最佳平衡
- 📊 **统计更新**: 降低更新频率至2秒，减少不必要的UI刷新

### 可靠性增强
- 🛡️ **错误处理**: 串口启动失败时提供详细错误类型和信息
- 🔒 **资源管理**: 改进串口停止逻辑，增加线程超时检测和强制清理
- 🚪 **优雅关闭**: 应用关闭时确保所有资源正确释放，避免资源泄漏
- 🔍 **调试增强**: 日志过滤工具错误时提供完整堆栈跟踪

### 代码质量
- 🧹 **代码清理**: 移除未使用的方法，提高代码可维护性
- 📝 **文档完善**: 增加详细的方法说明和优化记录
- ⚠️ **警告机制**: 线程未正常停止时输出明确警告信息

## 功能特性

### 基础功能
✅ **多串口同时监控** - 可以同时监控多个COM口
✅ **批量快速启动** - 🚀 并行打开多个串口，显著提升启动速度
✅ **关键词过滤** - 支持多个关键词过滤，只显示包含关键词的数据
✅ **正则表达式支持** - 支持多个正则表达式模式匹配
✅ **智能日志保存** - 日志文件保存**所有原始数据**，过滤条件仅影响显示和回调
✅ **图形界面和命令行** - 提供GUI和CLI两种使用方式
✅ **实时数据显示** - 实时显示串口接收到的数据
✅ **数据发送** - 支持向指定串口发送数据
✅ **配置记忆功能** - 自动保存和恢复上次使用的配置（波特率、关键词、正则表达式、发送数据）
✅ **批量配置保存** - 保存常用的多串口配置，一键快速启动

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 图形界面（推荐）

```bash
```

### 命令行

```bash
# 列出可用串口
python src/cli_app.py --list-ports

# 监控单个串口
python src/cli_app.py --ports COM1 --baudrate 9600

# 监控多个串口
python src/cli_app.py --ports COM1 COM2 COM3 --baudrate 115200
```

## 运行示例

```bash
# 基本使用示例
python examples/example_usage.py

# 批量启动示例
python examples/example_batch_usage.py
```

## 运行测试

```bash
# 运行单元测试
python tests/test_serial.py

# 运行性能测试
python tests/test_performance.py
```

## 打包成exe文件

### 方式1：GitHub自动构建（推荐）

项目配置了自动构建和发布流程，只需创建标签即可自动生成exe：

```bash
git tag v1.0.0
git push origin v1.0.0
```

详细说明请查看 [docs/RELEASE_GUIDE.md](docs/RELEASE_GUIDE.md)

### 方式2：本地手动打包

```bash
# 1. 安装打包依赖
pip install pyinstaller

# 2. 运行打包脚本
python scripts/build_exe.py

# 3. 在dist目录获取exe文件
```

## 更多文档

- [GUI布局说明](docs/GUI_LAYOUT.md)
- [发布指南](docs/RELEASE_GUIDE.md)
- [更新检查器指南](docs/UPDATE_CHECKER_GUIDE.md)

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！