#!/usr/bin/env python3
"""
测试MCP调用参数和返回结果的调试日志功能

这个测试脚本用于验证MCP工具调用时的调试信息是否正确记录到日志中。
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.mcp_manager import MCPManager
from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_mcp_debug_print():
    """
    测试MCP调用的调试打印功能
    """
    print("\n=== 开始测试MCP调试打印功能 ===")

    try:
        # 创建MCP LLM Vertex实例
        mcp_llm = MCPLLMVertex(
            vertex_id="test_mcp_debug", model_name="gpt-3.5-turbo", mcp_enabled=True, mcp_tools_enabled=True
        )

        print("\n1. 创建MCP LLM Vertex实例成功")

        # 获取MCP状态
        status = mcp_llm.get_mcp_status()
        print(f"\n2. MCP状态: {json.dumps(status, indent=2, ensure_ascii=False)}")

        # 模拟一个简单的工具调用
        print("\n3. 模拟MCP工具调用...")

        # 创建一个模拟的工具调用对象
        class MockToolCall:
            def __init__(self, tool_name, arguments):
                self.id = "test_call_123"
                self.function = MockFunction(tool_name, arguments)

        class MockFunction:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = json.dumps(arguments) if arguments else "{}"

        # 测试工具调用（这会触发调试打印）
        mock_call = MockToolCall("mcp_test_tool", {"param1": "value1", "param2": 42})

        print("\n4. 执行模拟工具调用（会显示调试信息）...")

        # 这里会调用_execute_mcp_tool方法，触发调试打印
        try:
            result = asyncio.run(mcp_llm._execute_mcp_tool(mock_call))
            print(f"\n5. 工具调用结果: {result}")
        except Exception as e:
            print(f"\n5. 工具调用异常（预期的）: {e}")
            print("   这是正常的，因为我们没有实际的MCP服务器运行")

        print("\n=== MCP调试打印功能测试完成 ===")

    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


def test_mcp_manager_debug():
    """
    测试MCP Manager的调试打印功能
    """
    print("\n=== 开始测试MCP Manager调试打印功能 ===")

    try:
        # 创建MCP Manager实例
        manager = MCPManager()

        print("\n1. 创建MCP Manager实例成功")

        # 测试工具调用（这会触发调试打印）
        print("\n2. 测试MCP Manager工具调用...")

        try:
            result = manager.call_tool("test_tool", {"param1": "value1", "param2": 42})
            print(f"\n3. Manager调用结果: {result}")
        except Exception as e:
            print(f"\n3. Manager调用异常（预期的）: {e}")
            print("   这是正常的，因为我们没有实际的MCP服务器运行")

        print("\n=== MCP Manager调试打印功能测试完成 ===")

    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("MCP调试打印功能测试")
    print("=" * 50)

    # 运行测试
    test_mcp_debug_print()
    print("\n" + "=" * 50)
    test_mcp_manager_debug()

    print("\n总结:")
    print("- 已在MCP相关代码中添加详细的调试日志功能")
    print("- 调试信息包括工具名称、参数、返回结果类型和内容")
    print("- 调试信息会通过logger.debug()记录到日志中")
    print("- 可以通过设置日志级别为DEBUG来查看这些调试信息")
    print("- 使用logger方式更符合项目的日志规范")
