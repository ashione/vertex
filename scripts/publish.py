#!/usr/bin/env python3
"""
PyPI发布脚本
自动化构建和发布到PyPI的流程
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """执行命令并打印输出"""
    print(f"执行命令: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if check and result.returncode != 0:
        print(f"命令执行失败，退出码: {result.returncode}")
        sys.exit(1)

    return result


def run_uv_command(cmd, check=True):
    """执行uv命令并打印输出"""
    full_cmd = f"uv {cmd}"
    return run_command(full_cmd, check)


def clean_build():
    """清理构建目录"""
    print("清理构建目录...")
    dirs_to_clean = ["build", "dist", "*.egg-info"]

    for pattern in dirs_to_clean:
        if "*" in pattern:
            # 使用glob匹配
            for path in Path(".").glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"删除目录: {path}")
        else:
            path = Path(pattern)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"删除: {path}")


def check_dependencies():
    """检查必要的依赖"""
    print("检查发布依赖...")
    print("同步开发依赖...")
    run_uv_command("sync --dev")


def run_tests():
    """运行测试"""
    print("运行测试...")
    if Path("vertex_flow/tests").exists():
        run_uv_command("run python -m pytest vertex_flow/tests/ -v")
    else:
        print("未找到测试目录，跳过测试")


def build_package():
    """构建包"""
    print("构建包...")
    run_uv_command("build")


def check_package():
    """检查包的完整性"""
    print("检查包完整性...")
    run_uv_command("run python -m twine check dist/*")


def upload_to_testpypi():
    """上传到TestPyPI"""
    print("上传到TestPyPI...")
    run_uv_command("run python -m twine upload --repository testpypi dist/*")


def upload_to_pypi():
    """上传到PyPI"""
    print("上传到PyPI...")
    run_uv_command("run python -m twine upload dist/*")


def bump_version(bump_type):
    """递增版本号"""
    print(f"递增版本号 ({bump_type})...")
    script_path = Path(__file__).parent / "version_bump.py"
    run_command(f"python {script_path} {bump_type}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="PyPI发布脚本")
    parser.add_argument("--test", action="store_true", help="上传到TestPyPI而不是PyPI")
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试")
    parser.add_argument("--skip-clean", action="store_true", help="跳过清理")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], help="发布前递增版本号")
    parser.add_argument("--no-bump", action="store_true", help="跳过版本递增")

    args = parser.parse_args()

    try:
        # 检查是否在项目根目录
        if not Path("pyproject.toml").exists():
            print("错误: 请在项目根目录运行此脚本")
            sys.exit(1)

        # 版本管理
        if args.bump and not args.no_bump:
            bump_version(args.bump)
        elif not args.no_bump and not args.test:
            # 正式发布时默认递增patch版本
            print("正式发布模式，自动递增patch版本...")
            print("如需跳过版本递增，请使用 --no-bump 参数")
            bump_version("patch")

        # 清理构建目录
        if not args.skip_clean:
            clean_build()

        # 检查依赖
        check_dependencies()

        # 运行测试
        if not args.skip_tests:
            run_tests()

        # 构建包
        build_package()

        # 检查包
        check_package()

        # 上传
        if args.test:
            upload_to_testpypi()
            print("\n✅ 成功上传到TestPyPI!")
            print("测试安装命令: pip install -i https://test.pypi.org/simple/ vertex")
        else:
            # 确认上传到正式PyPI
            confirm = input("确认上传到PyPI? (y/N): ")
            if confirm.lower() == "y":
                upload_to_pypi()
                print("\n✅ 成功上传到PyPI!")
                print("安装命令: pip install vertex")
            else:
                print("取消上传")

    except KeyboardInterrupt:
        print("\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发布失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
