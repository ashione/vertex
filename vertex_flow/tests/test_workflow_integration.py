import pytest

from vertex_flow.utils.logger import logging
from vertex_flow.workflow.constants import LOCAL_VAR, SOURCE_SCOPE, SOURCE_VAR
from vertex_flow.workflow.edge import Always, Edge
from vertex_flow.workflow.vertex import FunctionVertex, SinkVertex, SourceVertex, VertexGroup
from vertex_flow.workflow.workflow import Workflow, WorkflowContext

logger = logging.getLogger()


class TestWorkflowIntegration:
    """测试VertexGroup与普通Vertex在Workflow中的集成"""

    def create_simple_vertex_group(self):
        """创建一个简单的VertexGroup"""

        # 创建子图中的顶点
        def add_task(inputs):
            logger.info(f"Add task executed with inputs: {inputs}")
            a = inputs.get("a", 0)
            b = inputs.get("b", 0)
            return {"sum": a + b}

        def multiply_task(inputs):
            logger.info(f"Multiply task executed with inputs: {inputs}")
            value = inputs.get("sum", 0)
            factor = inputs.get("factor", 1)
            return {"product": value * factor}

        add_vertex = FunctionVertex(id="add_vertex", name="Add Vertex", task=add_task)

        # 设置add_vertex的变量依赖 - 从输入获取a和b
        add_vertex.add_variable("source", "a", "a")
        add_vertex.add_variable("source", "b", "b")

        multiply_vertex = FunctionVertex(id="multiply_vertex", name="Multiply Vertex", task=multiply_task)

        # 设置multiply_vertex的变量依赖
        multiply_vertex.add_variable("add_vertex", "sum", "sum")
        multiply_vertex.add_variable("source", "factor", "factor")

        # 创建VertexGroup
        vertex_group = VertexGroup(id="math_group", name="Math Operations Group")

        # 添加顶点到子图
        vertex_group.add_subgraph_vertex(add_vertex)
        vertex_group.add_subgraph_vertex(multiply_vertex)

        # 添加子图内的边
        edge = Edge(add_vertex, multiply_vertex, Always())
        vertex_group.add_subgraph_edge(edge)

        # 暴露输出
        vertex_group.add_exposed_output(vertex_id="multiply_vertex", variable="product", exposed_as="final_result")

        return vertex_group

    def test_vertex_group_with_source_and_sink(self):
        """测试VertexGroup与SourceVertex和SinkVertex组成workflow"""
        # 创建workflow
        context = WorkflowContext()
        workflow = Workflow(context)

        # 创建SourceVertex
        def source_task(inputs, context):
            return inputs

        source_vertex = SourceVertex(id="source", name="Source", task=source_task)

        # 创建VertexGroup
        vertex_group = self.create_simple_vertex_group()

        # 创建SinkVertex
        def sink_task(inputs, context):
            return inputs

        sink_vertex = SinkVertex(id="sink", name="Sink", task=sink_task)

        # 添加顶点到workflow
        workflow.add_vertex(source_vertex)
        workflow.add_vertex(vertex_group)
        workflow.add_vertex(sink_vertex)

        # 添加边
        workflow.add_edge(Edge(source_vertex, vertex_group, Always()))
        workflow.add_edge(Edge(vertex_group, sink_vertex, Always()))

        # 执行workflow
        test_input = {"a": 3, "b": 5, "factor": 4}
        workflow.execute_workflow(test_input, stream=False)

        # 验证结果
        result = workflow.result()
        assert "sink" in result
        assert "math_group" in result["sink"]
        assert result["sink"]["math_group"]["final_result"] == 32  # (3+5) * 4 = 32

    def test_vertex_group_with_function_vertices(self):
        """测试VertexGroup与FunctionVertex组成workflow"""
        # 创建workflow
        context = WorkflowContext()
        workflow = Workflow(context)

        # 创建SourceVertex
        def source_task(inputs, context):
            return inputs

        source_vertex = SourceVertex(id="source", name="Source", task=source_task)

        # 创建前处理FunctionVertex
        def preprocess_task(inputs):
            logger.info(f"Preprocess task executed with inputs: {inputs}")
            x = inputs.get("x", 0)
            y = inputs.get("y", 0)
            return {"a": x * 2, "b": y * 3, "factor": 2}

        preprocess_vertex = FunctionVertex(id="preprocess", name="Preprocess", task=preprocess_task)

        # 设置preprocess_vertex的变量依赖
        preprocess_vertex.add_variable("source", "x", "x")
        preprocess_vertex.add_variable("source", "y", "y")

        # 创建VertexGroup
        vertex_group = self.create_simple_vertex_group()
        vertex_group.get_subgraph_vertex("add_vertex").add_variable("preprocess", "a", "a")
        vertex_group.get_subgraph_vertex("add_vertex").add_variable("preprocess", "b", "b")
        vertex_group.get_subgraph_vertex("multiply_vertex").add_variable("preprocess", "factor", "factor")

        # 创建后处理FunctionVertex
        def postprocess_task(inputs):
            result = inputs.get("final_result", 0)
            return {"formatted_result": f"Final answer: {result}"}

        postprocess_vertex = FunctionVertex(id="postprocess", name="Postprocess", task=postprocess_task)

        # 创建SinkVertex
        def sink_task(inputs, context):
            return inputs

        sink_vertex = SinkVertex(id="sink", name="Sink", task=sink_task)

        # 设置变量依赖
        postprocess_vertex.add_variable("math_group", "final_result", "final_result")

        # 添加顶点到workflow
        workflow.add_vertex(source_vertex)
        workflow.add_vertex(preprocess_vertex)
        workflow.add_vertex(vertex_group)
        workflow.add_vertex(postprocess_vertex)
        workflow.add_vertex(sink_vertex)

        # 添加边
        workflow.add_edge(Edge(source_vertex, preprocess_vertex, Always()))
        workflow.add_edge(Edge(preprocess_vertex, vertex_group, Always()))
        workflow.add_edge(Edge(vertex_group, postprocess_vertex, Always()))
        workflow.add_edge(Edge(postprocess_vertex, sink_vertex, Always()))

        # 执行workflow
        test_input = {"x": 2, "y": 3}
        workflow.execute_workflow(test_input, stream=False)

        # 验证结果
        result = workflow.result()
        assert "sink" in result
        assert "postprocess" in result["sink"]
        # preprocess: a=4, b=9, factor=2
        # vertex_group: (4+9) * 2 = 26
        assert result["sink"]["postprocess"]["formatted_result"] == "Final answer: 26"

    def test_multiple_vertex_groups_in_workflow(self):
        """测试多个VertexGroup在同一个workflow中"""
        # 创建workflow
        context = WorkflowContext()
        workflow = Workflow(context)

        # 创建SourceVertex
        def source_task(inputs, context):
            return inputs

        source_vertex = SourceVertex(id="source", name="Source", task=source_task)

        # 创建第一个VertexGroup（数学运算）
        math_group = self.create_simple_vertex_group()
        math_group._id = "math_group"

        # 创建第二个VertexGroup（字符串处理）
        def concat_task(inputs):
            prefix = inputs.get("prefix", "")
            suffix = inputs.get("suffix", "")
            return {"text": prefix + suffix}

        def format_task(inputs):
            text = inputs.get("text", "")
            number = inputs.get("number", 0)
            return {"formatted": f"{text}: {number}"}

        concat_vertex = FunctionVertex(id="concat_vertex", name="Concat Vertex", task=concat_task)

        # 设置concat_vertex的变量依赖
        concat_vertex.add_variable("bridge", "prefix", "prefix")
        concat_vertex.add_variable("bridge", "suffix", "suffix")

        format_vertex = FunctionVertex(id="format_vertex", name="Format Vertex", task=format_task)

        # 设置format_vertex的变量依赖
        format_vertex.add_variable("concat_vertex", "text", "text")
        format_vertex.add_variable("bridge", "number", "number")

        string_group = VertexGroup(id="string_group", name="String Processing Group")

        string_group.add_subgraph_vertex(concat_vertex)
        string_group.add_subgraph_vertex(format_vertex)
        string_group.add_subgraph_edge(Edge(concat_vertex, format_vertex, Always()))
        string_group.add_exposed_output(vertex_id="format_vertex", variable="formatted", exposed_as="result")

        # 创建连接两个VertexGroup的FunctionVertex
        def bridge_task(inputs):
            math_result = inputs.get("final_result", 0)
            return {"prefix": "Result", "suffix": " calculated", "number": math_result}

        bridge_vertex = FunctionVertex(id="bridge", name="Bridge", task=bridge_task)

        bridge_vertex.add_variable("math_group", "final_result", "final_result")

        # 创建SinkVertex
        def sink_task(inputs, context):
            return inputs

        sink_vertex = SinkVertex(id="sink", name="Sink", task=sink_task)

        # 添加顶点到workflow
        workflow.add_vertex(source_vertex)
        workflow.add_vertex(math_group)
        workflow.add_vertex(bridge_vertex)
        workflow.add_vertex(string_group)
        workflow.add_vertex(sink_vertex)

        # 添加边
        workflow.add_edge(Edge(source_vertex, math_group, Always()))
        workflow.add_edge(Edge(math_group, bridge_vertex, Always()))
        workflow.add_edge(Edge(bridge_vertex, string_group, Always()))
        workflow.add_edge(Edge(string_group, sink_vertex, Always()))

        # 执行workflow
        test_input = {"a": 5, "b": 7, "factor": 3}
        workflow.execute_workflow(test_input, stream=False)

        # 验证结果
        result = workflow.result()
        assert "sink" in result
        assert "string_group" in result["sink"]
        # math_group: (5+7) * 3 = 36
        # string_group: "Result calculated: 36"
        logger.info(f"sink result {result}")
        assert result["sink"]["string_group"]["result"] == "Result calculated: 36"

    def test_vertex_group_error_handling(self):
        """测试VertexGroup在workflow中的错误处理"""

        # 创建会出错的VertexGroup
        def error_task(inputs):
            raise ValueError("Intentional error for testing")

        error_vertex = FunctionVertex(id="error_vertex", name="Error Vertex", task=error_task)

        error_group = VertexGroup(id="error_group", name="Error Group")

        error_group.add_subgraph_vertex(error_vertex)
        error_group.add_exposed_output(vertex_id="error_vertex", variable="result", exposed_as="output")

        # 创建workflow
        context = WorkflowContext()
        workflow = Workflow(context)

        # 添加SourceVertex和SinkVertex
        def source_task(inputs, context):
            return inputs

        source_vertex = SourceVertex(id="source", name="Source", task=source_task)

        def sink_task(inputs, context):
            return inputs

        sink_vertex = SinkVertex(id="sink", name="Sink", task=sink_task)

        workflow.add_vertex(source_vertex)
        workflow.add_vertex(error_group)
        workflow.add_vertex(sink_vertex)

        # 添加边
        workflow.add_edge(Edge(source_vertex, error_group, Always()))
        workflow.add_edge(Edge(error_group, sink_vertex, Always()))

        # 执行workflow应该抛出异常
        with pytest.raises(ValueError, match="Intentional error for testing"):
            workflow.execute_workflow({}, stream=False)

    def test_vertex_group_as_dependency(self):
        """测试VertexGroup作为其他顶点的依赖"""
        # 创建workflow
        context = WorkflowContext()
        workflow = Workflow(context)

        # 创建SourceVertex
        def source_task(inputs, context):
            return inputs

        source_vertex = SourceVertex(id="source", name="Source", task=source_task)

        # 创建VertexGroup
        vertex_group = self.create_simple_vertex_group()

        # 创建依赖VertexGroup输出的FunctionVertex
        def dependent_task(inputs):
            group_result = inputs.get("final_result", 0)
            return {"doubled": group_result * 2}

        dependent_vertex = FunctionVertex(id="dependent", name="Dependent Vertex", task=dependent_task)

        # 设置依赖关系
        dependent_vertex.add_variable("math_group", "final_result", "final_result")

        # 创建SinkVertex
        def sink_task(inputs, context):
            return inputs

        sink_vertex = SinkVertex(id="sink", name="Sink", task=sink_task)

        # 添加顶点到workflow
        workflow.add_vertex(source_vertex)
        workflow.add_vertex(vertex_group)
        workflow.add_vertex(dependent_vertex)
        workflow.add_vertex(sink_vertex)

        # 添加边
        workflow.add_edge(Edge(source_vertex, vertex_group, Always()))
        workflow.add_edge(Edge(vertex_group, dependent_vertex, Always()))
        workflow.add_edge(Edge(dependent_vertex, sink_vertex, Always()))

        # 执行workflow
        test_input = {"a": 4, "b": 6, "factor": 2}
        workflow.execute_workflow(test_input, stream=False)

        # 验证结果
        result = workflow.result()
        assert "sink" in result
        assert "dependent" in result["sink"]
        print(f"result: {result}")
        # vertex_group: (4+6) * 2 = 20
        # dependent: 20 * 2 = 40
        assert result["sink"]["dependent"]["doubled"] == 40
