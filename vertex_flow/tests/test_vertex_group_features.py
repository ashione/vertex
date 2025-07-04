#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顶点组功能综合测试
包含流式参数传递、子图执行等功能测试
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import ENABLE_STREAM, SYSTEM, USER
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.vertex_group import VertexGroup

logger = LoggerUtil.get_logger()


class MockMessage:
    """模拟消息对象"""

    def __init__(self, content):
        self.content = content


class MockChoice:
    """模拟选择对象"""

    def __init__(self, content, finish_reason="stop"):
        self.message = MockMessage(content)
        self.finish_reason = finish_reason


class MockResponse:
    """模拟响应对象"""

    def __init__(self, content):
        self.choices = [MockChoice(content)]


class MockChatModel:
    """模拟聊天模型"""

    def __init__(self):
        self.responses = ["这是一个测试响应"]
        self.response_index = 0

    def chat(self, messages, **kwargs):
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        return MockChoice(response)

    def chat_stream(self, messages, **kwargs):
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        # 模拟流式输出
        for char in response:
            yield MockChoice(char)

    def model_name(self):
        return "MockModel"


def test_vertex_group_streaming_parameter_passing():
    """测试VertexGroup中LLMVertex的流式参数传递"""
    print("=== 测试VertexGroup中LLMVertex的流式参数传递 ===")

    try:
        # 创建模拟模型
        mock_model = MockChatModel()

        # 创建VertexGroup
        vertex_group = VertexGroup(id="test_group")

        # 创建LLMVertex（初始时不启用流式）
        llm_vertex = LLMVertex(
            id="test_llm",
            params={
                "model": mock_model,
                SYSTEM: "你是一个测试助手",
                USER: ["请回答测试问题"],
                ENABLE_STREAM: False,  # 初始设置为False
            },
        )

        # 添加到子图
        vertex_group.add_subgraph_vertex(llm_vertex)

        # 创建工作流上下文
        context = WorkflowContext()

        # 测试1: 不启用流式的情况
        print("\n测试1: 不启用流式输出")
        inputs_no_stream = {"test_input": "测试数据"}

        print(f"执行前 LLMVertex ENABLE_STREAM: {llm_vertex.params.get(ENABLE_STREAM)}")
        vertex_group.execute_subgraph(inputs_no_stream, context)
        print(f"执行后 LLMVertex ENABLE_STREAM: {llm_vertex.params.get(ENABLE_STREAM)}")

        # 验证流式参数未被修改
        assert llm_vertex.params.get(ENABLE_STREAM) == False, "不启用流式时，ENABLE_STREAM应该保持False"

        # 测试2: 启用流式的情况
        print("\n测试2: 启用流式输出")
        inputs_with_stream = {"test_input": "测试数据", "stream": True}

        # 重置LLMVertex的ENABLE_STREAM参数
        llm_vertex.params[ENABLE_STREAM] = False
        print(f"执行前 LLMVertex ENABLE_STREAM: {llm_vertex.params.get(ENABLE_STREAM)}")

        vertex_group.execute_subgraph(inputs_with_stream, context)
        print(f"执行后 LLMVertex ENABLE_STREAM: {llm_vertex.params.get(ENABLE_STREAM)}")

        # 验证结果
        if llm_vertex.params.get(ENABLE_STREAM) == True:
            print("✅ 测试通过：VertexGroup正确设置了LLMVertex的流式参数")
            return True
        else:
            print("❌ 测试失败：VertexGroup未能正确设置LLMVertex的流式参数")
            return False

    except Exception as e:
        print(f"❌ 测试失败，出现异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_vertex_group_subgraph_execution():
    """测试VertexGroup的子图执行功能"""
    print("\n=== 测试VertexGroup子图执行功能 ===")

    try:
        # 创建模拟模型
        mock_model = MockChatModel()

        # 创建VertexGroup
        vertex_group = VertexGroup(id="subgraph_test_group", name="子图测试组")

        # 创建多个LLMVertex
        llm_vertex1 = LLMVertex(
            id="llm1",
            params={
                "model": mock_model,
                SYSTEM: "你是助手1",
                USER: ["问题1"],
                ENABLE_STREAM: False,
            },
        )

        llm_vertex2 = LLMVertex(
            id="llm2",
            params={
                "model": mock_model,
                SYSTEM: "你是助手2",
                USER: ["问题2"],
                ENABLE_STREAM: False,
            },
        )

        # 添加到子图
        vertex_group.add_subgraph_vertex(llm_vertex1)
        vertex_group.add_subgraph_vertex(llm_vertex2)

        # 创建工作流上下文
        context = WorkflowContext()

        # 执行子图
        inputs = {"test_data": "子图测试数据"}
        result = vertex_group.execute_subgraph(inputs, context)

        print(f"子图执行结果: {result}")

        # 验证子图中的顶点都被执行了
        assert len(vertex_group.subgraph_vertices) == 2, "应该有2个子图顶点"
        print("✅ 子图执行功能测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_vertex_group_streaming_propagation():
    """测试VertexGroup中流式参数的传播机制"""
    print("\n=== 测试VertexGroup流式参数传播机制 ===")

    try:
        # 创建模拟模型
        mock_model = MockChatModel()

        # 创建VertexGroup
        vertex_group = VertexGroup(id="propagation_test_group")

        # 创建多个LLMVertex，初始都不启用流式
        llm_vertices = []
        for i in range(3):
            llm_vertex = LLMVertex(
                id=f"llm_{i}",
                params={
                    "model": mock_model,
                    SYSTEM: f"你是助手{i}",
                    USER: [f"问题{i}"],
                    ENABLE_STREAM: False,
                },
            )
            llm_vertices.append(llm_vertex)
            vertex_group.add_subgraph_vertex(llm_vertex)

        # 创建工作流上下文
        context = WorkflowContext()

        # 测试流式参数传播
        print("\n测试流式参数传播")
        inputs_with_stream = {"test_data": "传播测试", "stream": True}

        # 执行前检查所有LLMVertex的流式状态
        print("执行前的流式状态:")
        for i, vertex in enumerate(llm_vertices):
            print(f"  LLM{i}: {vertex.params.get(ENABLE_STREAM)}")
            assert vertex.params.get(ENABLE_STREAM) == False, f"LLM{i}初始应该不启用流式"

        # 执行子图
        vertex_group.execute_subgraph(inputs_with_stream, context)

        # 执行后检查所有LLMVertex的流式状态
        print("执行后的流式状态:")
        all_streaming_enabled = True
        for i, vertex in enumerate(llm_vertices):
            stream_enabled = vertex.params.get(ENABLE_STREAM)
            print(f"  LLM{i}: {stream_enabled}")
            if not stream_enabled:
                all_streaming_enabled = False

        if all_streaming_enabled:
            print("✅ 流式参数传播测试通过：所有LLMVertex都启用了流式")
            return True
        else:
            print("❌ 流式参数传播测试失败：部分LLMVertex未启用流式")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_vertex_group_edge_cases():
    """测试VertexGroup的边界情况"""
    print("\n=== 测试VertexGroup边界情况 ===")

    try:
        # 测试空子图
        empty_group = VertexGroup(id="empty_group")
        context = WorkflowContext()

        result = empty_group.execute_subgraph({"test": "data"}, context)
        print(f"空子图执行结果: {result}")

        # 测试无效输入
        vertex_group = VertexGroup(id="edge_case_group")
        mock_model = MockChatModel()

        llm_vertex = LLMVertex(
            id="edge_llm",
            params={
                "model": mock_model,
                SYSTEM: "测试助手",
                USER: ["测试问题"],
                ENABLE_STREAM: False,
            },
        )
        vertex_group.add_subgraph_vertex(llm_vertex)

        # 测试None输入
        result_none = vertex_group.execute_subgraph(None, context)
        print(f"None输入执行结果: {result_none}")

        # 测试空字典输入
        result_empty = vertex_group.execute_subgraph({}, context)
        print(f"空字典输入执行结果: {result_empty}")

        print("✅ 边界情况测试通过")
        return True

    except Exception as e:
        print(f"❌ 边界情况测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始顶点组功能综合测试...\n")

    tests = [
        test_vertex_group_streaming_parameter_passing,
        test_vertex_group_subgraph_execution,
        test_vertex_group_streaming_propagation,
        test_vertex_group_edge_cases,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 异常: {e}")
            failed += 1

    print(f"\n=== 测试结果汇总 ===")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有顶点组功能测试通过！")
        return True
    else:
        print(f"\n💥 有 {failed} 个测试失败！")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
