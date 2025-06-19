#!/usr/bin/env python3
"""
配置加载器
优先从用户目录加载配置，如果不存在则使用包内默认配置
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

try:
    from importlib import resources
except ImportError:
    try:
        import importlib_resources as resources
    except ImportError:
        resources = None


class ConfigLoader:
    """配置加载器"""

    def __init__(self):
        self.user_config_dir = Path.home() / ".vertex" / "config"
        self.user_config_file = self.user_config_dir / "llm.yml"

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        # 优先从用户目录加载
        if self.user_config_file.exists():
            try:
                with open(self.user_config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                print(f"使用用户配置: {self.user_config_file}")
                return config
            except Exception as e:
                print(f"加载用户配置失败: {e}")

        # 如果用户配置不存在，尝试加载默认配置
        return self._load_default_config()

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        # 尝试从包中加载模板配置
        if resources:
            try:
                if hasattr(resources, "files"):
                    pkg_files = resources.files("vertex_flow.config")
                    template_path = pkg_files / "llm.yml.template"
                    if template_path.is_file():
                        content = template_path.read_text(encoding="utf-8")
                        config = yaml.safe_load(content) or {}
                        print("使用包内模板配置")
                        return config
                else:
                    with resources.path("vertex_flow.config", "llm.yml.template") as template_path:
                        if template_path.exists():
                            with open(template_path, "r", encoding="utf-8") as f:
                                config = yaml.safe_load(f) or {}
                            print("使用包内模板配置")
                            return config
            except (ImportError, FileNotFoundError, ModuleNotFoundError):
                pass

        # 如果包配置也不存在，尝试从开发环境加载
        current_dir = Path(__file__).parent
        for config_name in ["llm.yml.template", "llm.yml"]:
            config_file = current_dir / config_name
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f) or {}
                    print(f"使用开发环境配置: {config_file}")
                    return config
                except Exception as e:
                    print(f"加载配置失败 {config_file}: {e}")

        # 如果都找不到，返回基本配置
        print("警告: 找不到配置文件，使用基本默认配置")
        return self._get_basic_config()

    def _get_basic_config(self) -> Dict[str, Any]:
        """获取基本默认配置"""
        return {
            "llm": {
                "deepseek": {
                    "sk": "${llm.deepseek.sk:-YOUR_DEEPSEEK_API_KEY}",
                    "enabled": False,
                    "model-name": "deepseek-chat",
                }
            },
            "web": {"port": 8999, "host": "0.0.0.0", "workers": 8},
            "vector": {"local": {"enabled": True, "dimension": 384, "index_name": "default", "persist_dir": None}},
            "embedding": {
                "local": {
                    "enabled": True,
                    "model_name": "all-MiniLM-L6-v2",
                    "dimension": 384,
                    "use_mirror": True,
                    "mirror_url": "https://hf-mirror.com",
                }
            },
        }

    def has_user_config(self) -> bool:
        """检查是否有用户配置"""
        return self.user_config_file.exists()

    def get_config_path(self) -> Path:
        """获取配置文件路径"""
        return self.user_config_file

    def suggest_setup(self):
        """建议用户设置配置"""
        if not self.has_user_config():
            print()
            print("提示: 未找到用户配置文件")
            print("建议运行以下命令来设置配置:")
            print("  vertex config init    # 快速初始化配置")
            print("  vertex config         # 交互式配置向导")
            print()


# 全局配置加载器实例
_config_loader = ConfigLoader()


def load_config() -> Dict[str, Any]:
    """加载配置的便捷函数"""
    return _config_loader.load_config()


def get_config_loader() -> ConfigLoader:
    """获取配置加载器实例"""
    return _config_loader
