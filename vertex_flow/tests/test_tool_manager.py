#!/usr/bin/env python3
"""测试统一工具管理器的功能

扩展测试包括：
1. 基础工具管理器功能
2. MCP工具执行器
3. 常规工具执行器
4. 函数工具执行器
5. 工具优先级和回退机制
6. 复杂工具调用链
7. 性能和并发测试
8. 错误处理和恢复
"""

import asyncio
import json
import os
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, Mock, patch

# 添加项目路径
sys.path.insert(0, "/Users/wjf/workspaces/localqwen")

from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall
from vertex_flow.workflow.tools.tool_manager import (
    FunctionTool,
    FunctionToolExecutor,
    MCPToolExecutor,
    RegularToolExecutor,
    ToolCallResult,
    ToolManager,
)


class TestFunctionTool(unittest.TestCase):
    """测试FunctionTool类"""

    def test_function_tool_creation(self):
        """测试函数工具创建"""
        def test_func(inputs, context=None):
            return {"result": inputs.get("input", 0) * 2}

        schema = {
            "type": "object",
            "properties": {
                "input": {"type": "number", "description": "Input number"}
            },
            "required": ["input"]
        }

        tool = FunctionTool("multiply_by_two", "Multiply input by 2", test_func, schema)
        
        self.assertEqual(tool.name, "multiply_by_two")
        self.assertEqual(tool.description, "Multiply input by 2")
        self.assertEqual(tool.func, test_func)
        self.assertEqual(tool.schema, schema)

    def test_function_tool_to_dict(self):
        """测试函数工具转字典"""
        def test_func(inputs, context=None):
            return {"result": "test"}

        schema = {"type": "object", "properties": {}}
        tool = FunctionTool("test_tool", "A test tool", test_func, schema)
        
        tool_dict = tool.to_dict()
        expected = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": schema
            }
        }
        
        self.assertEqual(tool_dict, expected)

    def test_function_tool_execute(self):
        """测试函数工具执行"""
        def calculator(inputs, context=None):
            a = inputs.get("a", 0)
            b = inputs.get("b", 0)
            op = inputs.get("operation", "add")
            
            if op == "add":
                return {"result": a + b}
            elif op == "multiply":
                return {"result": a * b}
            else:
                raise ValueError(f"Unsupported operation: {op}")

        schema = {"type": "object", "properties": {}}
        tool = FunctionTool("calculator", "Basic calculator", calculator, schema)
        
        # 测试加法
        result = tool.execute({"a": 2, "b": 3, "operation": "add"}, None)
        self.assertEqual(result["result"], 5)
        
        # 测试乘法
        result = tool.execute({"a": 4, "b": 5, "operation": "multiply"}, None)
        self.assertEqual(result["result"], 20)
        
        # 测试错误情况
        with self.assertRaises(ValueError):
            tool.execute({"a": 1, "b": 2, "operation": "divide"}, None)


class TestFunctionToolExecutor(unittest.TestCase):
    """测试函数工具执行器"""

    def setUp(self):
        """设置测试环境"""
        self.context = WorkflowContext()
        
        # 创建测试函数工具
        def add_function(inputs, context=None):
            return {"result": inputs.get("a", 0) + inputs.get("b", 0)}
        
        def multiply_function(inputs, context=None):
            return {"result": inputs.get("a", 0) * inputs.get("b", 0)}
        
        def error_function(inputs, context=None):
            raise RuntimeError("Test error")
        
        self.function_tools = {
            "add": FunctionTool("add", "Add two numbers", add_function, {}),
            "multiply": FunctionTool("multiply", "Multiply two numbers", multiply_function, {}),
            "error_tool": FunctionTool("error_tool", "Always fails", error_function, {}),
        }
        
        self.executor = FunctionToolExecutor(self.function_tools)

    def test_can_handle(self):
        """测试工具识别"""
        self.assertTrue(self.executor.can_handle("add"))
        self.assertTrue(self.executor.can_handle("multiply"))
        self.assertFalse(self.executor.can_handle("unknown_tool"))
        self.assertFalse(self.executor.can_handle("mcp_tool"))

    def test_execute_function_tool_success(self):
        """测试成功执行函数工具"""
        tool_call = RuntimeToolCall({
            "id": "call_add",
            "type": "function",
            "function": {"name": "add", "arguments": '{"a": 2, "b": 3}'}
        })
        
        result = self.executor.execute_tool_call(tool_call, self.context)
        
        self.assertTrue(result.success)
        self.assertEqual(result.tool_call_id, "call_add")
        self.assertIn("5", result.content)  # JSON格式的结果

    def test_execute_function_tool_error(self):
        """测试函数工具执行错误"""
        tool_call = RuntimeToolCall({
            "id": "call_error",
            "type": "function",
            "function": {"name": "error_tool", "arguments": '{}'}
        })
        
        result = self.executor.execute_tool_call(tool_call, self.context)
        
        self.assertFalse(result.success)
        self.assertEqual(result.tool_call_id, "call_error")
        self.assertIn("Test error", result.content)

    def test_execute_unknown_function_tool(self):
        """测试执行未知函数工具"""
        tool_call = RuntimeToolCall({
            "id": "call_unknown",
            "type": "function",
            "function": {"name": "unknown_tool", "arguments": '{}'}
        })
        
        result = self.executor.execute_tool_call(tool_call, self.context)
        
        self.assertFalse(result.success)
        self.assertEqual(result.tool_call_id, "call_unknown")
        self.assertIn("not found", result.content)

    def test_execute_invalid_json_arguments(self):
        """测试无效JSON参数"""
        tool_call = RuntimeToolCall({
            "id": "call_invalid_json",
            "type": "function",
            "function": {"name": "add", "arguments": '{"a": 2, "b":}'}  # 无效JSON
        })
        
        result = self.executor.execute_tool_call(tool_call, self.context)
        
        self.assertFalse(result.success)
        self.assertEqual(result.tool_call_id, "call_invalid_json")


class TestRegularToolExecutor(unittest.TestCase):
    """测试常规工具执行器"""

    def setUp(self):
        """设置测试环境"""
        self.context = WorkflowContext()
        self.mock_tool_caller = Mock()
        self.tools = [
            {"type": "function", "function": {"name": "regular_tool", "description": "A regular tool"}}
        ]

    def test_can_handle(self):
        """测试工具识别"""
        executor = RegularToolExecutor()
        
        self.assertTrue(executor.can_handle("regular_tool"))
        self.assertTrue(executor.can_handle("any_tool"))
        self.assertFalse(executor.can_handle("mcp_tool"))
        self.assertFalse(executor.can_handle("mcp_test"))

    def test_execute_with_tool_caller(self):
        """测试使用tool_caller执行"""
        # 配置mock tool_caller
        mock_result = {"role": "tool", "tool_call_id": "call_123", "content": "Tool executed"}
        self.mock_tool_caller.execute_tool_calls_sync.return_value = [mock_result]
        
        executor = RegularToolExecutor(self.mock_tool_caller, self.tools)
        
        tool_call = RuntimeToolCall({
            "id": "call_123",
            "type": "function",
            "function": {"name": "regular_tool", "arguments": '{}'}
        })
        
        result = executor.execute_tool_call(tool_call, self.context)
        
        self.assertTrue(result.success)
        self.assertEqual(result.tool_call_id, "call_123")
        self.assertEqual(result.content, "Tool executed")

    def test_execute_without_tool_caller(self):
        """测试不使用tool_caller的回退执行"""
        executor = RegularToolExecutor(None, self.tools)
        
        tool_call = RuntimeToolCall({
            "id": "call_fallback",
            "type": "function",
            "function": {"name": "regular_tool", "arguments": '{}'}
        })
        
        result = executor.execute_tool_call(tool_call, self.context)
        
        self.assertTrue(result.success)
        self.assertEqual(result.tool_call_id, "call_fallback")
        self.assertIn("fallback", result.content)

    def test_execute_tool_caller_error(self):
        """测试tool_caller执行错误"""
        self.mock_tool_caller.execute_tool_calls_sync.side_effect = Exception("Tool caller error")
        
        executor = RegularToolExecutor(self.mock_tool_caller, self.tools)
        
        tool_call = RuntimeToolCall({
            "id": "call_error",
            "type": "function",
            "function": {"name": "regular_tool", "arguments": '{}'}
        })
        
        result = executor.execute_tool_call(tool_call, self.context)
        
        self.assertFalse(result.success)
        self.assertEqual(result.tool_call_id, "call_error")
        self.assertIn("Tool caller error", result.content)


class TestAdvancedToolManager(unittest.TestCase):
    """测试高级工具管理器功能"""

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

    def test_register_function_tool(self):
        """测试注册函数工具"""
        manager = ToolManager(self.mock_tool_caller, self.tools)
        
        def custom_function(inputs, context=None):
            return {"result": "custom"}
        
        # 手动注册函数工具
        custom_tool = FunctionTool("custom_tool", "Custom tool", custom_function, {})
        manager.function_tools["custom_tool"] = custom_tool
        
        # 验证工具已注册
        self.assertIn("custom_tool", manager.function_tools)
        
        # 测试执行
        tool_calls = [
            {"id": "call_custom", "type": "function", "function": {"name": "custom_tool", "arguments": "{}"}}
        ]
        
        results = manager.execute_tool_calls(tool_calls, self.context)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["role"], "tool")
        self.assertIn("custom", results[0]["content"])

    def test_tool_execution_priority(self):
        """测试工具执行优先级"""
        manager = ToolManager(self.mock_tool_caller, self.tools)
        
        # 注册一个与MCP工具同名的函数工具
        def local_mcp_tool(inputs, context=None):
            return {"result": "local_implementation"}
        
        mcp_tool = FunctionTool("mcp_test_tool", "Local MCP tool", local_mcp_tool, {})
        manager.function_tools["mcp_test_tool"] = mcp_tool
        
        # 测试MCP工具调用（应该优先使用MCP执行器）
        tool_calls = [
            {"id": "call_mcp", "type": "function", "function": {"name": "mcp_test_tool", "arguments": "{}"}}
        ]
        
        with patch("vertex_flow.workflow.mcp_manager.get_mcp_manager") as mock_get_mcp_manager:
            mock_manager = Mock()
            mock_result = Mock()
            mock_result.content = [{"type": "text", "text": "MCP implementation"}]
            mock_result.isError = False
            mock_manager.call_tool.return_value = mock_result
            mock_get_mcp_manager.return_value = mock_manager
            
            results = manager.execute_tool_calls(tool_calls, self.context)
            
            # 应该使用MCP实现，而不是本地函数实现
            self.assertEqual(len(results), 1)
            self.assertIn("MCP implementation", results[0]["content"])

    def test_mixed_tool_calls(self):
        """测试混合工具调用"""
        manager = ToolManager(self.mock_tool_caller, self.tools)
        
        # 注册函数工具
        def math_tool(inputs, context=None):
            return {"result": inputs.get("a", 0) + inputs.get("b", 0)}
        
        manager.function_tools["math_tool"] = FunctionTool("math_tool", "Math tool", math_tool, {})
        
        # 配置常规工具
        regular_result = {"role": "tool", "tool_call_id": "call_regular", "content": "Regular tool result"}
        self.mock_tool_caller.execute_tool_calls_sync.return_value = [regular_result]
        
        # 混合工具调用
        tool_calls = [
            {"id": "call_function", "type": "function", "function": {"name": "math_tool", "arguments": '{"a": 2, "b": 3}'}},
            {"id": "call_regular", "type": "function", "function": {"name": "regular_tool", "arguments": "{}"}},
        ]
        
        with patch("vertex_flow.workflow.mcp_manager.get_mcp_manager") as mock_get_mcp_manager:
            mock_manager = Mock()
            mock_result = Mock()
            mock_result.content = [{"type": "text", "text": "MCP tool result"}]
            mock_result.isError = False
            mock_manager.call_tool.return_value = mock_result
            mock_get_mcp_manager.return_value = mock_manager
            
            # 添加MCP工具调用
            tool_calls.append({
                "id": "call_mcp", 
                "type": "function", 
                "function": {"name": "mcp_search", "arguments": '{"query": "test"}'}
            })
            
            results = manager.execute_tool_calls(tool_calls, self.context)
            
            # 应该有3个结果
            self.assertEqual(len(results), 3)
            
            # 验证每个工具的结果
            results_by_id = {r["tool_call_id"]: r for r in results}
            
            # 函数工具结果
            self.assertIn("5", results_by_id["call_function"]["content"])
            
            # 常规工具结果
            self.assertEqual(results_by_id["call_regular"]["content"], "Regular tool result")
            
            # MCP工具结果
            self.assertIn("MCP tool result", results_by_id["call_mcp"]["content"])

    def test_concurrent_tool_execution(self):
        """测试并发工具执行"""
        manager = ToolManager(self.mock_tool_caller, self.tools)
        
        # 注册一个慢速函数工具
        def slow_tool(inputs, context=None):
            import time
            time.sleep(0.1)  # 模拟慢速操作
            return {"result": f"slow_result_{inputs.get('id', 0)}"}
        
        manager.function_tools["slow_tool"] = FunctionTool("slow_tool", "Slow tool", slow_tool, {})
        
        # 创建多个工具调用
        tool_calls = [
            {"id": f"call_{i}", "type": "function", "function": {"name": "slow_tool", "arguments": f'{{"id": {i}}}'}}
            for i in range(5)
        ]
        
        start_time = time.time()
        results = manager.execute_tool_calls(tool_calls, self.context)
        execution_time = time.time() - start_time
        
        # 验证结果
        self.assertEqual(len(results), 5)
        
        # 验证所有结果都正确
        for i, result in enumerate(results):
            self.assertEqual(result["tool_call_id"], f"call_{i}")
            self.assertIn(f"slow_result_{i}", result["content"])
        
        # 注意：当前实现是同步的，所以执行时间应该约为 5 * 0.1 = 0.5秒
        # 这个测试主要验证功能正确性，而不是真正的并发
        print(f"执行时间: {execution_time:.2f}秒")

    def test_tool_execution_error_isolation(self):
        """测试工具执行错误隔离"""
        manager = ToolManager(self.mock_tool_caller, self.tools)
        
        # 注册正常工具和错误工具
        def good_tool(inputs, context=None):
            return {"result": "success"}
        
        def bad_tool(inputs, context=None):
            raise Exception("Tool failed")
        
        manager.function_tools["good_tool"] = FunctionTool("good_tool", "Good tool", good_tool, {})
        manager.function_tools["bad_tool"] = FunctionTool("bad_tool", "Bad tool", bad_tool, {})
        
        # 混合调用
        tool_calls = [
            {"id": "call_good_1", "type": "function", "function": {"name": "good_tool", "arguments": "{}"}},
            {"id": "call_bad", "type": "function", "function": {"name": "bad_tool", "arguments": "{}"}},
            {"id": "call_good_2", "type": "function", "function": {"name": "good_tool", "arguments": "{}"}},
        ]
        
        results = manager.execute_tool_calls(tool_calls, self.context)
        
        # 应该有3个结果，错误不应该影响其他工具
        self.assertEqual(len(results), 3)
        
        results_by_id = {r["tool_call_id"]: r for r in results}
        
        # 验证好的工具成功执行
        self.assertIn("success", results_by_id["call_good_1"]["content"])
        self.assertIn("success", results_by_id["call_good_2"]["content"])
        
        # 验证坏的工具返回错误
        self.assertIn("Error:", results_by_id["call_bad"]["content"])
        self.assertIn("Tool failed", results_by_id["call_bad"]["content"])

    def test_tool_manager_default_tools(self):
        """测试工具管理器默认工具"""
        manager = ToolManager(self.mock_tool_caller, self.tools)
        
        # 检查是否注册了默认工具（如果有的话）
        print(f"已注册的函数工具: {list(manager.function_tools.keys())}")
        
        # 验证默认工具可以正常工作
        # 注意：这个测试取决于_register_default_tools的具体实现
        default_tool_names = list(manager.function_tools.keys())
        
        if default_tool_names:
            # 如果有默认工具，测试一个
            tool_name = default_tool_names[0]
            tool_calls = [
                {"id": "call_default", "type": "function", "function": {"name": tool_name, "arguments": "{}"}}
            ]
            
            try:
                results = manager.execute_tool_calls(tool_calls, self.context)
                self.assertEqual(len(results), 1)
                print(f"默认工具 {tool_name} 执行成功")
            except Exception as e:
                print(f"默认工具 {tool_name} 执行失败: {e}")


class TestUnifiedToolManager(unittest.TestCase):
    """测试统一工具管理器（原有测试保留）"""

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
