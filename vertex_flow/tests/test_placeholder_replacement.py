#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
占位符替换单元测试

测试workflow中占位符{{source}}是否被正确替换
"""

from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from vertex_flow.workflow.constants import LOCAL_VAR, SOURCE_SCOPE, SOURCE_VAR, SYSTEM, USER
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.edge import Edge
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.vertex import SinkVertex, SourceVertex, Vertex
from vertex_flow.workflow.workflow import Workflow


@pytest.fixture
def workflow():
    """创建workflow实例"""
    return Workflow()


@pytest.fixture
def context():
    """创建context实例"""
    return WorkflowContext()


def test_two_llm_placeholder_replacement(workflow, context):
    """测试两个LLM顶点之间的占位符替换"""

    # 1. 创建源顶点
    source_vertex = SourceVertex(id="source", name="数据源", task=lambda inputs, context: "初始输入数据")

    # 2. 创建第一个mock LLM顶点，生成数据
    first_llm_vertex = LLMVertex(
        id="llm1",
        name="数据生成LLM",
        params={"model": Mock(), SYSTEM: "你是一个数据生成器", USER: ["生成一段测试数据"]},
        # 添加必需的model参数
    )

    # 3. 创建第二个mock LLM顶点，使用占位符引用第一个LLM的结果
    second_llm_vertex = LLMVertex(
        id="llm2",
        name="数据分析LLM",
        params={
            "model": Mock(),  # 添加必需的model参数
            SYSTEM: "你是一个数据分析师",
            USER: ["请分析以下内容：{{llm1}}, {{source}}"],
        },
        variables=[
            {"source_scope": "source", "source_var": None, "local_var": "source"}
        ]
    )

    # 4. 创建sink顶点
    sink_vertex = SinkVertex(
        id="sink",
        name="输出接收器",
        task=lambda inputs, context: f"接收到结果: {inputs.get('llm2', '')}",
    )

    # Mock 第一个LLM的model.chat方法
    with patch.object(first_llm_vertex.model, "chat") as mock_chat1:
        mock_chat1.return_value = Mock(message=Mock(content="这是来自第一个LLM的测试数据"), finish_reason="stop")

        # Mock 第二个LLM的model.chat方法
        with patch.object(second_llm_vertex.model, "chat") as mock_chat2:
            mock_chat2.return_value = Mock(
                message=Mock(content="分析完成：这是来自第一个LLM的测试数据"), finish_reason="stop"
            )

            # 5. 添加顶点到workflow
            workflow.add_vertex(source_vertex)
            workflow.add_vertex(first_llm_vertex)
            workflow.add_vertex(second_llm_vertex)
            workflow.add_vertex(sink_vertex)

            # 6. 添加边连接
            workflow.add_edge(Edge(source_vertex, first_llm_vertex))
            workflow.add_edge(Edge(first_llm_vertex, second_llm_vertex))
            workflow.add_edge(Edge(source_vertex, second_llm_vertex))  # 添加source到llm2的直接依赖
            workflow.add_edge(Edge(second_llm_vertex, sink_vertex))

            # 8. 执行workflow
            test_input = {"content": "测试输入"}
            workflow.execute_workflow(test_input, stream=False)

            # 9. 验证结果
            # 检查第一个LLM顶点是否正确执行
            assert first_llm_vertex.is_executed
            assert first_llm_vertex.output is not None

            assert first_llm_vertex.output == "这是来自第一个LLM的测试数据"

            # 检查第二个LLM顶点是否正确执行
            assert second_llm_vertex.is_executed

            # 验证占位符是否被正确替换
            # 通过检查第二个LLM的mock_chat2的调用参数来验证
            mock_chat2.assert_called_once()
            call_args = mock_chat2.call_args
            call_args_list = call_args[0]
            messages = call_args_list[0]

            # 检查消息是否包含正确的内容
            assert len(messages) == 2
            assert messages[0]["content"] == "你是一个数据分析师"
            assert messages[1]["content"] == "请分析以下内容：这是来自第一个LLM的测试数据, 初始输入数据"

            # 验证第一个LLM也被正确调用
            mock_chat1.assert_called_once()
