#!/usr/bin/env python3
"""
测试 tool_caller 集成到 LLMVertex 和 MCPLLMVertex 的功能
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.tools.tool_caller import create_tool_caller
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex
from vertex_flow.workflow.vertex.vertex import WorkflowContext


def test_tool_caller_integration():
    """测试 tool_caller 集成功能"""
    print("=== 测试 tool_caller 集成 ===")

    # 创建一个简单的工具
    from vertex_flow.workflow.tools.functions import FunctionTool

    def test_tool_func(message: str) -> str:
        """测试工具函数"""
        return f"工具调用成功: {message}"

    test_tool = FunctionTool(
        name="test_tool",
        description="测试工具",
        func=test_tool_func,
        schema={
            "type": "object",
            "properties": {"message": {"type": "string", "description": "测试消息"}},
            "required": ["message"],
        },
    )

    tools = [test_tool]

    # 创建 tool_caller
    tool_caller = create_tool_caller("openai")

    # 创建一个模拟的 ChatModel
    class MockChatModel(ChatModel):
        def __init__(self):
            super().__init__(name="mock", sk="mock", base_url="mock", provider="mock")

        def chat(self, messages, **kwargs):
            return "模拟响应"

    model = MockChatModel()

    # 测试 LLMVertex 集成
    print("\n1. 测试 LLMVertex 集成:")
    try:
        llm_vertex = LLMVertex(
            id="test_llm",
            name="测试LLM",
            model=model,
            tools=tools,
            tool_caller=tool_caller,
            params={"enable_stream": False},
        )

        print(f"✓ LLMVertex 创建成功，tool_caller: {llm_vertex.tool_caller is not None}")
        print(f"✓ 工具数量: {len(llm_vertex.tools)}")

    except Exception as e:
        print(f"✗ LLMVertex 集成失败: {e}")
        llm_vertex = None

    # 测试 MCPLLMVertex 集成
    print("\n2. 测试 MCPLLMVertex 集成:")
    try:
        mcp_llm_vertex = MCPLLMVertex(
            id="test_mcp_llm",
            name="测试MCP LLM",
            model=model,
            tools=tools,
            tool_caller=tool_caller,
            params={"enable_stream": False},
            mcp_enabled=True,
        )

        print(f"✓ MCPLLMVertex 创建成功，tool_caller: {mcp_llm_vertex.tool_caller is not None}")
        print(f"✓ 工具数量: {len(mcp_llm_vertex.tools)}")
        print(f"✓ MCP 启用状态: {mcp_llm_vertex.mcp_enabled}")

    except Exception as e:
        print(f"✗ MCPLLMVertex 集成失败: {e}")
        mcp_llm_vertex = None

    # 测试 _build_llm_tools 方法
    print("\n3. 测试工具构建:")
    try:
        if llm_vertex:
            llm_tools = llm_vertex._build_llm_tools()
            print(f"✓ LLMVertex 工具构建成功，工具数量: {len(llm_tools) if llm_tools else 0}")

            # 检查 tool_caller 的工具列表是否同步
            if llm_vertex.tool_caller:
                print(f"✓ LLMVertex tool_caller 工具同步: {llm_vertex.tool_caller.tools == llm_vertex.tools}")
        else:
            print("✗ LLMVertex 未创建成功，跳过工具构建测试")

        if mcp_llm_vertex:
            mcp_tools = mcp_llm_vertex._build_llm_tools()
            print(f"✓ MCPLLMVertex 工具构建成功，工具数量: {len(mcp_tools) if mcp_tools else 0}")

            # 检查 tool_caller 的工具列表是否同步
            if mcp_llm_vertex.tool_caller:
                print(
                    f"✓ MCPLLMVertex tool_caller 工具同步: {mcp_llm_vertex.tool_caller.tools == mcp_llm_vertex.tools}"
                )
        else:
            print("✗ MCPLLMVertex 未创建成功，跳过工具构建测试")

    except Exception as e:
        print(f"✗ 工具构建测试失败: {e}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_tool_caller_integration()
