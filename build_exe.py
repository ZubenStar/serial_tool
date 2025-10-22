"""
打包脚本 - 将串口工具打包成exe文件
使用PyInstaller进行打包
"""
import os
import sys
import subprocess

def build_exe():
    """构建exe文件"""
    
    print("=" * 60)
    print("开始打包串口监控工具...")
    print("=" * 60)
    
    # PyInstaller命令 - 使用spec文件
    cmd = [
        'pyinstaller',
        '--clean',                      # 清理临时文件
        'serial_tool.spec'              # 使用spec配置文件
    ]
    
    try:
        # 执行打包命令
        print("\n执行打包命令...")
        subprocess.run(cmd, check=True)
        
        print("\n" + "=" * 60)
        print("✅ 打包成功!")
        print("=" * 60)
        # 重命名exe为中文名
        import shutil
        if os.path.exists('dist/SerialMonitorTool.exe'):
            if os.path.exists('dist/串口监控工具.exe'):
                os.remove('dist/串口监控工具.exe')
            shutil.move('dist/SerialMonitorTool.exe', 'dist/串口监控工具.exe')
            print("\n✅ 已将exe重命名为中文名称")
        
        print("\n生成的文件位置:")
        print("  - exe文件: dist/串口监控工具.exe")
        print("  - 配置文件: 运行时自动生成 serial_tool_config.json")
        print("  - 日志目录: 运行时自动创建 logs/ 目录")
        print("\n使用说明:")
        print("  1. 将 dist/串口监控工具.exe 复制到任意目录")
        print("  2. 双击运行即可")
        print("  3. 配置会自动保存在exe同目录下")
        print("=" * 60)
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        print("\n请确保已安装PyInstaller:")
        print("  pip install pyinstaller")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ 未找到PyInstaller")
        print("\n请先安装PyInstaller:")
        print("  pip install pyinstaller")
        sys.exit(1)

if __name__ == "__main__":
    # 检查是否在正确的目录
    if not os.path.exists('gui_app.py'):
        print("❌ 错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 创建logs目录
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("✅ 创建logs目录")
    
    build_exe()