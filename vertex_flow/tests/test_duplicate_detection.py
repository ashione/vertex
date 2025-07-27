#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重复调用检测功能
针对DeepSeek等非OpenAI原生Tool Calling模型的重复调用检测
"""

import json
import logging
from unittest.mock import MagicMock, Mock

from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall
from vertex_flow.workflow.tools.tool_manager import ToolCallResult, ToolManager

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_duplicate_call_detection():
    """测试重复调用检测功能"""
    print("\n=== 测试重复调用检测功能 ===")

    # 创建工具管理器
    tool_manager = ToolManager()

    # 模拟上下文
    context = Mock(spec=WorkflowContext)

    # 创建相同的工具调用（模拟DeepSeek重复调用场景）
    def create_tool_call(call_id: str, city: str = ""):
        return RuntimeToolCall(
            {
                "id": call_id,
                "type": "function",
                "function": {"name": "get_weather", "arguments": json.dumps({"city": city})},
            }
        )

    # 测试1: 正常调用（不重复）
    print("\n1. 测试正常调用（不重复）")
    tool_call1 = create_tool_call("call_1", "北京")
    warning1 = tool_manager._check_duplicate_call(tool_call1)
    print(f"第一次调用警告: {warning1}")
    assert warning1 is None, "第一次调用不应该有警告"

    tool_manager._record_tool_call(tool_call1)

    # 测试2: 不同参数的调用（不重复）
    print("\n2. 测试不同参数的调用（不重复）")
    tool_call2 = create_tool_call("call_2", "上海")
    warning2 = tool_manager._check_duplicate_call(tool_call2)
    print(f"不同参数调用警告: {warning2}")
    assert warning2 is None, "不同参数的调用不应该有警告"

    tool_manager._record_tool_call(tool_call2)

    # 测试3: 相同参数的重复调用（应该检测到）
    print("\n3. 测试相同参数的重复调用")
    tool_call3 = create_tool_call("call_3", "北京")
    warning3 = tool_manager._check_duplicate_call(tool_call3)
    print(f"重复调用警告: {warning3}")
    assert warning3 is not None, "重复调用应该有警告"
    assert "重复调用" in warning3, "警告信息应该包含'重复调用'"

    tool_manager._record_tool_call(tool_call3)

    # 测试4: 空参数的重复调用（DeepSeek常见场景）
    print("\n4. 测试空参数的重复调用（DeepSeek常见场景）")
    empty_call1 = create_tool_call("call_4", "")
    tool_manager._record_tool_call(empty_call1)

    empty_call2 = create_tool_call("call_5", "")
    warning4 = tool_manager._check_duplicate_call(empty_call2)
    print(f"空参数重复调用警告: {warning4}")
    assert warning4 is not None, "空参数重复调用应该有警告"

    tool_manager._record_tool_call(empty_call2)

    # 测试5: 连续重复调用阻止逻辑
    print("\n5. 测试连续重复调用阻止逻辑")
    # 添加更多相同的调用以触发阻止逻辑
    for i in range(3):
        empty_call = create_tool_call(f"call_block_{i}", "")
        tool_manager._record_tool_call(empty_call)

    # 现在应该阻止重复调用
    final_empty_call = create_tool_call("call_final", "")
    should_block = tool_manager._should_block_duplicate_call(final_empty_call)
    print(f"是否应该阻止重复调用: {should_block}")
    assert should_block, "连续重复调用应该被阻止"

    print("\n✅ 重复调用检测功能测试通过！")


def test_duplicate_warning_generation():
    """测试重复调用警告信息生成"""
    print("\n=== 测试重复调用警告信息生成 ===")

    tool_manager = ToolManager()

    # 测试不同类型的重复调用警告
    test_cases = [
        {"name": "get_weather", "args": {"city": ""}, "expected_keywords": ["为空", "city", "建议"]},
        {"name": "search_file", "args": {"query": ""}, "expected_keywords": ["为空", "query", "建议"]},
        {"name": "get_weather", "args": {"city": "北京"}, "expected_keywords": ["重复调用", "建议", "分析"]},
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. 测试 {case['name']} 工具的警告生成")

        tool_call = RuntimeToolCall(
            {
                "id": f"test_{i}",
                "type": "function",
                "function": {"name": case["name"], "arguments": json.dumps(case["args"])},
            }
        )

        warning = tool_manager._generate_duplicate_warning(tool_call, 1)
        print(f"生成的警告: {warning}")

        # 检查警告是否包含预期的关键词
        for keyword in case["expected_keywords"]:
            assert keyword in warning, f"警告信息应该包含关键词: {keyword}"

    print("\n✅ 重复调用警告信息生成测试通过！")


def test_call_history_management():
    """测试调用历史管理"""
    print("\n=== 测试调用历史管理 ===")

    tool_manager = ToolManager()

    # 测试历史记录限制
    print(f"最大历史记录数量: {tool_manager.max_history_size}")

    # 添加超过最大数量的调用记录
    for i in range(tool_manager.max_history_size + 5):
        tool_call = RuntimeToolCall(
            {
                "id": f"call_{i}",
                "type": "function",
                "function": {"name": "test_tool", "arguments": json.dumps({"param": f"value_{i}"})},
            }
        )
        tool_manager._record_tool_call(tool_call)

    # 检查历史记录是否被正确限制
    print(f"当前历史记录数量: {len(tool_manager.call_history)}")
    assert len(tool_manager.call_history) <= tool_manager.max_history_size, "历史记录数量不应超过最大限制"

    # 检查最新的记录是否被保留
    latest_call = tool_manager.call_history[-1]
    print(f"最新调用记录: {latest_call}")
    assert "value_" in latest_call[0], "最新的调用记录应该被保留"

    print("\n✅ 调用历史管理测试通过！")


def main():
    """运行所有测试"""
    print("开始测试DeepSeek重复调用检测功能...")

    try:
        test_duplicate_call_detection()
        test_duplicate_warning_generation()
        test_call_history_management()

        print("\n🎉 所有测试通过！重复调用检测功能正常工作。")
        print("\n功能特点:")
        print("- ✅ 检测相同工具名和参数的重复调用")
        print("- ✅ 特别处理空参数的重复调用（DeepSeek常见问题）")
        print("- ✅ 生成明确的警告信息指导模型修正参数")
        print("- ✅ 连续重复调用阻止机制")
        print("- ✅ 调用历史管理和限制")
        print("- ✅ 针对DeepSeek等非OpenAI原生Tool Calling模型优化")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        raise


if __name__ == "__main__":
    main()
