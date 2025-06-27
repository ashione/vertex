#!/usr/bin/env python3
"""
VertexGroup 使用示例

本文件展示了如何使用 VertexGroup 创建和执行包含多个顶点的子图。
VertexGroup 允许将多个相关的顶点组织成一个逻辑单元，并控制哪些变量暴露给外部。
"""

import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.edge import Always, Edge
from vertex_flow.workflow.vertex import FunctionVertex, VertexGroup


def example_1_simple_calculation_subgraph():
    """
    示例1: 简单计算子图
    创建一个包含加法和乘法操作的子图
    """
    print("\n=== 示例1: 简单计算子图 ===")

    # 定义任务函数
    def add_task(inputs):
        a = inputs.get("a", 0)
        b = inputs.get("b", 0)
        result = a + b
        print(f"  加法: {a} + {b} = {result}")
        return {"sum": result}

    def multiply_task(inputs):
        value = inputs.get("value", 1)
        factor = inputs.get("factor", 2)
        result = value * factor
        print(f"  乘法: {value} * {factor} = {result}")
        return {"product": result}

    # 创建顶点
    add_vertex = FunctionVertex(id="add_vertex", name="加法顶点", task=add_task)

    multiply_vertex = FunctionVertex(
        id="multiply_vertex",
        name="乘法顶点",
        task=multiply_task,
        variables=[{"source_scope": "add_vertex", "source_var": "sum", "local_var": "value"}],
    )

    # 创建边
    edge = Edge(add_vertex, multiply_vertex, Always())

    # 定义暴露输出
    exposed_outputs = [
        {"vertex_id": "add_vertex", "variable": "sum", "exposed_as": "addition_result"},
        {"vertex_id": "multiply_vertex", "variable": "product", "exposed_as": "final_result"},
    ]

    # 创建VertexGroup
    calc_group = VertexGroup(
        id="calculation_group",
        name="计算组",
        subgraph_vertices=[add_vertex, multiply_vertex],
        subgraph_edges=[edge],
        exposed_outputs=exposed_outputs,
    )

    # 执行子图
    inputs = {"a": 10, "b": 5, "factor": 3}
    context = WorkflowContext()

    print(f"输入: {inputs}")
    result = calc_group.execute_subgraph(inputs, context)

    print(f"暴露的输出: {result['subgraph_outputs']}")
    print(f"执行摘要: {result['execution_summary']}")

    return calc_group


def example_2_data_processing_pipeline():
    """
    示例2: 数据处理管道
    创建一个数据处理管道，包含数据清洗、转换和聚合步骤
    """
    print("\n=== 示例2: 数据处理管道 ===")

    # 数据清洗任务
    def clean_data_task(inputs):
        raw_data = inputs.get("raw_data", [])
        # 移除空值和负数
        cleaned = [x for x in raw_data if x is not None and x >= 0]
        print(f"  数据清洗: {len(raw_data)} -> {len(cleaned)} 条记录")
        return {"cleaned_data": cleaned}

    # 数据转换任务
    def transform_data_task(inputs):
        data = inputs.get("data", [])
        multiplier = inputs.get("multiplier", 1)
        # 将每个值乘以倍数
        transformed = [x * multiplier for x in data]
        print(f"  数据转换: 乘以 {multiplier}")
        return {"transformed_data": transformed}

    # 数据聚合任务
    def aggregate_data_task(inputs):
        data = inputs.get("data", [])
        if not data:
            return {"sum": 0, "avg": 0, "count": 0}

        total = sum(data)
        count = len(data)
        average = total / count
        print(f"  数据聚合: 总和={total}, 平均值={average:.2f}, 数量={count}")
        return {"sum": total, "avg": average, "count": count}

    # 创建顶点
    clean_vertex = FunctionVertex(id="clean_vertex", name="数据清洗", task=clean_data_task)

    transform_vertex = FunctionVertex(
        id="transform_vertex",
        name="数据转换",
        task=transform_data_task,
        variables=[{"source_scope": "clean_vertex", "source_var": "cleaned_data", "local_var": "data"}],
    )

    aggregate_vertex = FunctionVertex(
        id="aggregate_vertex",
        name="数据聚合",
        task=aggregate_data_task,
        variables=[{"source_scope": "transform_vertex", "source_var": "transformed_data", "local_var": "data"}],
    )

    # 创建边
    edge1 = Edge(clean_vertex, transform_vertex, Always())
    edge2 = Edge(transform_vertex, aggregate_vertex, Always())

    # 定义暴露输出
    exposed_outputs = [
        {"vertex_id": "clean_vertex", "variable": "cleaned_data", "exposed_as": "clean_data"},
        {"vertex_id": "aggregate_vertex", "variable": "sum", "exposed_as": "total_sum"},
        {"vertex_id": "aggregate_vertex", "variable": "avg", "exposed_as": "average"},
        {"vertex_id": "aggregate_vertex", "variable": "count", "exposed_as": "record_count"},
    ]

    # 创建VertexGroup
    pipeline_group = VertexGroup(
        id="data_pipeline_group",
        name="数据处理管道",
        subgraph_vertices=[clean_vertex, transform_vertex, aggregate_vertex],
        subgraph_edges=[edge1, edge2],
        exposed_outputs=exposed_outputs,
    )

    # 执行管道
    inputs = {"raw_data": [1, 2, -1, 3, None, 4, 5, -2, 6], "multiplier": 2}
    context = WorkflowContext()

    print(f"原始数据: {inputs['raw_data']}")
    print(f"转换倍数: {inputs['multiplier']}")

    result = pipeline_group.execute_subgraph(inputs, context)

    print(f"\n处理结果:")
    for key, value in result["subgraph_outputs"].items():
        print(f"  {key}: {value}")

    return pipeline_group


def example_3_nested_vertex_groups():
    """
    示例3: 嵌套VertexGroup
    展示如何在工作流中使用VertexGroup作为普通顶点
    """
    print("\n=== 示例3: 嵌套VertexGroup ===")

    # 创建一个简单的计算子图
    def square_task(inputs):
        value = inputs.get("value", 0)
        result = value**2
        print(f"  平方: {value}^2 = {result}")
        return {"squared": result}

    def sqrt_task(inputs):
        value = inputs.get("value", 0)
        result = value**0.5
        print(f"  开方: √{value} = {result:.2f}")
        return {"sqrt": result}

    # 创建子图顶点
    square_vertex = FunctionVertex(id="square_vertex", name="平方", task=square_task)

    sqrt_vertex = FunctionVertex(
        id="sqrt_vertex",
        name="开方",
        task=sqrt_task,
        variables=[{"source_scope": "square_vertex", "source_var": "squared", "local_var": "value"}],
    )

    # 创建子图
    math_group = VertexGroup(
        id="math_group",
        name="数学运算组",
        subgraph_vertices=[square_vertex, sqrt_vertex],
        subgraph_edges=[Edge(square_vertex, sqrt_vertex, Always())],
        exposed_outputs=[
            {"vertex_id": "square_vertex", "variable": "squared", "exposed_as": "square_result"},
            {"vertex_id": "sqrt_vertex", "variable": "sqrt", "exposed_as": "sqrt_result"},
        ],
    )

    # 创建外部处理顶点
    def final_process_task(inputs):
        square_result = inputs.get("square_result", 0)
        sqrt_result = inputs.get("sqrt_result", 0)
        difference = abs(square_result - sqrt_result)
        print(f"  最终处理: |{square_result} - {sqrt_result:.2f}| = {difference:.2f}")
        return {"difference": difference}

    final_vertex = FunctionVertex(id="final_vertex", name="最终处理", task=final_process_task)

    # 执行数学运算组
    inputs = {"value": 16}
    context = WorkflowContext()

    print(f"输入值: {inputs['value']}")

    # 执行子图
    math_result = math_group.execute_subgraph(inputs, context)
    print(f"数学运算组输出: {math_result['subgraph_outputs']}")

    # 使用子图输出作为最终处理的输入
    final_inputs = math_result["subgraph_outputs"]
    final_vertex.execute(inputs=final_inputs, context=context)
    print(f"最终结果: {final_vertex.output}")

    return math_group, final_vertex


def example_4_dynamic_subgraph_construction():
    """
    示例4: 动态子图构建
    展示如何动态添加顶点和边到VertexGroup
    """
    print("\n=== 示例4: 动态子图构建 ===")

    # 创建空的VertexGroup
    dynamic_group = VertexGroup(id="dynamic_group", name="动态构建组")

    # 动态添加顶点
    def step1_task(inputs):
        value = inputs.get("start_value", 1)
        result = value + 10
        print(f"  步骤1: {value} + 10 = {result}")
        return {"step1_result": result}

    def step2_task(inputs):
        value = inputs.get("input_value", 0)
        result = value * 2
        print(f"  步骤2: {value} * 2 = {result}")
        return {"step2_result": result}

    def step3_task(inputs):
        value = inputs.get("input_value", 0)
        result = value - 5
        print(f"  步骤3: {value} - 5 = {result}")
        return {"step3_result": result}

    # 创建并添加顶点
    step1_vertex = FunctionVertex(id="step1", name="步骤1", task=step1_task)
    step2_vertex = FunctionVertex(
        id="step2",
        name="步骤2",
        task=step2_task,
        variables=[{"source_scope": "step1", "source_var": "step1_result", "local_var": "input_value"}],
    )
    step3_vertex = FunctionVertex(
        id="step3",
        name="步骤3",
        task=step3_task,
        variables=[{"source_scope": "step2", "source_var": "step2_result", "local_var": "input_value"}],
    )

    # 动态添加到组中
    dynamic_group.add_subgraph_vertex(step1_vertex)
    dynamic_group.add_subgraph_vertex(step2_vertex)
    dynamic_group.add_subgraph_vertex(step3_vertex)

    # 动态添加边
    dynamic_group.add_subgraph_edge(Edge(step1_vertex, step2_vertex, Always()))
    dynamic_group.add_subgraph_edge(Edge(step2_vertex, step3_vertex, Always()))

    # 动态添加暴露输出
    dynamic_group.add_exposed_output("step1", "step1_result", "first_step")
    dynamic_group.add_exposed_output("step2", "step2_result", "second_step")
    dynamic_group.add_exposed_output("step3", "step3_result", "final_step")

    print(f"动态构建的子图信息:")
    print(f"  顶点数量: {len(dynamic_group.get_subgraph_vertices())}")
    print(f"  边数量: {len(dynamic_group.get_subgraph_edges())}")
    print(f"  暴露输出数量: {len(dynamic_group.exposed_outputs)}")

    # 执行动态构建的子图
    inputs = {"start_value": 5}
    context = WorkflowContext()

    print(f"\n执行动态子图，输入: {inputs}")
    result = dynamic_group.execute_subgraph(inputs, context)

    print(f"执行结果:")
    for key, value in result["subgraph_outputs"].items():
        print(f"  {key}: {value}")

    return dynamic_group


def main():
    """
    运行所有示例
    """
    print("VertexGroup 使用示例")
    print("=" * 50)

    try:
        # 运行示例
        example_1_simple_calculation_subgraph()
        example_2_data_processing_pipeline()
        example_3_nested_vertex_groups()
        example_4_dynamic_subgraph_construction()

        print("\n=== 所有示例执行完成 ===")

    except Exception as e:
        print(f"\n执行示例时出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
