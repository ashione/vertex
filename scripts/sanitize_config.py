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
    对配置文件中的sk值和api-key值进行脱敏处理

    Args:
        content (str): 配置文件内容

    Returns:
        str: 脱敏后的内容
    """
    # 1. 匹配sk配置行的正则表达式
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

    # 执行SK替换
    sanitized_content = re.sub(sk_pattern, replace_sk, content)

    # 2. 匹配包含真实API密钥的sk配置（新格式）
    # 匹配格式: sk: ${llm.deepseek.sk:-sk-1c72572257634abb90a9b17520a94847}
    # 或: sk: ${llm.openrouter.sk:-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}
    new_sk_pattern = r"(\s*sk:\s*\$\{[^:]+:-)(sk-[a-zA-Z0-9\-]{10,})(\})"

    def replace_new_sk(match):
        prefix = match.group(1)
        sk_value = match.group(2)
        suffix = match.group(3)

        # 如果包含真实的API密钥（长度 > 10），则脱敏
        if len(sk_value) > 10:
            if sk_value.startswith("sk-or-"):
                sanitized = "sk-or-***SANITIZED***"
            elif sk_value.startswith("sk-"):
                sanitized = "sk-***SANITIZED***"
            else:
                sanitized = "***SANITIZED***"
            return f"{prefix}{sanitized}{suffix}"
        else:
            return match.group(0)  # 保持原样

    # 执行新格式SK替换
    sanitized_content = re.sub(new_sk_pattern, replace_new_sk, sanitized_content)

    # 3. 匹配api-key配置行的正则表达式
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

    # 4. 匹配包含真实API密钥的api-key配置（新格式）
    # 匹配格式: api-key: ${vector.dashvector.api_key:-sk-abc123...}
    new_api_key_pattern = r"(\s*api-key:\s*\$\{[^:]+:-)(sk-[a-zA-Z0-9\-]{10,}|[a-zA-Z0-9]{20,})(\})"

    def replace_new_api_key(match):
        prefix = match.group(1)
        api_value = match.group(2)
        suffix = match.group(3)

        # 如果包含真实的API密钥（长度 > 10），则脱敏
        if len(api_value) > 10:
            if api_value.startswith("sk-"):
                sanitized = "sk-***SANITIZED***"
            else:
                sanitized = "***SANITIZED***"
            return f"{prefix}{sanitized}{suffix}"
        else:
            return match.group(0)  # 保持原样

    # 执行新格式API密钥替换
    sanitized_content = re.sub(new_api_key_pattern, replace_new_api_key, sanitized_content)

    # 5. 匹配通用敏感信息占位符（避免占位符被误脱敏）
    # 保护格式如: YOUR_XXX_API_KEY 不被脱敏
    placeholder_pattern = r"(\s*(?:sk|api-key):\s*\$\{[^:]+:-)(YOUR_[A-Z_]+_(?:API_)?KEY)(\})"

    def protect_placeholder(match):
        # 占位符不需要脱敏，保持原样
        return match.group(0)

    # 这一步实际上不需要替换，只是为了明确逻辑
    # sanitized_content = re.sub(placeholder_pattern, protect_placeholder, sanitized_content)

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

    # 需要脱敏的配置文件列表（按重要性排序）
    config_files = []

    # 检查根目录config/（如果存在）
    root_config_dir = project_root / "config"
    if root_config_dir.exists():
        # 添加根目录配置文件
        for pattern in ["*.yml", "*.yaml", "*.template"]:
            config_files.extend(root_config_dir.glob(pattern))

    # 检查vertex_flow/config/目录
    vertex_config_dir = project_root / "vertex_flow" / "config"
    if vertex_config_dir.exists():
        # 添加vertex_flow配置文件
        for pattern in ["*.yml", "*.yaml", "*.template"]:
            config_files.extend(vertex_config_dir.glob(pattern))

    # 如果没有找到配置文件，使用默认列表
    if not config_files:
        config_files = [
            # 新的配置文件位置（优先级高）
            project_root / "vertex_flow" / "config" / "llm.yml.template",
            # 可以添加其他需要脱敏的配置文件
        ]

    print("🔒 开始配置文件脱敏处理...")

    sanitized_count = 0
    total_files = 0

    for config_file in config_files:
        if config_file.exists():
            total_files += 1
            if sanitize_file(str(config_file)):
                sanitized_count += 1
        else:
            print(f"⚠ 配置文件不存在: {config_file}")

    print(f"\n📊 处理统计:")
    print(f"   检查的文件: {total_files}")
    print(f"   脱敏的文件: {sanitized_count}")

    if sanitized_count > 0:
        print(f"\n✓ 共对 {sanitized_count} 个配置文件进行了脱敏处理")
        print("请检查脱敏结果，确认无误后再提交")
    else:
        print("\n- 所有配置文件均无需脱敏或已经脱敏")


if __name__ == "__main__":
    main()
