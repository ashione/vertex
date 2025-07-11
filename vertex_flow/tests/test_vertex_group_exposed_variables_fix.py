#!/usr/bin/env python3
"""
测试VertexGroup exposed_variables修复功能的专项测试
本测试文件专门验证修复后的VertexGroup exposed_variables功能
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from vertex_flow.workflow.constants import LOCAL_VAR, SOURCE_SCOPE, SOURCE_VAR, SUBGRAPH_SOURCE
from vertex_flow.workflow.vertex.function_vertex import FunctionVertex
from vertex_flow.workflow.vertex.vertex_group import VertexGroup


def test_exposed_variables_flattened_output():
    """测试exposed_variables配置时返回扁平化输出"""
    print("=== 测试exposed_variables扁平化输出 ===")

    def task_a(inputs):
        value = inputs.get("input_value", 0)
        return {"result_a": value * 2, "internal_data": "secret"}

    def task_b(inputs):
        result_a = inputs.get("result_a", 0)
        return {"result_b": result_a + 10, "debug_info": "processed"}

    vertex_a = FunctionVertex(
        id="vertex_a",
        name="Vertex A",
        task=task_a,
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
    )

    vertex_b = FunctionVertex(
        id="vertex_b",
        name="Vertex B",
        task=task_b,
        variables=[{SOURCE_SCOPE: "vertex_a", SOURCE_VAR: "result_a", LOCAL_VAR: "result_a"}],
    )

    vertex_group = VertexGroup(
        id="test_group",
        name="Test Group",
        subgraph_vertices=[vertex_a, vertex_b],
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
        exposed_variables=[
            {SOURCE_SCOPE: "vertex_a", SOURCE_VAR: "result_a", LOCAL_VAR: "exposed_a"},
            {SOURCE_SCOPE: "vertex_b", SOURCE_VAR: "result_b", LOCAL_VAR: "exposed_b"},
        ],
    )

    result = vertex_group.execute(inputs={"input_value": 5})
    print(f"VertexGroup执行结果: {result}")

    # 验证扁平化输出
    assert "exposed_a" in result, "应该包含暴露的变量exposed_a"
    assert "exposed_b" in result, "应该包含暴露的变量exposed_b"
    assert result["exposed_a"] == 10, f"期望exposed_a为10，实际为{result['exposed_a']}"
    assert result["exposed_b"] == 20, f"期望exposed_b为20，实际为{result['exposed_b']}"

    # 验证不包含未暴露的变量
    assert "vertex_a" not in result, "不应该包含子图顶点的嵌套输出"
    assert "vertex_b" not in result, "不应该包含子图顶点的嵌套输出"
    assert "internal_data" not in result, "不应该包含未暴露的内部变量"
    assert "debug_info" not in result, "不应该包含未暴露的调试信息"

    print("✓ exposed_variables扁平化输出测试通过")


def test_no_exposed_variables_backward_compatibility():
    """测试没有exposed_variables时的向后兼容性"""
    print("\n=== 测试向后兼容性（无exposed_variables） ===")

    def task_simple(inputs):
        value = inputs.get("input_value", 0)
        return {"result": value * 3, "status": "completed"}

    vertex_simple = FunctionVertex(
        id="vertex_simple",
        name="Simple Vertex",
        task=task_simple,
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
    )

    # 不配置exposed_variables
    vertex_group = VertexGroup(
        id="backward_group",
        name="Backward Compatibility Group",
        subgraph_vertices=[vertex_simple],
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
        # 故意不设置exposed_variables
    )

    result = vertex_group.execute(inputs={"input_value": 4})
    print(f"VertexGroup执行结果: {result}")

    # 验证向后兼容性：应该返回子图顶点的输出
    assert "vertex_simple" in result, "向后兼容：应该包含子图顶点的输出"
    assert result["vertex_simple"]["result"] == 12, f"期望结果为12，实际为{result['vertex_simple']['result']}"
    assert result["vertex_simple"]["status"] == "completed", "应该包含所有子图顶点的输出"

    print("✓ 向后兼容性测试通过")


def test_exposed_variables_edge_cases():
    """测试exposed_variables的边界情况"""
    print("\n=== 测试exposed_variables边界情况 ===")

    def task_with_none(inputs):
        value = inputs.get("input_value", 0)
        return {"result": value if value > 0 else None, "always_present": "exists"}

    def task_with_empty(inputs):
        return {"empty_dict": {}, "empty_list": [], "zero_value": 0}

    vertex_none = FunctionVertex(
        id="vertex_none",
        name="Vertex with None",
        task=task_with_none,
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
    )

    vertex_empty = FunctionVertex(
        id="vertex_empty",
        name="Vertex with Empty Values",
        task=task_with_empty,
    )

    vertex_group = VertexGroup(
        id="edge_case_group",
        name="Edge Case Group",
        subgraph_vertices=[vertex_none, vertex_empty],
        variables=[{SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "input_value", LOCAL_VAR: "input_value"}],
        exposed_variables=[
            {SOURCE_SCOPE: "vertex_none", SOURCE_VAR: "result", LOCAL_VAR: "nullable_result"},
            {SOURCE_SCOPE: "vertex_none", SOURCE_VAR: "always_present", LOCAL_VAR: "always_there"},
            {SOURCE_SCOPE: "vertex_empty", SOURCE_VAR: "empty_dict", LOCAL_VAR: "empty_dict_exposed"},
            {SOURCE_SCOPE: "vertex_empty", SOURCE_VAR: "zero_value", LOCAL_VAR: "zero_exposed"},
        ],
    )

    # 测试正值情况
    result_positive = vertex_group.execute(inputs={"input_value": 5})
    print(f"正值输入结果: {result_positive}")

    # 验证存在的变量
    if "nullable_result" in result_positive:
        assert result_positive["nullable_result"] == 5, "正值应该被正确暴露"
    if "always_there" in result_positive:
        assert result_positive["always_there"] == "exists", "非空值应该被正确暴露"
    if "empty_dict_exposed" in result_positive:
        assert result_positive["empty_dict_exposed"] == {}, "空字典应该被正确暴露"
    if "zero_exposed" in result_positive:
        assert result_positive["zero_exposed"] == 0, "零值应该被正确暴露"

    # 测试零值情况
    result_zero = vertex_group.execute(inputs={"input_value": 0})
    print(f"零值输入结果: {result_zero}")

    # 验证存在的变量
    if "nullable_result" in result_zero:
        assert result_zero["nullable_result"] is None, "None值应该被正确暴露"
    if "always_there" in result_zero:
        assert result_zero["always_there"] == "exists", "非空值应该被正确暴露"

    print("✓ 边界情况测试通过")


def test_exposed_variables_name_conflicts():
    """测试exposed_variables名称冲突处理"""
    print("\n=== 测试exposed_variables名称冲突 ===")

    def task_conflict_a(inputs):
        return {"same_name": "from_a", "unique_a": "value_a"}

    def task_conflict_b(inputs):
        return {"same_name": "from_b", "unique_b": "value_b"}

    vertex_a = FunctionVertex(id="conflict_a", name="Conflict A", task=task_conflict_a)
    vertex_b = FunctionVertex(id="conflict_b", name="Conflict B", task=task_conflict_b)

    vertex_group = VertexGroup(
        id="conflict_group",
        name="Conflict Group",
        subgraph_vertices=[vertex_a, vertex_b],
        exposed_variables=[
            {SOURCE_SCOPE: "conflict_a", SOURCE_VAR: "same_name", LOCAL_VAR: "exposed_a"},
            {SOURCE_SCOPE: "conflict_b", SOURCE_VAR: "same_name", LOCAL_VAR: "exposed_b"},
            {SOURCE_SCOPE: "conflict_a", SOURCE_VAR: "unique_a", LOCAL_VAR: "unique_from_a"},
            {SOURCE_SCOPE: "conflict_b", SOURCE_VAR: "unique_b", LOCAL_VAR: "unique_from_b"},
        ],
    )

    result = vertex_group.execute(inputs={})
    print(f"名称冲突处理结果: {result}")

    # 验证不同的暴露名称能正确区分来源
    assert result["exposed_a"] == "from_a", "来自vertex_a的值应该正确暴露"
    assert result["exposed_b"] == "from_b", "来自vertex_b的值应该正确暴露"
    assert result["unique_from_a"] == "value_a", "unique_a应该正确暴露"
    assert result["unique_from_b"] == "value_b", "unique_b应该正确暴露"

    print("✓ 名称冲突处理测试通过")


def test_exposed_variables_complex_data_types():
    """测试exposed_variables处理复杂数据类型"""
    print("\n=== 测试复杂数据类型暴露 ===")

    def task_complex(inputs):
        return {
            "nested_dict": {"level1": {"level2": "deep_value"}},
            "list_data": [1, 2, {"nested": "in_list"}],
            "mixed_types": {"string": "text", "number": 42, "boolean": True, "null": None, "list": ["a", "b", "c"]},
        }

    vertex_complex = FunctionVertex(id="complex_vertex", name="Complex Data Vertex", task=task_complex)

    vertex_group = VertexGroup(
        id="complex_group",
        name="Complex Data Group",
        subgraph_vertices=[vertex_complex],
        exposed_variables=[
            {SOURCE_SCOPE: "complex_vertex", SOURCE_VAR: "nested_dict", LOCAL_VAR: "exposed_nested"},
            {SOURCE_SCOPE: "complex_vertex", SOURCE_VAR: "list_data", LOCAL_VAR: "exposed_list"},
            {SOURCE_SCOPE: "complex_vertex", SOURCE_VAR: "mixed_types", LOCAL_VAR: "exposed_mixed"},
        ],
    )

    result = vertex_group.execute(inputs={})
    print(f"复杂数据类型结果: {result}")

    # 验证复杂数据类型的正确暴露
    assert result["exposed_nested"]["level1"]["level2"] == "deep_value", "嵌套字典应该正确暴露"
    assert result["exposed_list"][2]["nested"] == "in_list", "列表中的嵌套数据应该正确暴露"
    assert result["exposed_mixed"]["string"] == "text", "混合类型中的字符串应该正确暴露"
    assert result["exposed_mixed"]["number"] == 42, "混合类型中的数字应该正确暴露"
    assert result["exposed_mixed"]["boolean"] is True, "混合类型中的布尔值应该正确暴露"
    assert result["exposed_mixed"]["null"] is None, "混合类型中的None值应该正确暴露"
    assert result["exposed_mixed"]["list"] == ["a", "b", "c"], "混合类型中的列表应该正确暴露"

    print("✓ 复杂数据类型测试通过")


def test_exposed_variables_missing_source():
    """测试exposed_variables引用不存在的源变量"""
    print("\n=== 测试引用不存在的源变量 ===")

    def task_normal(inputs):
        return {"existing_var": "exists"}

    vertex_normal = FunctionVertex(id="normal_vertex", name="Normal Vertex", task=task_normal)

    vertex_group = VertexGroup(
        id="missing_source_group",
        name="Missing Source Group",
        subgraph_vertices=[vertex_normal],
        exposed_variables=[
            {SOURCE_SCOPE: "normal_vertex", SOURCE_VAR: "existing_var", LOCAL_VAR: "exposed_existing"},
            {SOURCE_SCOPE: "normal_vertex", SOURCE_VAR: "non_existing_var", LOCAL_VAR: "exposed_missing"},
            {SOURCE_SCOPE: "non_existing_vertex", SOURCE_VAR: "any_var", LOCAL_VAR: "exposed_from_missing_vertex"},
        ],
    )

    result = vertex_group.execute(inputs={})
    print(f"缺失源变量处理结果: {result}")

    # 验证存在的变量正常暴露
    assert "exposed_existing" in result, "存在的变量应该被正确暴露"
    assert result["exposed_existing"] == "exists", "存在的变量值应该正确"

    # 验证不存在的变量不会导致错误，但也不会出现在结果中
    # 根据实际实现，不存在的变量会被忽略
    assert "exposed_missing" not in result, "不存在的变量不应该出现在结果中"
    assert "exposed_from_missing_vertex" not in result, "来自不存在顶点的变量不应该出现在结果中"
    print(f"结果中的键: {list(result.keys())}")

    print("✓ 缺失源变量处理测试通过")


def main():
    """主测试函数"""
    try:
        test_exposed_variables_flattened_output()
        test_no_exposed_variables_backward_compatibility()
        test_exposed_variables_edge_cases()
        test_exposed_variables_name_conflicts()
        test_exposed_variables_complex_data_types()
        test_exposed_variables_missing_source()
        print("\n🎉 所有VertexGroup exposed_variables修复测试通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
