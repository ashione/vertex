#!/usr/bin/env python3
"""
链式调用示例：演示vertex的三种构图方法

这个示例展示了如何使用不同的API来构建workflow：
1. vertex_a.to(vertex_b) - 创建always edge的链式调用
2. vertex_a.c_to(vertex_b, "condition") - 创建conditional edge的链式调用
3. vertex_a | vertex_b - 使用 | 操作符的构图方法（保持向后兼容）
"""

from vertex_flow.workflow.edge import Always, Condition
from vertex_flow.workflow.vertex import LLMVertex, SinkVertex, SourceVertex
from vertex_flow.workflow.workflow import Workflow


def demo_basic_chain():
    """演示基本的链式调用"""
    print("\n" + "=" * 60)
    print("🔗 基本链式调用演示 - to方法")
    print("=" * 60)

    # 创建workflow
    workflow = Workflow()

    # 默认task函数
    def default_task(inputs, context):
        return inputs

    def sink_task(inputs, context):
        print(f"Sink received: {inputs}")
        return None

    # 创建vertices
    source = SourceVertex(id="source", name="数据源", task=default_task)
    llm1 = LLMVertex(id="llm1", name="第一个LLM", task=default_task)
    llm2 = LLMVertex(id="llm2", name="第二个LLM", task=default_task)
    llm3 = LLMVertex(id="llm3", name="第三个LLM", task=default_task)
    sink = SinkVertex(id="sink", name="输出", task=sink_task)

    # 添加到workflow
    workflow.add_vertex(source)
    workflow.add_vertex(llm1)
    workflow.add_vertex(llm2)
    workflow.add_vertex(llm3)
    workflow.add_vertex(sink)

    # 🔥 新的链式调用方法：source.to(llm1).to(llm2).to(llm3).to(sink)
    print("✅ 使用链式调用创建工作流：")
    print("   source.to(llm1).to(llm2).to(llm3).to(sink)")
    source.to(llm1).to(llm2).to(llm3).to(sink)

    print(f"✨ 总共创建了 {len(workflow.edges)} 条边")
    for edge in workflow.edges:
        print(f"   {edge.from_vertex.id} -> {edge.to_vertex.id}")


def demo_conditional_chain():
    """演示条件链式调用"""
    print("\n" + "=" * 60)
    print("🎯 条件链式调用演示 - c_to方法")
    print("=" * 60)

    # 创建workflow
    workflow = Workflow()

    def default_task(inputs, context):
        return inputs

    def check_task(inputs, context):
        # 模拟条件检查
        return {"result": "success", "data": inputs}

    def sink_task(inputs, context):
        print(f"Sink received: {inputs}")
        return None

    # 创建vertices
    source = SourceVertex(id="source", name="数据源", task=default_task)
    checker = LLMVertex(id="checker", name="条件检查器", task=check_task)
    success_path = LLMVertex(id="success", name="成功路径", task=default_task)
    failure_path = LLMVertex(id="failure", name="失败路径", task=default_task)
    final_process = LLMVertex(id="final", name="最终处理", task=default_task)
    sink = SinkVertex(id="sink", name="输出", task=sink_task)

    # 添加到workflow
    for vertex in [source, checker, success_path, failure_path, final_process, sink]:
        workflow.add_vertex(vertex)

    # 🔥 混合链式调用：条件分支 + 常规连接
    print("✅ 使用条件链式调用创建工作流：")
    print("   source.to(checker)")
    print("   checker.c_to(success_path, 'true').to(final_process)")
    print("   checker.c_to(failure_path, 'false').to(final_process)")
    print("   final_process.to(sink)")

    source.to(checker)
    checker.c_to(success_path, "true").to(final_process)
    checker.c_to(failure_path, "false").to(final_process)
    final_process.to(sink)

    print(f"✨ 总共创建了 {len(workflow.edges)} 条边")
    for edge in workflow.edges:
        edge_type = "条件边" if hasattr(edge.edge_type, "id") else "固定边"
        condition = f"({edge.edge_type.id})" if hasattr(edge.edge_type, "id") else ""
        print(f"   {edge.from_vertex.id} -> {edge.to_vertex.id} [{edge_type}{condition}]")


def demo_or_operator():
    """演示 | 操作符构图方法（保持向后兼容）"""
    print("\n" + "=" * 60)
    print("⚡ | 操作符构图演示 - __or__方法")
    print("=" * 60)

    # 创建workflow
    workflow = Workflow()

    def default_task(inputs, context):
        return inputs

    def sink_task(inputs, context):
        print(f"Sink received: {inputs}")
        return None

    # 创建vertices
    source = SourceVertex(id="source", name="数据源", task=default_task)
    transform1 = LLMVertex(id="transform1", name="转换器1", task=default_task)
    transform2 = LLMVertex(id="transform2", name="转换器2", task=default_task)
    aggregator = LLMVertex(id="aggregator", name="聚合器", task=default_task)
    sink = SinkVertex(id="sink", name="输出", task=sink_task)

    # 添加到workflow
    for vertex in [source, transform1, transform2, aggregator, sink]:
        workflow.add_vertex(vertex)

    # 🔥 使用 | 操作符构图（保持向后兼容性）
    print("✅ 使用 | 操作符创建工作流：")
    print("   source | transform1 | aggregator | sink")
    print("   source | transform2 | aggregator")

    source | transform1 | aggregator | sink
    source | transform2 | aggregator

    print(f"✨ 总共创建了 {len(workflow.edges)} 条边")
    for edge in workflow.edges:
        print(f"   {edge.from_vertex.id} -> {edge.to_vertex.id}")


def demo_mixed_approaches():
    """演示混合使用三种构图方法"""
    print("\n" + "=" * 60)
    print("🎨 混合构图方法演示")
    print("=" * 60)

    # 创建workflow
    workflow = Workflow()

    def default_task(inputs, context):
        return inputs

    def decision_task(inputs, context):
        return {"decision": "route_a", "data": inputs}

    def sink_task(inputs, context):
        print(f"Sink received: {inputs}")
        return None

    # 创建vertices
    start = SourceVertex(id="start", name="开始", task=default_task)
    preprocessor = LLMVertex(id="preprocess", name="预处理", task=default_task)
    decision = LLMVertex(id="decision", name="决策节点", task=decision_task)
    route_a = LLMVertex(id="route_a", name="路径A", task=default_task)
    route_b = LLMVertex(id="route_b", name="路径B", task=default_task)
    postprocessor = LLMVertex(id="postprocess", name="后处理", task=default_task)
    end = SinkVertex(id="end", name="结束", task=sink_task)

    # 添加到workflow
    for vertex in [start, preprocessor, decision, route_a, route_b, postprocessor, end]:
        workflow.add_vertex(vertex)

    # 🔥 混合使用三种构图方法
    print("✅ 混合使用三种构图方法：")
    print("   1. | 操作符: start | preprocessor")
    print("   2. to方法链式: preprocessor.to(decision)")
    print("   3. c_to条件分支: decision.c_to(route_a, 'route_a').to(postprocessor)")
    print("   4. c_to条件分支: decision.c_to(route_b, 'route_b')")
    print("   5. | 操作符: route_b | postprocessor | end")

    # 方法1：使用 | 操作符
    start | preprocessor

    # 方法2：使用 to 方法
    preprocessor.to(decision)

    # 方法3：使用 c_to 条件分支，然后链式调用 to
    decision.c_to(route_a, "route_a").to(postprocessor)
    decision.c_to(route_b, "route_b")

    # 方法4：混合使用 | 操作符
    route_b | postprocessor | end

    print(f"\n✨ 总共创建了 {len(workflow.edges)} 条边")
    for edge in workflow.edges:
        edge_type = "条件边" if hasattr(edge.edge_type, "id") else "固定边"
        condition = f"({edge.edge_type.id})" if hasattr(edge.edge_type, "id") else ""
        print(f"   {edge.from_vertex.id} -> {edge.to_vertex.id} [{edge_type}{condition}]")


def main():
    """主函数"""
    print("🚀 Vertex Flow 链式调用功能演示")
    print("=" * 60)
    print("这个演示展示了三种构图方法：")
    print("1. 🔗 to() - 创建always edge的链式调用")
    print("2. 🎯 c_to() - 创建conditional edge的链式调用")
    print("3. ⚡ | 操作符 - 使用管道操作符构图（向后兼容）")
    print("4. 🎨 混合使用 - 在同一个workflow中混合使用不同方法")

    try:
        demo_basic_chain()
        demo_conditional_chain()
        demo_or_operator()
        demo_mixed_approaches()

        print("\n" + "=" * 60)
        print("✅ 所有演示完成！")
        print("💡 提示：你可以根据需要选择最适合的构图方法：")
        print("   - 简单线性流程：使用 to() 链式调用")
        print("   - 条件分支流程：使用 c_to() 条件调用")
        print("   - 兼容旧代码：使用 | 操作符")
        print("   - 复杂流程：混合使用多种方法")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 演示过程中出现错误：{e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
