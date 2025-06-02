#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件脱敏工具
用于在提交前自动对配置文件中的敏感信息进行脱敏处理
"""

import os
import re
import sys
from pathlib import Path


def sanitize_sk_values(content):
    """
    对配置文件中的sk值进行脱敏处理

    Args:
        content (str): 配置文件内容

    Returns:
        str: 脱敏后的内容
    """
    # 匹配sk配置行的正则表达式
    # 匹配格式: sk: ${llm.deepseek.sk:sk-[ACTUAL_KEY]}
    # 也匹配: sk: ${llm.openrouter.sk:sk-or-v1-[ACTUAL_KEY]}
    sk_pattern = r"(\s*sk:\s*\$\{[^:]+:)(sk-[a-zA-Z0-9\-]+)(\})"

    def replace_sk(match):
        prefix = match.group(1)
        sk_value = match.group(2)
        suffix = match.group(3)

        # 保留sk-前缀，后面用***代替
        if sk_value.startswith("sk-or-"):
            sanitized = "sk-or-***SANITIZED***"
        elif sk_value.startswith("sk-"):
            sanitized = "sk-***SANITIZED***"
        else:
            sanitized = "***SANITIZED***"

        return f"{prefix}{sanitized}{suffix}"

    # 执行替换
    sanitized_content = re.sub(sk_pattern, replace_sk, content)

    # 匹配api-key配置行的正则表达式
    # 匹配格式: api-key: ${vector.dashvector.api_key:sk-}
    api_key_pattern = r"(\s*api-key:\s*\$\{[^:]+:)(sk-[a-zA-Z0-9]*)(\})"

    def replace_api_key(match):
        prefix = match.group(1)
        api_value = match.group(2)
        suffix = match.group(3)

        # 如果api_value不为空且不是占位符，则脱敏
        if api_value and api_value != "sk-" and len(api_value) > 3:
            sanitized = "sk-***SANITIZED***"
        else:
            sanitized = api_value  # 保持原样（空值或占位符）

        return f"{prefix}{sanitized}{suffix}"

    # 执行api-key替换
    sanitized_content = re.sub(api_key_pattern, replace_api_key, sanitized_content)

    return sanitized_content


def sanitize_file(file_path):
    """
    对指定文件进行脱敏处理

    Args:
        file_path (str): 文件路径

    Returns:
        bool: 是否进行了脱敏处理
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        sanitized_content = sanitize_sk_values(original_content)

        # 检查是否有变化
        if original_content != sanitized_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(sanitized_content)
            print(f"✓ 已对 {file_path} 进行脱敏处理")
            return True
        else:
            print(f"- {file_path} 无需脱敏")
            return False

    except Exception as e:
        print(f"✗ 处理文件 {file_path} 时出错: {e}")
        return False


def main():
    """
    主函数
    """
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # 需要脱敏的配置文件列表
    config_files = [
        project_root / "config" / "llm.yml",
        # 可以添加其他需要脱敏的配置文件
    ]

    print("🔒 开始配置文件脱敏处理...")

    sanitized_count = 0
    for config_file in config_files:
        if config_file.exists():
            if sanitize_file(str(config_file)):
                sanitized_count += 1
        else:
            print(f"⚠ 配置文件不存在: {config_file}")

    if sanitized_count > 0:
        print(f"\n✓ 共处理了 {sanitized_count} 个配置文件")
        print("请检查脱敏结果，确认无误后再提交")
    else:
        print("\n- 所有配置文件均无需脱敏")


if __name__ == "__main__":
    main()
