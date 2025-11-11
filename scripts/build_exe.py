"""
打包脚本 - 将串口工具打包成exe文件
使用PyInstaller进行打包
"""
import os
import sys
import subprocess
from datetime import datetime

def parse_version(version_str):
    """解析版本号字符串"""
    parts = version_str.split('.')
    return [int(p) for p in parts]

def increment_version(version_str, bump_type='patch'):
    """
    自动递增版本号
    bump_type: 'major', 'minor', 'patch'
    """
    parts = parse_version(version_str)
    
    if bump_type == 'major':
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif bump_type == 'minor':
        parts[1] += 1
        parts[2] = 0
    else:  # patch
        parts[2] += 1
    
    return '.'.join(map(str, parts))

def build_exe(auto_version=None):
    """
    构建exe文件
    auto_version: None (不更新), 'major', 'minor', 'patch' (自动递增版本号)
    """
    
    print("=" * 60)
    print("开始打包串口监控工具...")
    print("=" * 60)
    
    # 备份原始VERSION文件
    original_version = None
    try:
        with open('VERSION', 'r', encoding='utf-8') as f:
            original_version = f.read().strip()
    except Exception as e:
        print(f"\n⚠️  读取VERSION文件失败: {e}")
        return
    
    # 自动更新版本号
    current_version = original_version
    if auto_version in ['major', 'minor', 'patch']:
        try:
            new_version = increment_version(original_version, auto_version)
            with open('VERSION', 'w', encoding='utf-8') as f:
                f.write(new_version)
            print(f"\n✅ 版本号已更新: {original_version} -> {new_version} ({auto_version})")
            current_version = new_version
        except Exception as e:
            print(f"\n⚠️  更新版本号失败: {e}")
            return
    
    # 添加编译时间到VERSION文件
    try:
        # 获取当前时区信息
        from datetime import timezone
        import time
        
        # 获取本地时区偏移
        utc_offset = -time.timezone if not time.daylight else -time.altzone
        hours_offset = utc_offset // 3600
        minutes_offset = (abs(utc_offset) % 3600) // 60
        tz_str = f"UTC{hours_offset:+03d}:{minutes_offset:02d}"
        
        build_time = datetime.now().strftime(f'%Y-%m-%d %H:%M:%S {tz_str}')
        version_with_time = f"{current_version}\n{build_time}"
        
        with open('VERSION', 'w', encoding='utf-8') as f:
            f.write(version_with_time)
        
        print(f"\n✅ 已添加编译时间: {current_version} (编译时间: {build_time})")
    except Exception as e:
        print(f"\n⚠️  添加编译时间失败: {e}")
        # 如果版本号已更新，需要恢复
        if auto_version:
            with open('VERSION', 'w', encoding='utf-8') as f:
                f.write(original_version)
        return
    
    # PyInstaller命令 - 使用spec文件
    cmd = [
        'pyinstaller',
        '--clean',                      # 清理临时文件
        'scripts/serial_tool.spec'      # 使用spec配置文件
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
    except FileNotFoundError:
        print("\n❌ 未找到PyInstaller")
        print("\n请先安装PyInstaller:")
        print("  pip install pyinstaller")
    finally:
        # 恢复VERSION文件（保留新版本号，只移除编译时间）
        try:
            with open('VERSION', 'w', encoding='utf-8') as f:
                f.write(current_version)
            if auto_version:
                print(f"\n✅ VERSION文件已更新为: {current_version}")
            else:
                print(f"\n✅ 已恢复VERSION文件")
        except Exception as e:
            print(f"\n⚠️  恢复VERSION文件失败: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='打包串口监控工具')
    parser.add_argument('--version', choices=['major', 'minor', 'patch'],
                       help='自动递增版本号: major (主版本), minor (次版本), patch (补丁版本)')
    args = parser.parse_args()
    
    # 检查是否在正确的目录
    if not os.path.exists('src/gui_app.py'):
        print("❌ 错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 创建logs目录
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("✅ 创建logs目录")
    
    build_exe(auto_version=args.version)