#!/usr/bin/env python3
"""
WhileVertexGroup使用示例

演示如何使用WhileVertexGroup创建包含复杂子图的循环工作流
"""

import os
import sys
from typing import Any, Dict

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vertex_flow.workflow.edge import Always, Edge
from vertex_flow.workflow.vertex import FunctionVertex, SinkVertex, SourceVertex, WhileVertexGroup
from vertex_flow.workflow.workflow import Workflow


def create_simple_counter_example():
    """创建一个简单的计数器示例"""
    print("=== 创建简单计数器示例 ===")

    # 计数任务
    def increment_task(inputs, context=None):
        counter = inputs.get("counter", 0)
        return {"counter": counter + 1, "message": f"当前计数: {counter + 1}"}

    # 验证任务
    def validate_task(inputs, context=None):
        counter = inputs.get("counter", 0)
        is_valid = counter <= 10
        return {"counter": counter, "is_valid": is_valid, "status": "验证完成"}

    # 创建子图顶点
    increment_vertex = FunctionVertex(id="increment", task=increment_task)
    validate_vertex = FunctionVertex(id="validate", task=validate_task)

    # 创建子图边
    edge = Edge(increment_vertex, validate_vertex, Always())

    # 循环条件：计数小于5时继续
    def condition_task(inputs, context=None):
        counter = inputs.get("counter", 0)
        should_continue = counter < 5
        print(f"计数器检查: counter={counter}, continue={should_continue}")
        return should_continue

    # 循环执行任务：传递数据
    def execute_task(inputs, context=None):
        return inputs

    # 创建WhileVertexGroup
    while_group = WhileVertexGroup(
        id="counter_group",
        name="计数器循环组",
        subgraph_vertices=[increment_vertex, validate_vertex],
        subgraph_edges=[edge],
        condition_task=condition_task,
        execute_task=execute_task,
    )

    return while_group


def demo_counter_workflow():
    """演示计数器工作流"""
    print("\n" + "=" * 50)
    print("计数器工作流演示")
    print("=" * 50)

    # 创建工作流
    workflow = Workflow()

    # 创建源顶点
    def source_task(inputs, context=None):
        return {"counter": 0, "message": "开始计数"}

    source = SourceVertex(id="source", task=source_task)

    # 创建WhileVertexGroup
    while_group = create_simple_counter_example()

    # 创建汇顶点
    def sink_task(inputs, context=None):
        counter = inputs.get("counter", 0)
        print(f"\n计数完成！最终计数: {counter}")
        if context:
            context.set_output("final_counter", counter)
            context.set_output("completed", True)
        return None

    sink = SinkVertex(id="sink", task=sink_task)

    # 添加顶点到工作流
    workflow.add_vertex(source)
    workflow.add_vertex(while_group)
    workflow.add_vertex(sink)

    # 连接顶点
    source | while_group | sink

    print(f"工作流创建完成，包含 {len(workflow.vertices)} 个顶点")
    print(f"WhileVertexGroup包含 {len(while_group.subgraph_vertices)} 个子图顶点")

    # 显示工作流结构
    print("\n工作流结构:")
    for vertex_id, vertex in workflow.vertices.items():
        task_type = getattr(vertex, "task_type", "UNKNOWN")
        print(f"  - {vertex_id}: {task_type}")

    print("\nWhileVertexGroup子图结构:")
    for vertex_id, vertex in while_group.subgraph_vertices.items():
        task_type = getattr(vertex, "task_type", "UNKNOWN")
        print(f"  - {vertex_id}: {task_type}")

    return workflow


def main():
    """主函数"""
    print("WhileVertexGroup使用示例")
    print("=" * 50)

    try:
        # 演示计数器工作流
        counter_workflow = demo_counter_workflow()
        print("✅ 计数器工作流创建成功")

        print("\n" + "=" * 50)
        print("WhileVertexGroup核心功能:")
        print("1. 继承自VertexGroup，支持子图管理")
        print("2. 内置WhileVertex，提供循环控制")
        print("3. 支持复杂的子图结构和边连接")
        print("4. 灵活的循环条件和执行逻辑")
        print("5. 可作为标准vertex集成到任何工作流")
        print("6. task_type显示为WHILE_VERTEX_GROUP")
        print("=" * 50)

    except Exception as e:
        print(f"❌ 示例执行失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
