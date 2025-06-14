#!/usr/bin/env python3
"""
版本管理脚本
自动化版本号递增和更新
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import Tuple, Optional


class VersionBumper:
    """版本管理器"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.setup_py_path = self.project_root / "setup.py"
        
    def get_current_version(self) -> Optional[str]:
        """从pyproject.toml获取当前版本"""
        if not self.pyproject_path.exists():
            print("错误: 未找到pyproject.toml文件")
            return None
            
        with open(self.pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 匹配版本号
        version_pattern = r'version\s*=\s*["\']([^"\']+)["\']'
        version_match = re.search(version_pattern, content)
        if version_match:
            return version_match.group(1)
        
        print("错误: 在pyproject.toml中未找到版本号")
        return None
    
    def parse_version(self, version: str) -> Tuple[int, int, int]:
        """解析版本号为(major, minor, patch)"""
        try:
            parts = version.split('.')
            if len(parts) != 3:
                raise ValueError("版本号格式应为 major.minor.patch")
            return tuple(int(part) for part in parts)
        except ValueError as e:
            print(f"错误: 无效的版本号格式 '{version}': {e}")
            sys.exit(1)
    
    def format_version(self, major: int, minor: int, patch: int) -> str:
        """格式化版本号"""
        return f"{major}.{minor}.{patch}"
    
    def bump_version(self, bump_type: str, current_version: str) -> str:
        """递增版本号"""
        major, minor, patch = self.parse_version(current_version)
        
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            print(f"错误: 无效的版本递增类型 '{bump_type}'")
            sys.exit(1)
        
        return self.format_version(major, minor, patch)
    
    def update_pyproject_toml(self, new_version: str) -> bool:
        """更新pyproject.toml中的版本号"""
        if not self.pyproject_path.exists():
            print("错误: 未找到pyproject.toml文件")
            return False
        
        with open(self.pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换版本号
        version_pattern = r'(version\s*=\s*["\'])[^"\']+(["\'])'
        new_content = re.sub(version_pattern, f'\\1{new_version}\\2', content)
        
        if new_content == content:
            print("警告: pyproject.toml中的版本号未发生变化")
            return False
        
        with open(self.pyproject_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 已更新pyproject.toml中的版本号为 {new_version}")
        return True
    
    def update_setup_py(self, new_version: str) -> bool:
        """更新setup.py中的版本号（如果存在）"""
        if not self.setup_py_path.exists():
            return True  # 文件不存在不算错误
        
        with open(self.setup_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换版本号
        version_pattern = r'(version\s*=\s*["\'])([^"\']+)(["\'])'
        new_content = re.sub(version_pattern, f'\\1{new_version}\\2', content)
        
        if new_content != content:
            with open(self.setup_py_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ 已更新setup.py中的版本号为 {new_version}")
        
        return True
    
    def update_init_file(self, new_version: str) -> bool:
        """更新__init__.py中的__version__（如果存在）"""
        init_files = [
            self.project_root / "__init__.py",
            self.project_root / "vertex_flow" / "__init__.py"
        ]
        
        updated = False
        for init_file in init_files:
            if not init_file.exists():
                continue
                
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找并替换__version__
            version_pattern = r'(__version__\s*=\s*["\'])([^"\']+)(["\'])'
            new_content = re.sub(version_pattern, f'\\1{new_version}\\2', content)
            
            if new_content != content:
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ 已更新{init_file}中的版本号为 {new_version}")
                updated = True
        
        return True
    
    def show_current_version(self):
        """显示当前版本号"""
        current = self.get_current_version()
        if current:
            print(f"当前版本: {current}")
        else:
            print("无法获取当前版本")
    
    def bump_and_update(self, bump_type: str, dry_run: bool = False) -> bool:
        """递增并更新版本号"""
        current_version = self.get_current_version()
        if not current_version:
            return False
        
        new_version = self.bump_version(bump_type, current_version)
        
        print(f"版本号变更: {current_version} -> {new_version}")
        
        if dry_run:
            print("(预览模式，未实际更新文件)")
            return True
        
        # 更新所有相关文件
        success = True
        success &= self.update_pyproject_toml(new_version)
        success &= self.update_setup_py(new_version)
        success &= self.update_init_file(new_version)
        
        if success:
            print(f"\n🎉 版本号已成功更新为 {new_version}")
            print("\n建议的后续步骤:")
            print(f"1. git add .")
            print(f"2. git commit -m 'bump version to {new_version}'")
            print(f"3. git tag v{new_version}")
            print(f"4. git push && git push --tags")
        
        return success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='版本管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s show                    # 显示当前版本
  %(prog)s patch                   # 递增补丁版本 (0.1.0 -> 0.1.1)
  %(prog)s minor                   # 递增次版本 (0.1.0 -> 0.2.0)
  %(prog)s major                   # 递增主版本 (0.1.0 -> 1.0.0)
  %(prog)s patch --dry-run         # 预览版本变更
        """
    )
    
    parser.add_argument(
        'action',
        choices=['show', 'patch', 'minor', 'major'],
        help='要执行的操作'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，不实际修改文件'
    )
    
    parser.add_argument(
        '--project-root',
        default='.',
        help='项目根目录路径 (默认: 当前目录)'
    )
    
    args = parser.parse_args()
    
    # 检查是否在项目根目录
    project_root = Path(args.project_root)
    if not (project_root / 'pyproject.toml').exists():
        print(f"错误: 在 {project_root} 中未找到pyproject.toml文件")
        print("请确保在项目根目录运行此脚本")
        sys.exit(1)
    
    bumper = VersionBumper(args.project_root)
    
    try:
        if args.action == 'show':
            bumper.show_current_version()
        else:
            success = bumper.bump_and_update(args.action, args.dry_run)
            if not success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()