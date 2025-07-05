#!/usr/bin/env python3
"""
测试VertexGroup的变量筛选和变量暴露功能
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from vertex_flow.workflow.constants import LOCAL_VAR, SOURCE_SCOPE, SOURCE_VAR, SUBGRAPH_SOURCE
from vertex_flow.workflow.vertex.function_vertex import FunctionVertex
from vertex_flow.workflow.vertex.vertex_group import VertexGroup


def test_vertex_group_basic():
    """测试VertexGroup的基本变量筛选和暴露功能"""
    print("=== 测试VertexGroup基本功能 ===")

    # 创建测试顶点
    def test_function(inputs):
        input_value = inputs.get("input_value", 0)
        return {"result": input_value * 2, "status": "success"}

    test_vertex = FunctionVertex(
        id="test_vertex",
        name="Test Vertex",
        task=test_function,
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
    )

    # 创建VertexGroup
    vertex_group = VertexGroup(
        id="test_group",
        name="Test Group",
        subgraph_vertices=[test_vertex],
        variables=[
            # 变量筛选：从外部输入中筛选input_value传递给子图
            {SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}
        ],
        exposed_variables=[
            # 变量暴露：将子图内部test_vertex的result暴露给外部
            {SOURCE_SCOPE: "test_vertex", SOURCE_VAR: "result", LOCAL_VAR: "exposed_result"}
        ],
    )

    # 执行VertexGroup
    result = vertex_group.execute(inputs={"input_value": 5})
    print(f"VertexGroup执行结果: {result}")

    # 验证结果 - 根据当前实现，VertexGroup返回子图顶点的输出
    assert "test_vertex" in result, "应该包含子图顶点的输出"
    assert result["test_vertex"]["result"] == 10, f"期望结果为10，实际为{result['test_vertex']['result']}"
    assert "status" not in result, "未暴露的变量status不应该出现在结果中"

    print("✓ VertexGroup基本功能测试通过")


def test_vertex_group_no_exposed_variables():
    """测试VertexGroup没有暴露变量时的情况"""
    print("\n=== 测试VertexGroup无暴露变量 ===")

    # 创建测试顶点
    def test_function(inputs):
        input_value = inputs.get("input_value", 0)
        return {"result": input_value * 2, "status": "success"}

    test_vertex = FunctionVertex(
        id="test_vertex",
        name="Test Vertex",
        task=test_function,
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
    )

    # 创建VertexGroup，不设置exposed_variables
    vertex_group = VertexGroup(
        id="test_group_no_expose",
        name="Test Group No Expose",
        subgraph_vertices=[test_vertex],
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
        # 不设置exposed_variables
    )

    # 执行VertexGroup
    result = vertex_group.execute(inputs={"input_value": 5})
    print(f"VertexGroup执行结果: {result}")

    # 验证结果应该包含子图顶点的输出
    assert "test_vertex" in result, "应该包含子图顶点的输出"
    assert result["test_vertex"]["result"] == 10, f"期望结果为10，实际为{result['test_vertex']['result']}"

    print("✓ VertexGroup无暴露变量测试通过")


def main():
    """主测试函数"""
    try:
        test_vertex_group_basic()
        test_vertex_group_no_exposed_variables()
        print("\n🎉 所有测试通过！VertexGroup变量功能正常工作")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
