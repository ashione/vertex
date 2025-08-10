#!/usr/bin/env python3
"""
测试工作流历史记录功能

测试WorkflowInput中的历史记录支持是否正确工作。
"""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

# 导入需要测试的模块
try:
    from vertex_flow.workflow.app.app import WorkflowInput, create_llm_vertex
    from vertex_flow.workflow.constants import CONVERSATION_HISTORY
except ImportError:
    # 如果导入失败，跳过测试
    pytest.skip("App module not available", allow_module_level=True)


class TestWorkflowHistory:
    """测试工作流历史记录功能"""

    def test_workflow_input_with_empty_history(self):
        """测试空历史记录的WorkflowInput"""
        input_data = WorkflowInput(workflow_name="test", content="Hello", history=[])

        assert input_data.workflow_name == "test"
        assert input_data.content == "Hello"
        assert input_data.history == []
        assert isinstance(input_data.history, list)

    def test_workflow_input_with_history(self):
        """测试包含历史记录的WorkflowInput"""
        history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello! How can I help you?"}]

        input_data = WorkflowInput(workflow_name="chat", content="What's the weather?", history=history)

        assert input_data.workflow_name == "chat"
        assert input_data.content == "What's the weather?"
        assert input_data.history == history
        assert len(input_data.history) == 2

    def test_workflow_input_multimodal_history(self):
        """测试多模态历史记录"""
        multimodal_history = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
                ],
            },
            {"role": "assistant", "content": "I can see a beautiful landscape in the image."},
        ]

        input_data = WorkflowInput(
            workflow_name="multimodal", content="Tell me more about it", history=multimodal_history, image_url=None
        )

        assert len(input_data.history) == 2
        assert isinstance(input_data.history[0]["content"], list)
        assert input_data.history[0]["content"][0]["type"] == "text"
        assert input_data.history[0]["content"][1]["type"] == "image_url"

    def test_workflow_input_default_history(self):
        """测试默认历史记录（应该为空列表）"""
        input_data = WorkflowInput(workflow_name="default", content="Test message")

        assert input_data.history == []
        assert isinstance(input_data.history, list)

    @patch("vertex_flow.workflow.app.app.LLMVertex")
    @patch("vertex_flow.workflow.app.app.MCPLLMVertex")
    def test_create_llm_vertex_with_history(self, mock_mcp_vertex, mock_llm_vertex):
        """测试create_llm_vertex函数创建LLMVertex（历史记录现在通过workflow inputs传递）"""
        # 准备测试数据
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]

        input_data = WorkflowInput(
            workflow_name="test", content="Current question", history=history, enable_mcp=False  # 禁用MCP以简化测试
        )

        # 模拟chatmodel和function_tools
        chatmodel = "test-model"
        function_tools = []

        # 调用函数
        vertex, status = create_llm_vertex(input_data, chatmodel, function_tools)

        # 验证LLMVertex被调用
        assert mock_llm_vertex.called

        # 获取传递给LLMVertex的参数
        call_args = mock_llm_vertex.call_args
        params = call_args[1]["params"]  # 获取params参数

        # 验证历史记录现在在params中（历史记录功能已修复）
        assert CONVERSATION_HISTORY in params
        # 验证其他必要的参数仍然存在
        assert "enable_reasoning" in params
        assert "enable_search" in params

    @patch("vertex_flow.workflow.app.app.LLMVertex")
    def test_create_llm_vertex_without_history(self, mock_llm_vertex):
        """测试create_llm_vertex函数处理无历史记录的情况"""
        input_data = WorkflowInput(
            workflow_name="test", content="Question without history", history=[], enable_mcp=False  # 空历史记录
        )

        chatmodel = "test-model"
        function_tools = []

        # 调用函数
        vertex, status = create_llm_vertex(input_data, chatmodel, function_tools)

        # 验证LLMVertex被调用
        assert mock_llm_vertex.called

        # 获取传递给LLMVertex的参数
        call_args = mock_llm_vertex.call_args
        params = call_args[1]["params"]

        # 验证空历史记录不会被传递
        assert CONVERSATION_HISTORY not in params

    def test_workflow_input_serialization(self):
        """测试WorkflowInput的序列化"""
        history = [{"role": "user", "content": "Test"}, {"role": "assistant", "content": "Response"}]

        input_data = WorkflowInput(
            workflow_name="test", content="Hello", history=history, stream=True, enable_mcp=False
        )

        # 测试dict()方法
        data_dict = input_data.dict()

        assert data_dict["workflow_name"] == "test"
        assert data_dict["content"] == "Hello"
        assert data_dict["history"] == history
        assert data_dict["stream"] is True
        assert data_dict["enable_mcp"] is False

    def test_large_history_handling(self):
        """测试大量历史记录的处理"""
        # 创建大量历史记录
        large_history = []
        for i in range(100):
            large_history.extend(
                [{"role": "user", "content": f"Question {i}"}, {"role": "assistant", "content": f"Answer {i}"}]
            )

        input_data = WorkflowInput(
            workflow_name="large_history_test", content="Current question", history=large_history
        )

        assert len(input_data.history) == 200  # 100 * 2
        assert input_data.history[0]["content"] == "Question 0"
        assert input_data.history[-1]["content"] == "Answer 99"

    def test_history_with_all_parameters(self):
        """测试历史记录与所有其他参数的兼容性"""
        history = [{"role": "user", "content": "Test"}]

        input_data = WorkflowInput(
            workflow_name="comprehensive_test",
            env_vars={"ENV_VAR": "value"},
            user_vars={"USER_VAR": "user_value"},
            content="Test content",
            image_url="https://example.com/image.jpg",
            stream=True,
            enable_mcp=True,
            history=history,
            system_prompt="Custom system prompt",
            enable_reasoning=True,
            show_reasoning=False,
            temperature=0.8,
            max_tokens=2000,
            enable_search=False,
            enable_tools=False,
        )

        # 验证所有参数都正确设置
        assert input_data.workflow_name == "comprehensive_test"
        assert input_data.env_vars == {"ENV_VAR": "value"}
        assert input_data.user_vars == {"USER_VAR": "user_value"}
        assert input_data.content == "Test content"
        assert input_data.image_url == "https://example.com/image.jpg"
        assert input_data.stream is True
        assert input_data.enable_mcp is True
        assert input_data.history == history
        assert input_data.system_prompt == "Custom system prompt"
        assert input_data.enable_reasoning is True
        assert input_data.show_reasoning is False
        assert input_data.temperature == 0.8
        assert input_data.max_tokens == 2000
        assert input_data.enable_search is False
        assert input_data.enable_tools is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
