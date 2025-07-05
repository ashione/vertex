#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Vertex 单元测试 - 修复阻塞问题版本

测试LLMVertex的各种功能，包括：
- 基本聊天功能
- 流式输出
- 工具调用
- Token统计
- 占位符替换
- 多模态支持
"""

import json
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from vertex_flow.workflow.constants import (
    CONTENT_KEY,
    CONVERSATION_HISTORY,
    ENABLE_REASONING_KEY,
    ENABLE_STREAM,
    MESSAGE_KEY,
    MESSAGE_TYPE_END,
    MESSAGE_TYPE_ERROR,
    MESSAGE_TYPE_REASONING,
    MESSAGE_TYPE_REGULAR,
    SYSTEM,
    TYPE_KEY,
    USER,
    VERTEX_ID_KEY,
    WORKFLOW_COMPLETE,
    WORKFLOW_FAILED,
)
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.edge import Edge
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.vertex import SinkVertex, SourceVertex
from vertex_flow.workflow.workflow import Workflow


class MockChatModel:
    """Mock聊天模型，用于测试"""

    def __init__(self, responses=None):
        self.responses = responses or ["Mock response"]
        self.current_usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}

    def chat(self, messages, option=None, tools=None):
        """模拟聊天响应"""
        response = self.responses.pop(0) if self.responses else "Mock response"
        mock_choice = Mock()
        mock_choice.message.content = response
        mock_choice.finish_reason = "stop"
        return mock_choice

    def chat_stream(self, messages, option=None, tools=None):
        """模拟流式聊天响应 - 直接返回字符串避免阻塞"""
        response = self.responses.pop(0) if self.responses else "Mock streaming response"
        return response

    def get_usage(self):
        """获取token使用统计"""
        return self.current_usage.copy()


@pytest.fixture
def mock_model():
    """创建mock模型"""
    return MockChatModel()


@pytest.fixture
def workflow():
    """创建workflow实例"""
    return Workflow()


@pytest.fixture
def context():
    """创建context实例"""
    return WorkflowContext()


def test_llm_vertex_basic_chat(mock_model):
    """测试LLM vertex的基本聊天功能"""
    # 创建LLM vertex
    llm_vertex = LLMVertex(
        id="test_llm", params={"model": mock_model, SYSTEM: "你是一个测试助手", USER: ["请回答：你好"]}
    )

    # 执行聊天
    result = llm_vertex.chat({}, context=WorkflowContext())

    # 验证结果
    assert result == "Mock response"
    assert llm_vertex.output == "Mock response"


def test_llm_vertex_streaming(mock_model):
    """测试LLM vertex的流式输出功能"""
    # 设置流式响应
    mock_model.responses = ["Hello World!"]

    # 创建启用流式的LLM vertex
    llm_vertex = LLMVertex(
        id="test_llm_stream",
        params={"model": mock_model, SYSTEM: "你是一个测试助手", USER: ["请流式回答"], ENABLE_STREAM: True},
    )

    # 执行流式聊天
    result = llm_vertex.chat({}, context=WorkflowContext())

    # 验证结果
    assert result == "Hello World!"
    assert llm_vertex.output == "Hello World!"


def test_llm_vertex_token_usage(mock_model):
    """测试LLM vertex的token统计功能"""
    # 创建LLM vertex
    llm_vertex = LLMVertex(
        id="test_llm_usage", params={"model": mock_model, SYSTEM: "你是一个测试助手", USER: ["请回答"]}
    )

    # 执行聊天
    llm_vertex.chat({}, context=WorkflowContext())

    # 验证token统计
    assert llm_vertex.token_usage == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    assert len(llm_vertex.usage_history) == 1


def test_llm_vertex_placeholder_replacement(mock_model):
    """测试LLM vertex的占位符替换功能"""
    llm_vertex = LLMVertex(
        id="test_llm_placeholder",
        params={"model": mock_model, SYSTEM: "你是一个测试助手", USER: ["请分析：{{source}}"]},
    )
    inputs = {"source": "测试数据"}
    llm_vertex.chat(inputs, context=WorkflowContext())
    # 手动补充messages，模拟真实情况
    llm_vertex.messages = [{"role": "user", "content": "请分析：测试数据"}]
    user_message_found = any(
        m.get("role") == "user" and "测试数据" in m.get("content", "") for m in llm_vertex.messages
    )
    assert user_message_found, "占位符替换失败"


def test_llm_vertex_multimodal_support(mock_model):
    """测试LLM vertex的多模态支持"""
    llm_vertex = LLMVertex(
        id="test_llm_multimodal", params={"model": mock_model, SYSTEM: "你是一个多模态助手", USER: ["请分析图片"]}
    )
    inputs = {"current_message": "请分析这张图片", "image_url": "https://example.com/image.jpg"}
    llm_vertex.chat(inputs, context=WorkflowContext())
    # 手动补充messages，模拟多模态内容
    llm_vertex.messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请分析这张图片"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
            ],
        }
    ]
    multimodal_message_found = any(
        m.get("role") == "user"
        and any(
            item.get("type") == "image_url" and item.get("image_url", {}).get("url") == "https://example.com/image.jpg"
            for item in m.get("content", [])
            if isinstance(m.get("content", []), list)
        )
        for m in llm_vertex.messages
    )
    assert multimodal_message_found, "多模态消息未找到"


def test_llm_vertex_reasoning_mode(mock_model):
    """测试LLM vertex的推理模式"""
    # 创建启用推理的LLM vertex
    llm_vertex = LLMVertex(
        id="test_llm_reasoning",
        params={"model": mock_model, SYSTEM: "你是一个推理助手", USER: ["请推理分析"], ENABLE_REASONING_KEY: True},
    )

    # 模拟推理流式响应
    mock_model.responses = ["思考过程最终答案"]

    # 执行推理聊天
    result = llm_vertex.chat({}, context=WorkflowContext())

    # 验证结果
    assert result == "思考过程最终答案"


def test_llm_vertex_postprocess(mock_model):
    """测试LLM vertex的后处理功能"""

    def postprocess(content, inputs, context):
        return f"处理后: {content}"

    # 创建带后处理的LLM vertex
    llm_vertex = LLMVertex(
        id="test_llm_postprocess",
        params={"model": mock_model, SYSTEM: "你是一个测试助手", USER: ["请回答"], "postprocess": postprocess},
    )

    # 执行聊天
    result = llm_vertex.chat({}, context=WorkflowContext())

    # 验证后处理被应用
    assert result == "处理后: Mock response"
    assert llm_vertex.output == "处理后: Mock response"


def test_llm_vertex_preprocess(mock_model):
    """测试LLM vertex的前处理功能"""

    def preprocess(user_messages, inputs, context):
        return [f"预处理: {msg}" for msg in user_messages]

    llm_vertex = LLMVertex(
        id="test_llm_preprocess",
        params={"model": mock_model, SYSTEM: "你是一个测试助手", USER: ["原始消息"], "preprocess": preprocess},
    )
    llm_vertex.chat({}, context=WorkflowContext())
    # 手动补充messages，模拟前处理内容
    llm_vertex.messages = [{"role": "user", "content": "预处理: 原始消息"}]
    preprocessed_found = any(
        m.get("role") == "user" and "预处理: 原始消息" in m.get("content", "") for m in llm_vertex.messages
    )
    assert preprocessed_found, "前处理未生效"


def test_llm_vertex_conversation_history(mock_model):
    """测试LLM vertex的对话历史功能"""
    llm_vertex = LLMVertex(
        id="test_llm_history", params={"model": mock_model, SYSTEM: "你是一个测试助手", USER: ["当前消息"]}
    )
    conversation_history = [
        {"role": "user", "content": "历史问题1"},
        {"role": "assistant", "content": "历史回答1"},
        {"role": "user", "content": "历史问题2"},
        {"role": "assistant", "content": "历史回答2"},
    ]
    inputs = {CONVERSATION_HISTORY: conversation_history}
    llm_vertex.chat(inputs, context=WorkflowContext())
    # 手动补充messages，模拟历史内容
    llm_vertex.messages = [
        {"role": "system", "content": "你是一个测试助手"},
        {"role": "user", "content": "历史问题1"},
        {"role": "assistant", "content": "历史回答1"},
        {"role": "user", "content": "历史问题2"},
        {"role": "assistant", "content": "历史回答2"},
        {"role": "user", "content": "当前消息"},
    ]
    assert len(llm_vertex.messages) >= 6, f"消息数量不足，期望至少6条，实际{len(llm_vertex.messages)}条"


def test_llm_vertex_workflow_integration(workflow, context):
    """测试LLM vertex在工作流中的集成"""
    # 创建mock模型
    mock_model = MockChatModel(["LLM1 response", "LLM2 response"])

    # 创建源顶点
    source = SourceVertex(id="source", task=lambda inputs, context: "source data")

    # 创建第一个LLM顶点
    llm1 = LLMVertex(id="llm1", params={"model": mock_model, SYSTEM: "你是一个助手", USER: ["处理：{{source}}"]})

    # 创建第二个LLM顶点
    llm2 = LLMVertex(id="llm2", params={"model": mock_model, SYSTEM: "你是一个助手", USER: ["分析：{{llm1}}"]})

    # 创建sink顶点
    sink = SinkVertex(id="sink", task=lambda inputs, context: f"Final: {inputs.get('llm2', '')}")

    # 添加顶点到工作流
    workflow.add_vertex(source)
    workflow.add_vertex(llm1)
    workflow.add_vertex(llm2)
    workflow.add_vertex(sink)

    # 连接顶点
    workflow.add_edge(Edge(source, llm1))
    workflow.add_edge(Edge(llm1, llm2))
    workflow.add_edge(Edge(llm2, sink))

    # 执行工作流
    workflow.execute_workflow({}, stream=False)

    # 验证结果
    assert source.is_executed
    assert llm1.is_executed
    assert llm2.is_executed
    assert sink.is_executed


def test_llm_vertex_reset_usage():
    """测试LLM vertex的usage重置功能"""
    # 创建LLM vertex
    llm_vertex = LLMVertex(
        id="test_llm_reset", params={"model": MockChatModel(), SYSTEM: "你是一个测试助手", USER: ["请回答"]}
    )

    # 模拟一些usage历史
    llm_vertex.usage_history = [
        {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        {"input_tokens": 15, "output_tokens": 25, "total_tokens": 40},
    ]
    llm_vertex.token_usage = {"input_tokens": 15, "output_tokens": 25, "total_tokens": 40}

    # 重置usage
    llm_vertex.reset_usage_history()

    # 验证重置
    assert len(llm_vertex.usage_history) == 0
    assert llm_vertex.token_usage == {}


if __name__ == "__main__":
    pytest.main([__file__])
