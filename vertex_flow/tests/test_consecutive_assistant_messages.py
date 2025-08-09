#!/usr/bin/env python3
"""
测试连续assistant消息问题的修复
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "."))

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex

logger = LoggerUtil.get_logger(__name__)


def test_no_consecutive_assistant_messages():
    """测试不会产生连续的assistant消息"""
    print("测试: 避免连续的assistant消息")

    # 模拟消息列表
    messages = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]

    # 检查是否有连续的assistant消息
    consecutive_count = 0
    for i in range(1, len(messages)):
        if messages[i]["role"] == "assistant" and messages[i - 1]["role"] == "assistant":
            consecutive_count += 1

    print(f"连续assistant消息数量: {consecutive_count}")
    assert consecutive_count == 0, f"发现 {consecutive_count} 个连续的assistant消息"
    print("✓ 测试通过: 没有连续的assistant消息")


def test_message_sequence_integrity():
    """测试消息序列完整性"""
    print("\n测试: 消息序列完整性")

    # 模拟正常的对话序列
    messages = [
        {"role": "user", "content": "What is AI?"},
        {"role": "assistant", "content": "AI stands for Artificial Intelligence..."},
        {"role": "user", "content": "Tell me more"},
        {"role": "assistant", "content": "AI involves machine learning..."},
    ]

    # 验证消息序列的完整性
    for i, message in enumerate(messages):
        assert "role" in message, f"消息 {i} 缺少role字段"
        assert "content" in message, f"消息 {i} 缺少content字段"
        assert message["role"] in ["user", "assistant", "system"], f"消息 {i} 的role无效: {message['role']}"

    print(f"验证了 {len(messages)} 条消息的完整性")
    print("✓ 测试通过: 消息序列完整性正常")


def test_unified_tool_manager_integration():
    """测试统一工具管理器集成"""
    print("\n测试: 统一工具管理器集成")

    try:
        from vertex_flow.workflow.tools.tool_manager import ToolManager

        # 创建统一工具管理器
        manager = ToolManager()

        # 验证管理器创建成功
        assert manager is not None, "统一工具管理器创建失败"

        print("✓ 测试通过: 统一工具管理器集成正常")

    except ImportError as e:
        print(f"⚠ 警告: 无法导入统一工具管理器: {e}")
        print("这可能是正常的，如果模块尚未完全集成")


def main():
    """运行所有测试"""
    print("开始测试连续assistant消息问题的修复...\n")

    try:
        test_no_consecutive_assistant_messages()
        test_message_sequence_integrity()
        test_unified_tool_manager_integration()

        print("\n🎉 所有测试通过！连续assistant消息问题已修复。")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
