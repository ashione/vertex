#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词使用示例

展示如何使用提示词管理系统获取和格式化提示词。
"""

from vertex_flow.prompts import DeepResearchPrompts, format_prompt, get_prompt


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")

    # 直接获取提示词
    system_prompt = get_prompt("deep_research", "system", "topic_analysis")
    if system_prompt:
        print(f"系统提示词长度: {len(system_prompt)}")
        print(f"前100字符: {system_prompt[:100]}...")
    else:
        print("未找到系统提示词")

    # 格式化提示词
    variables = {"source": "人工智能在医疗领域的应用"}
    formatted_prompt = format_prompt("deep_research", "user", "topic_analysis", variables)
    if formatted_prompt:
        print(f"\n格式化后的用户提示词:")
        print(formatted_prompt)
    else:
        print("格式化提示词失败")


def example_direct_class_usage():
    """直接使用类的示例"""
    print("\n=== 直接使用类示例 ===")

    prompts = DeepResearchPrompts()

    # 获取所有可用的提示词
    available_prompts = prompts.list_available_prompts()
    print("可用的提示词:")
    for prompt_type, names in available_prompts.items():
        print(f"  {prompt_type}: {names}")

    # 验证变量
    template = prompts.get_topic_analysis_user_prompt()
    if template:
        variables = {"source": "区块链技术"}
        validation = prompts.validate_variables(template, variables)
        print(f"\n变量验证结果: {validation}")


def example_workflow_integration():
    """工作流集成示例"""
    print("\n=== 工作流集成示例 ===")

    # 模拟深度研究工作流的提示词使用
    workflow_steps = [
        ("topic_analysis", {"source": "量子计算的发展前景"}),
        ("analysis_plan", {"topic_analysis": "这是主题分析的结果..."}),
        ("information_collection", {"analysis_plan": "这是研究规划的结果..."}),
    ]

    for step_name, variables in workflow_steps:
        system_prompt = get_prompt("deep_research", "system", step_name)
        user_prompt = format_prompt("deep_research", "user", step_name, variables)

        print(f"\n步骤: {step_name}")
        if system_prompt:
            print(f"系统提示词长度: {len(system_prompt)}")
        if user_prompt:
            print(f"用户提示词: {user_prompt[:100]}...")


def example_prompt_management():
    """提示词管理示例"""
    print("\n=== 提示词管理示例 ===")

    prompts = DeepResearchPrompts()

    # 缓存提示词
    system_prompt = prompts.get_topic_analysis_system_prompt()
    if system_prompt:
        prompts.cache_prompt("topic_analysis_system", system_prompt)

        # 从缓存获取
        cached_prompt = prompts.get_cached_prompt("topic_analysis_system")
        print(f"缓存命中: {cached_prompt is not None}")

        # 清除缓存
        prompts.clear_cache()
        cached_prompt = prompts.get_cached_prompt("topic_analysis_system")
        print(f"清除后缓存命中: {cached_prompt is not None}")


if __name__ == "__main__":
    example_basic_usage()
    example_direct_class_usage()
    example_workflow_integration()
    example_prompt_management()
