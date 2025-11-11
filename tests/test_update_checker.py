"""
更新检查功能测试脚本
用于测试版本比较和更新检查功能
"""
from update_checker import UpdateChecker
import sys


def test_version_parsing():
    """测试版本号解析"""
    print("=" * 60)
    print("测试1: 版本号解析")
    print("=" * 60)
    
    checker = UpdateChecker()
    
    test_cases = [
        ("1.2.3", (1, 2, 3)),
        ("v1.2.3", (1, 2, 3)),
        ("2.0.0", (2, 0, 0)),
        ("v3.10.5", (3, 10, 5)),
        ("invalid", (0, 0, 0)),
    ]
    
    for version_str, expected in test_cases:
        result = checker._parse_version(version_str)
        status = "✓" if result == expected else "✗"
        print(f"{status} {version_str:15} -> {result} (期望: {expected})")
    
    print()


def test_version_comparison():
    """测试版本号比较"""
    print("=" * 60)
    print("测试2: 版本号比较")
    print("=" * 60)
    
    checker = UpdateChecker()
    
    test_cases = [
        ("3.2.0", "3.1.0", 1, "3.2.0 > 3.1.0"),
        ("3.1.0", "3.1.0", 0, "3.1.0 == 3.1.0"),
        ("3.0.0", "3.1.0", -1, "3.0.0 < 3.1.0"),
        ("4.0.0", "3.9.9", 1, "4.0.0 > 3.9.9"),
        ("v2.1.0", "v2.0.9", 1, "v2.1.0 > v2.0.9"),
    ]
    
    for v1, v2, expected, desc in test_cases:
        result = checker._compare_versions(v1, v2)
        status = "✓" if result == expected else "✗"
        print(f"{status} {desc:25} (结果: {result}, 期望: {expected})")
    
    print()


def test_current_version():
    """测试当前版本读取"""
    print("=" * 60)
    print("测试3: 当前版本读取")
    print("=" * 60)
    
    checker = UpdateChecker()
    current = checker.current_version
    print(f"当前版本: {current}")
    print(f"版本元组: {checker._parse_version(current)}")
    print()


def test_update_check():
    """测试更新检查（需要网络连接）"""
    print("=" * 60)
    print("测试4: 更新检查（需要网络）")
    print("=" * 60)
    
    # 注意：这里使用示例配置，实际使用时需要修改为你的仓库
    checker = UpdateChecker(owner="yourusername", repo="serial_tool")
    
    print(f"当前版本: {checker.current_version}")
    print("正在检查更新...")
    
    try:
        has_update, update_info = checker.check_for_updates()
        
        if update_info:
            print(f"\n服务器响应成功！")
            print(f"最新版本: {update_info.get('version', 'N/A')}")
            print(f"有可用更新: {'是' if has_update else '否'}")
            
            if has_update:
                print("\n更新摘要:")
                print("-" * 60)
                summary = checker.get_update_summary(update_info)
                print(summary)
        else:
            print("✗ 无法获取更新信息（可能是网络问题或配置错误）")
            print("  提示：请检查 owner 和 repo 配置是否正确")
    
    except Exception as e:
        print(f"✗ 检查更新时出错: {e}")
    
    print()


def test_simulated_update():
    """测试模拟更新场景"""
    print("=" * 60)
    print("测试5: 模拟更新场景")
    print("=" * 60)
    
    checker = UpdateChecker()
    current = checker.current_version
    
    # 模拟服务器返回的更新信息
    mock_update_info = {
        "version": "99.0.0",  # 比当前版本高
        "name": "重大更新 v99.0.0",
        "description": "这是一个模拟的更新测试\n- 新功能1\n- 新功能2\n- Bug修复",
        "download_url": "https://github.com/example/serial_tool/releases/tag/v99.0.0",
        "published_at": "2025-11-11T10:00:00Z",
        "assets": [
            {
                "name": "serial_tool_v99.0.0.exe",
                "download_url": "https://example.com/download/serial_tool.exe",
                "size": 15728640
            }
        ]
    }
    
    print(f"当前版本: {current}")
    print(f"模拟最新版本: {mock_update_info['version']}")
    
    # 比较版本
    has_update = checker._compare_versions(
        mock_update_info['version'],
        current
    ) > 0
    
    print(f"是否需要更新: {'是' if has_update else '否'}")
    
    if has_update:
        print("\n更新摘要:")
        print("-" * 60)
        summary = checker.get_update_summary(mock_update_info)
        print(summary)
    
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print(" 更新检查功能测试")
    print("=" * 60 + "\n")
    
    try:
        test_version_parsing()
        test_version_comparison()
        test_current_version()
        test_simulated_update()
        
        # 询问是否进行实际网络测试
        print("=" * 60)
        response = input("是否进行实际网络更新检查？(y/n): ").lower().strip()
        if response == 'y':
            test_update_check()
        else:
            print("跳过网络测试")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        print("\n提示：")
        print("1. 如需实际测试，请先配置 gui_app.py 中的 GitHub 仓库信息")
        print("2. 确保 VERSION 文件包含正确的版本号")
        print("3. 发布 GitHub Release 时，tag 格式应为 v3.1.0")
        print()
        
    except Exception as e:
        print(f"\n测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()