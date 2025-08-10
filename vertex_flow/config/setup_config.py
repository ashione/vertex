#!/usr/bin/env python3
"""
配置设置脚本
帮助用户基于模板创建实际的配置文件
适用于已安装的vertex包
"""

import getpass
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        # 用户配置目录
        self.user_config_dir = Path.home() / ".vertex" / "config"
        self.config_file = self.user_config_dir / "llm.yml"

        # 包内模板文件
        self.template_file = self._find_template()

    def _find_template(self) -> Path:
        """查找模板文件"""
        # 尝试从当前目录查找（开发模式）
        current_dir = Path(__file__).parent
        template_file = current_dir / "llm.yml.template"
        if template_file.exists():
            return template_file

        # 最后尝试使用当前的配置文件作为模板
        config_file = current_dir / "llm.yml"
        if config_file.exists():
            return config_file

        # 如果都找不到，返回预期位置
        return current_dir / "llm.yml.template"

    def ensure_config_dir(self):
        """确保配置目录存在"""
        self.user_config_dir.mkdir(parents=True, exist_ok=True)

    def has_template(self) -> bool:
        """检查是否存在模板文件"""
        return self.template_file.exists()

    def has_config(self) -> bool:
        """检查是否存在用户配置文件"""
        return self.config_file.exists()

    def load_template(self) -> Dict[str, Any]:
        """加载模板配置"""
        if not self.has_template():
            raise FileNotFoundError(f"模板文件不存在: {self.template_file}")

        with open(self.template_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save_config(self, config: Dict[str, Any]):
        """保存配置到用户目录"""
        self.ensure_config_dir()
        with open(self.config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def get_api_key_securely(self, service_name: str, current_value: str) -> str:
        """安全地获取API密钥"""
        if current_value and not current_value.startswith("YOUR_"):
            use_existing = input(f"检测到 {service_name} 已有配置，是否保留？(y/n): ").lower().strip()
            if use_existing in ["y", "yes", "是"]:
                return current_value

        while True:
            api_key = getpass.getpass(f"请输入 {service_name} 的API密钥 (留空跳过): ")
            if not api_key:
                return current_value
            if len(api_key.strip()) < 10:
                print("API密钥长度太短，请重新输入")
                continue
            return api_key.strip()

    def interactive_setup(self):
        """交互式设置配置"""
        print("=== Vertex 配置向导 ===")
        print("此向导将帮助您配置各种API密钥和服务设置")
        print(f"配置将保存在: {self.config_file}")
        print()

        # 加载模板
        try:
            config = self.load_template()
        except FileNotFoundError:
            print("错误: 找不到配置模板文件")
            return False

        # LLM服务配置
        print("配置LLM服务:")
        llm_config = config.get("llm", {})

        services = {"deepseek": "DeepSeek", "tongyi": "通义千问", "openrouter": "OpenRouter", "openai": "OpenAI"}

        for service_key, service_name in services.items():
            if service_key in llm_config:
                current_sk = llm_config[service_key].get("sk", "").split(":-")[-1].rstrip("}")
                new_sk = self.get_api_key_securely(service_name, current_sk)

                if new_sk and not new_sk.startswith("YOUR_"):
                    llm_config[service_key]["sk"] = f"${{llm.{service_key}.sk:-{new_sk}}}"

                    # 询问是否启用
                    enable = input(f"是否启用 {service_name}？(y/n): ").lower().strip()
                    llm_config[service_key]["enabled"] = enable in ["y", "yes", "是"]

        # 网络搜索服务配置
        print("\n配置网络搜索服务:")
        web_search_config = config.get("web-search", {})

        search_services = {"bocha": "Bocha搜索", "bing": "Bing搜索"}

        for service_key, service_name in search_services.items():
            if service_key in web_search_config:
                current_sk = web_search_config[service_key].get("sk", "").split(":-")[-1].rstrip("}")
                new_sk = self.get_api_key_securely(service_name, current_sk)

                if new_sk and not new_sk.startswith("YOUR_"):
                    web_search_config[service_key]["sk"] = f"${{web-search.{service_key}.sk:-{new_sk}}}"

                    # 询问是否启用
                    enable = input(f"是否启用 {service_name}？(y/n): ").lower().strip()
                    web_search_config[service_key]["enabled"] = enable in ["y", "yes", "是"]

        # 金融服务配置
        print("\n配置金融服务 (可选):")
        finance_config = config.get("finance", {})

        finance_services = {"alpha-vantage": "Alpha Vantage", "finnhub": "Finnhub"}

        for service_key, service_name in finance_services.items():
            if service_key in finance_config:
                setup_finance = input(f"是否配置 {service_name}？(y/n): ").lower().strip()
                if setup_finance in ["y", "yes", "是"]:
                    current_key = finance_config[service_key].get("api-key", "").split(":-")[-1].rstrip("}")
                    new_key = self.get_api_key_securely(service_name, current_key)

                    if new_key and not new_key.startswith("YOUR_"):
                        finance_config[service_key]["api-key"] = f"${{finance.{service_key}.api-key:-{new_key}}}"
                        finance_config[service_key]["enabled"] = True

        # 向量存储配置
        print("\n配置向量存储:")
        use_cloud_vector = input("是否使用云端向量存储 (DashVector)？(y/n): ").lower().strip()

        if use_cloud_vector in ["y", "yes", "是"]:
            vector_config = config.get("vector", {})
            dashvector_config = vector_config.get("dashvector", {})

            # 配置DashVector
            current_key = dashvector_config.get("api-key", "").split(":-")[-1].rstrip("}")
            new_key = self.get_api_key_securely("DashVector", current_key)

            if new_key and not new_key.startswith("YOUR_"):
                dashvector_config["api-key"] = f"${{vector.dashvector.api_key:-{new_key}}}"
                dashvector_config["enabled"] = True
                vector_config["local"]["enabled"] = False

        # 嵌入模型配置
        print("\n配置嵌入模型:")
        use_cloud_embedding = input("是否使用云端嵌入模型？(y/n): ").lower().strip()

        if use_cloud_embedding in ["y", "yes", "是"]:
            embedding_config = config.get("embedding", {})

            # 配置DashScope或BCE
            provider = input("选择云端嵌入提供商 (1: DashScope, 2: BCE): ").strip()

            if provider == "1":
                dashscope_config = embedding_config.get("dashscope", {})
                current_key = dashscope_config.get("api-key", "").split(":-")[-1].rstrip("}")
                new_key = self.get_api_key_securely("DashScope", current_key)

                if new_key and not new_key.startswith("YOUR_"):
                    dashscope_config["api-key"] = f"${{embedding.dashscope.api_key:-{new_key}}}"
                    dashscope_config["enabled"] = True
                    embedding_config["local"]["enabled"] = False

            elif provider == "2":
                bce_config = embedding_config.get("bce", {})
                current_key = bce_config.get("api-key", "").split(":-")[-1].rstrip("}")
                new_key = self.get_api_key_securely("BCE", current_key)

                if new_key and not new_key.startswith("YOUR_"):
                    bce_config["api-key"] = f"${{embedding.bce.api_key:-{new_key}}}"
                    bce_config["enabled"] = True
                    embedding_config["local"]["enabled"] = False

        # 保存配置
        self.save_config(config)
        print(f"\n配置已保存到: {self.config_file}")
        print("配置完成！您现在可以运行应用程序了。")
        return True

    def reset_config(self):
        """重置配置为模板"""
        if self.has_config():
            backup_file = self.config_file.with_suffix(".yml.backup")
            shutil.copy2(self.config_file, backup_file)
            print(f"原配置已备份到: {backup_file}")

        if self.has_template():
            shutil.copy2(self.template_file, self.config_file)
            print(f"配置已重置为模板: {self.config_file}")
        else:
            print("错误: 找不到模板文件")


def main():
    """主函数"""
    manager = ConfigManager()

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "reset":
            manager.reset_config()
            return
        elif command == "check":
            print(f"模板文件存在: {manager.has_template()}")
            print(f"用户配置文件存在: {manager.has_config()}")
            if manager.has_template():
                print(f"模板路径: {manager.template_file}")
            if manager.has_config():
                print(f"配置路径: {manager.config_file}")
            return
        elif command in ["help", "-h", "--help"]:
            print("使用方法:")
            print("  vertex config                   # 交互式配置")
            print("  vertex config reset             # 重置配置为模板")
            print("  vertex config check             # 检查配置状态")
            return

    # 确保配置目录存在
    manager.ensure_config_dir()

    # 检查是否已有配置
    if manager.has_config():
        overwrite = input("检测到已有配置文件，是否重新配置？(y/n): ").lower().strip()
        if overwrite not in ["y", "yes", "是"]:
            print("配置取消")
            return

    # 运行交互式设置
    success = manager.interactive_setup()

    if success:
        print(f"\n提示: 您也可以直接编辑配置文件: {manager.config_file}")
        print("或使用环境变量来覆盖配置值")
        print("\n环境变量示例:")
        print("export llm_deepseek_sk=your_deepseek_api_key")
        print("export web_search_bocha_sk=your_bocha_api_key")
        print("\n启动应用: vertex")
    else:
        print("配置失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
