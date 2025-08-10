#!/usr/bin/env python3
"""
配置初始化脚本
简单快速地基于模板创建配置文件
适用于已安装的vertex包
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

try:
    from importlib import resources
except ImportError:
    try:
        import importlib_resources as resources
    except ImportError:
        resources = None


def find_template(template_name: str = "llm.yml.template") -> Optional[Path]:
    """查找模板文件"""
    # 尝试从已安装的包中获取模板
    if resources:
        try:
            if hasattr(resources, "files"):
                pkg_files = resources.files("vertex_flow.config")
                template_path = pkg_files / template_name
                if template_path.is_file():
                    content = template_path.read_text(encoding="utf-8")
                    temp_file = Path.home() / ".vertex" / f"temp_{template_name}"
                    temp_file.parent.mkdir(parents=True, exist_ok=True)
                    temp_file.write_text(content, encoding="utf-8")
                    return temp_file
            else:
                with resources.path("vertex_flow.config", template_name) as template_path:
                    if template_path.exists():
                        return Path(template_path)
        except (ImportError, FileNotFoundError, ModuleNotFoundError):
            pass

    # 开发模式
    current_dir = Path(__file__).parent
    template_file = current_dir / template_name
    if template_file.exists():
        return template_file

    # 最后尝试使用当前配置文件作为模板
    config_file = current_dir / template_name.replace(".template", "")
    if config_file.exists():
        return config_file

    return None


def init_config():
    """初始化配置文件"""
    user_config_dir = Path.home() / ".vertex" / "config"
    config_file = user_config_dir / "llm.yml"

    # 确保配置目录存在
    user_config_dir.mkdir(parents=True, exist_ok=True)

    # 查找模板文件
    template_file = find_template("llm.yml.template")
    if not template_file or not template_file.exists():
        print("错误: 找不到配置模板文件")
        print("请确保vertex包正确安装，或在开发环境中运行")
        return False

    # 检查是否已有配置文件
    if config_file.exists():
        response = input(f"配置文件 {config_file} 已存在，是否覆盖？(y/n): ")
        if response.lower() not in ["y", "yes", "是"]:
            print("取消初始化")
            return False

        # 备份现有配置
        backup_file = config_file.with_suffix(".yml.backup")
        shutil.copy2(config_file, backup_file)
        print(f"原配置已备份到: {backup_file}")

    # 复制模板到配置文件
    shutil.copy2(template_file, config_file)
    print(f"配置文件已创建: {config_file}")

    # 复制MCP模板
    mcp_template = find_template("mcp.yml.template")
    if mcp_template and mcp_template.exists():
        mcp_config_file = user_config_dir / "mcp.yml"
        if mcp_config_file.exists():
            backup_mcp = mcp_config_file.with_suffix(".yml.backup")
            shutil.copy2(mcp_config_file, backup_mcp)
            print(f"原MCP配置已备份到: {backup_mcp}")
        shutil.copy2(mcp_template, mcp_config_file)
        print(f"MCP配置文件已创建: {mcp_config_file}")

    # 清理临时文件
    if template_file.name == "temp_template.yml":
        template_file.unlink(missing_ok=True)

    print()
    print("下一步:")
    print("1. 编辑配置文件，填入您的API密钥")
    print("2. 或使用交互式配置: vertex config")
    print("3. 或使用环境变量来设置API密钥")
    print()
    print("环境变量示例:")
    print("export llm_deepseek_sk=your_deepseek_api_key")
    print("export web_search_bocha_sk=your_bocha_api_key")

    return True


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["help", "-h", "--help"]:
        print("配置初始化脚本")
        print("用法: vertex config init")
        print("此脚本将基于模板创建配置文件")
        return

    print("=== Vertex 配置初始化 ===")
    success = init_config()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
