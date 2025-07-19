#!/usr/bin/env python3
"""测试统一工具管理器的功能"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# 添加项目路径
sys.path.insert(0, "/Users/wjf/workspaces/localqwen")

from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall
from vertex_flow.workflow.tools.tool_manager import MCPToolExecutor, RegularToolExecutor, ToolCallResult, ToolManager


class TestUnifiedToolManager(unittest.TestCase):
    """测试统一工具管理器"""

    def setUp(self):
        """设置测试环境"""
        self.context = WorkflowContext()
        self.mock_tool_caller = Mock()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        self.manager = ToolManager(self.mock_tool_caller, self.tools)

    def test_tool_call_result(self):
        """测试工具调用结果封装"""
        # 成功的结果
        success_result = ToolCallResult("call_123", "Success content", success=True)
        message = success_result.to_message()

        self.assertEqual(message["role"], "tool")
        self.assertEqual(message["tool_call_id"], "call_123")
        self.assertEqual(message["content"], "Success content")

        # 失败的结果
        error_result = ToolCallResult("call_456", "Error content", success=False, error="Test error")
        error_message = error_result.to_message()

        self.assertEqual(error_message["role"], "tool")
        self.assertEqual(error_message["tool_call_id"], "call_456")
        self.assertEqual(error_message["content"], "Error: Test error")

    def test_mcp_tool_executor_can_handle(self):
        """测试MCP工具执行器的工具识别"""
        executor = MCPToolExecutor()

        self.assertTrue(executor.can_handle("mcp_test_tool"))
        self.assertFalse(executor.can_handle("regular_tool"))

    @patch("vertex_flow.workflow.mcp_manager.get_mcp_manager")
    def test_mcp_tool_executor_error_handling(self, mock_get_mcp_manager):
        """测试MCPToolExecutor的错误处理机制"""

        # 创建执行器
        executor = MCPToolExecutor()

        # 创建工具调用对象
        tool_call_dict = {
            "id": "call_test_error",
            "type": "function",
            "function": {"name": "mcp_error_tool", "arguments": '{"test": "value"}'},
        }
        tool_call = RuntimeToolCall(tool_call_dict)

        # 场景1：测试MCP工具返回错误结果
        mock_manager = Mock()
        mock_error_result = Mock()
        mock_error_result.content = [{"type": "text", "text": "Tool execution failed: Invalid arguments"}]
        mock_error_result.isError = True
        mock_manager.call_tool.return_value = mock_error_result
        mock_get_mcp_manager.return_value = mock_manager

        result = executor.execute_tool_call(tool_call, self.context)

        # 验证错误结果的正确处理
        self.assertFalse(result.success)  # 应该标记为失败
        self.assertEqual(result.tool_call_id, "call_test_error")
        self.assertIn("Tool execution failed: Invalid arguments", result.content)

        # 验证错误消息格式
        message = result.to_message()
        self.assertEqual(message["role"], "tool")
        self.assertEqual(message["tool_call_id"], "call_test_error")
        self.assertIn("Error:", message["content"])  # 应该有Error前缀

        # 场景2：测试MCP工具返回成功结果
        mock_success_result = Mock()
        mock_success_result.content = [{"type": "text", "text": "Operation completed successfully"}]
        mock_success_result.isError = False
        mock_manager.call_tool.return_value = mock_success_result

        result = executor.execute_tool_call(tool_call, self.context)

        # 验证成功结果的正确处理
        self.assertTrue(result.success)  # 应该标记为成功
        self.assertEqual(result.tool_call_id, "call_test_error")
        self.assertEqual(result.content, "Operation completed successfully")

        # 验证成功消息格式
        message = result.to_message()
        self.assertEqual(message["role"], "tool")
        self.assertEqual(message["content"], "Operation completed successfully")  # 没有Error前缀

    def test_regular_tool_executor_can_handle(self):
        """测试常规工具执行器的工具识别"""
        executor = RegularToolExecutor()

        self.assertTrue(executor.can_handle("regular_tool"))
        self.assertFalse(executor.can_handle("mcp_test_tool"))

    def test_create_assistant_message_with_tool_caller(self):
        """测试使用tool_caller创建assistant消息"""
        # 模拟choice对象
        mock_choice = Mock()
        mock_choice.message = Mock()
        mock_choice.message.content = "Test content"
        mock_choice.message.tool_calls = []

        # 配置mock_tool_caller
        expected_message = {"role": "assistant", "content": "Test content", "tool_calls": []}
        self.mock_tool_caller.create_assistant_message.return_value = expected_message

        result = self.manager.create_assistant_message(mock_choice)

        self.mock_tool_caller.create_assistant_message.assert_called_once_with(mock_choice)
        self.assertEqual(result, expected_message)

    def test_create_assistant_message_manual(self):
        """测试手动创建assistant消息"""
        # 测试工具调用列表
        tool_calls = [
            {"id": "call_123", "type": "function", "function": {"name": "test_tool", "arguments": '{"param": "value"}'}}
        ]

        # 不使用tool_caller
        manager_no_caller = ToolManager(None, self.tools)
        result = manager_no_caller.create_assistant_message(tool_calls)

        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["content"], "")  # 现在应该是空字符串而不是None
        self.assertEqual(len(result["tool_calls"]), 1)
        self.assertEqual(result["tool_calls"][0]["id"], "call_123")
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "test_tool")

    def test_execute_tool_calls_with_regular_tool(self):
        """测试执行常规工具调用"""
        tool_calls = [
            {"id": "call_123", "type": "function", "function": {"name": "test_tool", "arguments": '{"param": "value"}'}}
        ]

        # 配置mock_tool_caller
        mock_tool_result = {"role": "tool", "tool_call_id": "call_123", "content": "Tool executed successfully"}
        self.mock_tool_caller.execute_tool_calls_sync.return_value = [mock_tool_result]

        results = self.manager.execute_tool_calls(tool_calls, self.context)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["role"], "tool")
        self.assertEqual(results[0]["tool_call_id"], "call_123")
        self.assertEqual(results[0]["content"], "Tool executed successfully")

    @patch("vertex_flow.workflow.mcp_manager.get_mcp_manager")
    def test_execute_tool_calls_with_mcp_tool(self, mock_get_mcp_manager):
        """测试执行MCP工具调用"""
        tool_calls = [
            {
                "id": "call_456",
                "type": "function",
                "function": {"name": "mcp_test_tool", "arguments": '{"param": "value"}'},
            }
        ]

        # 模拟MCP管理器
        mock_manager = Mock()
        mock_result = Mock()
        mock_result.content = "MCP tool result"
        mock_result.isError = False  # 标记为成功结果
        mock_manager.call_tool.return_value = mock_result
        mock_get_mcp_manager.return_value = mock_manager

        results = self.manager.execute_tool_calls(tool_calls, self.context)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["role"], "tool")
        self.assertEqual(results[0]["tool_call_id"], "call_456")
        self.assertEqual(results[0]["content"], "MCP tool result")

        # 验证MCP工具被正确调用（移除mcp_前缀）
        mock_manager.call_tool.assert_called_once_with("test_tool", {"param": "value"})

    @patch("vertex_flow.workflow.mcp_manager.get_mcp_manager")
    def test_execute_tool_calls_with_mcp_tool_error(self, mock_get_mcp_manager):
        """测试执行MCP工具调用失败的情况"""
        tool_calls = [
            {
                "id": "call_error",
                "type": "function",
                "function": {"name": "mcp_failing_tool", "arguments": '{"param": "value"}'},
            }
        ]

        # 模拟MCP管理器返回错误结果
        mock_manager = Mock()
        mock_error_result = Mock()
        mock_error_result.content = [{"type": "text", "text": "MCP Error: Required parameter missing"}]
        mock_error_result.isError = True  # 标记为错误结果
        mock_manager.call_tool.return_value = mock_error_result
        mock_get_mcp_manager.return_value = mock_manager

        results = self.manager.execute_tool_calls(tool_calls, self.context)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["role"], "tool")
        self.assertEqual(results[0]["tool_call_id"], "call_error")
        # 验证错误消息格式：应该包含 "Error:" 前缀
        self.assertIn("Error:", results[0]["content"])
        self.assertIn("MCP Error: Required parameter missing", results[0]["content"])

        # 验证MCP工具被正确调用
        mock_manager.call_tool.assert_called_once_with("failing_tool", {"param": "value"})

    @patch("vertex_flow.workflow.mcp_manager.get_mcp_manager")
    def test_execute_tool_calls_with_mcp_tool_complex_error(self, mock_get_mcp_manager):
        """测试执行MCP工具调用复杂错误情况"""
        tool_calls = [
            {
                "id": "call_complex_error",
                "type": "function",
                "function": {"name": "mcp_complex_tool", "arguments": "{}"},
            }
        ]

        # 模拟MCP管理器返回复杂错误结果
        mock_manager = Mock()
        mock_error_result = Mock()
        mock_error_result.content = [
            {"type": "text", "text": "Validation failed"},
            {"type": "text", "text": "Parameter 'required_field' is missing"},
        ]
        mock_error_result.isError = True
        mock_manager.call_tool.return_value = mock_error_result
        mock_get_mcp_manager.return_value = mock_manager  # 这里应该返回mock_manager而不是mock_error_result

        results = self.manager.execute_tool_calls(tool_calls, self.context)

        self.assertEqual(len(results), 1)
        result_message = results[0]

        self.assertEqual(result_message["role"], "tool")
        self.assertEqual(result_message["tool_call_id"], "call_complex_error")

        # 验证复杂错误消息被正确合并和格式化
        content = result_message["content"]
        self.assertIn("Error:", content)
        self.assertIn("Validation failed", content)
        self.assertIn("Parameter 'required_field' is missing", content)

    @patch("vertex_flow.workflow.mcp_manager.get_mcp_manager")
    def test_execute_tool_calls_with_mcp_tool_no_content(self, mock_get_mcp_manager):
        """测试MCP工具返回空内容的情况"""
        tool_calls = [
            {
                "id": "call_empty",
                "type": "function",
                "function": {"name": "mcp_empty_tool", "arguments": "{}"},
            }
        ]

        # 模拟MCP管理器返回空内容的成功结果
        mock_manager = Mock()
        mock_empty_result = Mock()
        mock_empty_result.content = []  # 空内容
        mock_empty_result.isError = False
        mock_manager.call_tool.return_value = mock_empty_result
        mock_get_mcp_manager.return_value = mock_manager

        results = self.manager.execute_tool_calls(tool_calls, self.context)

        self.assertEqual(len(results), 1)
        result_message = results[0]

        self.assertEqual(result_message["role"], "tool")
        self.assertEqual(result_message["tool_call_id"], "call_empty")
        # 应该返回默认的成功消息
        self.assertEqual(result_message["content"], "Tool executed successfully but returned no content")

    def test_handle_tool_calls_complete(self):
        """测试完整的工具调用处理"""
        # 模拟choice对象
        mock_choice = Mock()
        mock_choice.message = Mock()
        mock_choice.message.content = "I'll use a tool"
        mock_choice.message.tool_calls = [
            {"id": "call_123", "type": "function", "function": {"name": "test_tool", "arguments": '{"param": "value"}'}}
        ]

        # 配置mock_tool_caller
        assistant_message = {
            "role": "assistant",
            "content": "I'll use a tool",
            "tool_calls": mock_choice.message.tool_calls,
        }
        tool_result = {"role": "tool", "tool_call_id": "call_123", "content": "Tool executed successfully"}

        self.mock_tool_caller.create_assistant_message.return_value = assistant_message
        self.mock_tool_caller.execute_tool_calls_sync.return_value = [tool_result]

        messages = []
        success = self.manager.handle_tool_calls_complete(mock_choice, self.context, messages)

        self.assertTrue(success)
        self.assertEqual(len(messages), 2)  # assistant + tool message
        self.assertEqual(messages[0]["role"], "assistant")
        self.assertEqual(messages[1]["role"], "tool")

    def test_handle_tool_calls_complete_avoid_duplicate(self):
        """测试避免重复的assistant消息"""
        # 模拟已存在相同的assistant消息
        existing_tool_calls = [
            {"id": "call_123", "type": "function", "function": {"name": "test_tool", "arguments": '{"param": "value"}'}}
        ]

        messages = [{"role": "assistant", "content": "I'll use a tool", "tool_calls": existing_tool_calls}]

        # 模拟相同的choice对象
        mock_choice = Mock()
        mock_choice.message = Mock()
        mock_choice.message.content = "I'll use a tool"
        mock_choice.message.tool_calls = existing_tool_calls

        # 配置mock_tool_caller
        tool_result = {"role": "tool", "tool_call_id": "call_123", "content": "Tool executed successfully"}
        self.mock_tool_caller.execute_tool_calls_sync.return_value = [tool_result]

        success = self.manager.handle_tool_calls_complete(mock_choice, self.context, messages)

        self.assertTrue(success)
        # 应该只添加了tool消息，没有重复的assistant消息
        self.assertEqual(len(messages), 2)  # 原有assistant + 新的tool message
        self.assertEqual(messages[0]["role"], "assistant")  # 原有的
        self.assertEqual(messages[1]["role"], "tool")  # 新添加的

    def test_update_tools(self):
        """测试更新工具列表"""
        new_tools = [
            {
                "type": "function",
                "function": {
                    "name": "new_tool",
                    "description": "A new tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        self.manager.update_tools(new_tools)
        self.assertEqual(self.manager.tools, new_tools)


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
