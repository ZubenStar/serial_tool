"""
更新检查模块
用于检查应用程序的最新版本并提供更新提示
"""
import urllib.request
import json
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import re


class UpdateChecker:
    """应用程序更新检查器"""
    
    # GitHub API 配置（请根据实际项目修改）
    GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}/releases/latest"
    # 备用：自定义服务器URL
    CUSTOM_UPDATE_URL = None  # 例如: "https://yourdomain.com/api/version"
    
    def __init__(self, owner: str = "yourusername", repo: str = "serial_tool"):
        """
        初始化更新检查器
        
        Args:
            owner: GitHub用户名或组织名
            repo: GitHub仓库名
        """
        self.owner = owner
        self.repo = repo
        self.current_version = self._get_current_version()
    
    def _get_current_version(self) -> str:
        """从VERSION文件读取当前版本号"""
        try:
            version_file = Path(__file__).parent / "VERSION"
            if version_file.exists():
                content = version_file.read_text(encoding='utf-8').strip()
                lines = content.split('\n')
                return lines[0].strip()
        except Exception as e:
            print(f"读取当前版本失败: {e}")
        return "0.0.0"
    
    def _parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """
        解析版本号字符串为元组
        
        Args:
            version_str: 版本号字符串，如 "1.2.3" 或 "v1.2.3"
            
        Returns:
            版本号元组 (major, minor, patch)
        """
        # 移除可能的 'v' 前缀
        version_str = version_str.lstrip('v').strip()
        
        # 使用正则表达式提取版本号
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
        if match:
            major, minor, patch = map(int, match.groups())
            return (major, minor, patch)
        
        return (0, 0, 0)
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        比较两个版本号
        
        Args:
            version1: 第一个版本号
            version2: 第二个版本号
            
        Returns:
            1: version1 > version2
            0: version1 == version2
            -1: version1 < version2
        """
        v1 = self._parse_version(version1)
        v2 = self._parse_version(version2)
        
        if v1 > v2:
            return 1
        elif v1 < v2:
            return -1
        else:
            return 0
    
    def _fetch_from_github(self) -> Optional[Dict[str, Any]]:
        """从GitHub API获取最新版本信息"""
        try:
            url = self.GITHUB_API_URL.format(owner=self.owner, repo=self.repo)
            
            # 设置超时和User-Agent
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'SerialToolUpdateChecker/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                return {
                    'version': data.get('tag_name', '').lstrip('v'),
                    'name': data.get('name', ''),
                    'description': data.get('body', ''),
                    'download_url': data.get('html_url', ''),
                    'published_at': data.get('published_at', ''),
                    'assets': [
                        {
                            'name': asset.get('name', ''),
                            'download_url': asset.get('browser_download_url', ''),
                            'size': asset.get('size', 0)
                        }
                        for asset in data.get('assets', [])
                    ]
                }
        except Exception as e:
            print(f"从GitHub获取更新信息失败: {e}")
            return None
    
    def _fetch_from_custom_server(self) -> Optional[Dict[str, Any]]:
        """从自定义服务器获取最新版本信息"""
        if not self.CUSTOM_UPDATE_URL:
            return None
        
        try:
            req = urllib.request.Request(
                self.CUSTOM_UPDATE_URL,
                headers={'User-Agent': 'SerialToolUpdateChecker/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            print(f"从自定义服务器获取更新信息失败: {e}")
            return None
    
    def check_for_updates(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        检查是否有可用更新
        
        Returns:
            (has_update, update_info): 
                has_update - 是否有更新
                update_info - 更新信息字典，包含版本号、描述、下载链接等
        """
        # 优先尝试从GitHub获取
        update_info = self._fetch_from_github()
        
        # 如果GitHub失败，尝试自定义服务器
        if not update_info:
            update_info = self._fetch_from_custom_server()
        
        # 如果都失败了
        if not update_info:
            return False, None
        
        # 比较版本
        latest_version = update_info.get('version', '0.0.0')
        has_update = self._compare_versions(latest_version, self.current_version) > 0
        
        return has_update, update_info
    
    def get_update_summary(self, update_info: Dict[str, Any]) -> str:
        """
        生成更新摘要文本
        
        Args:
            update_info: 更新信息字典
            
        Returns:
            格式化的更新摘要文本
        """
        if not update_info:
            return "无法获取更新信息"
        
        version = update_info.get('version', 'Unknown')
        name = update_info.get('name', '')
        description = update_info.get('description', '无更新说明')
        
        # 限制描述长度
        if len(description) > 500:
            description = description[:500] + "..."
        
        summary = f"发现新版本: {version}\n"
        if name:
            summary += f"版本名称: {name}\n"
        summary += f"\n当前版本: {self.current_version}\n"
        summary += f"\n更新内容:\n{description}\n"
        
        # 添加下载链接
        download_url = update_info.get('download_url', '')
        if download_url:
            summary += f"\n下载地址: {download_url}"
        
        # 添加资源文件信息
        assets = update_info.get('assets', [])
        if assets:
            summary += "\n\n可用下载:"
            for asset in assets:
                name = asset.get('name', 'Unknown')
                size_mb = asset.get('size', 0) / (1024 * 1024)
                summary += f"\n  • {name} ({size_mb:.2f} MB)"
        
        return summary


def check_updates_simple(owner: str = "yourusername", repo: str = "serial_tool") -> Tuple[bool, str]:
    """
    简单的更新检查函数
    
    Args:
        owner: GitHub用户名
        repo: 仓库名
        
    Returns:
        (has_update, message): 是否有更新和提示消息
    """
    checker = UpdateChecker(owner, repo)
    has_update, update_info = checker.check_for_updates()
    
    if has_update and update_info:
        message = checker.get_update_summary(update_info)
        return True, message
    elif update_info:
        return False, f"当前已是最新版本 ({checker.current_version})"
    else:
        return False, "无法连接到更新服务器"


if __name__ == "__main__":
    # 测试代码
    print("正在检查更新...")
    has_update, message = check_updates_simple()
    print(message)