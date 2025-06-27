from unittest.mock import Mock

import pytest

from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.edge import Always, Edge
from vertex_flow.workflow.vertex import FunctionVertex, SubgraphContext, VertexGroup


class TestSubgraphContext:
    """测试SubgraphContext类"""

    def test_init(self):
        """测试SubgraphContext初始化"""
        parent_context = WorkflowContext()
        context = SubgraphContext(parent_context)

        assert context.parent_context == parent_context
        assert context.internal_outputs == {}
        assert context.exposed_variables == {}

    def test_store_and_get_internal_output(self):
        """测试存储和获取内部输出"""
        context = SubgraphContext()

        # 存储输出
        context.store_internal_output("vertex1", {"result": 42})
        context.store_internal_output("vertex2", "hello")

        # 获取输出
        assert context.get_internal_output("vertex1") == {"result": 42}
        assert context.get_internal_output("vertex2") == "hello"
        assert context.get_internal_output("nonexistent") is None

    def test_expose_variable(self):
        """测试暴露变量"""
        context = SubgraphContext()

        # 存储一些内部输出
        context.store_internal_output("vertex1", {"x": 10, "y": 20})
        context.store_internal_output("vertex2", "simple_value")

        # 暴露字典中的特定变量
        context.expose_variable("vertex1", "x", "exposed_x")
        context.expose_variable("vertex1", "y")  # 使用原名

        # 暴露整个值
        context.expose_variable("vertex2", None, "simple")

        exposed = context.get_exposed_variables()
        assert exposed["exposed_x"] == 10
        assert exposed["y"] == 20
        assert exposed["simple"] == "simple_value"


class TestVertexGroup:
    """测试VertexGroup类"""

    def create_simple_vertices(self):
        """创建简单的测试顶点"""

        def add_task(inputs, context=None):
            a = inputs.get("a", 0)
            b = inputs.get("b", 0)
            return {"sum": a + b}

        def multiply_task(inputs, context=None):
            value = inputs.get("value", 1)
            factor = inputs.get("factor", 2)
            return {"product": value * factor}

        vertex1 = FunctionVertex(id="add_vertex", name="Add Vertex", task=add_task)

        vertex2 = FunctionVertex(
            id="multiply_vertex",
            name="Multiply Vertex",
            task=multiply_task,
            variables=[{"source_scope": "add_vertex", "source_var": "sum", "local_var": "value"}],
        )

        return vertex1, vertex2

    def test_init(self):
        """测试VertexGroup初始化"""
        vertex1, vertex2 = self.create_simple_vertices()
        edge = Edge(vertex1, vertex2, Always())

        variables = [
            {"source_scope": "add_vertex", "source_var": "sum", "local_var": "addition_result"},
            {"source_scope": "multiply_vertex", "source_var": "product", "local_var": "final_result"},
        ]

        group = VertexGroup(
            id="test_group",
            name="Test Group",
            subgraph_vertices=[vertex1, vertex2],
            subgraph_edges=[edge],
            variables=variables,
        )

        assert group.id == "test_group"
        assert group.name == "Test Group"
        assert len(group.subgraph_vertices) == 2
        assert len(group.subgraph_edges) == 1
        assert len(group.variables) == 2
        assert vertex1._vertex_group_ref == group
        assert vertex2._vertex_group_ref == group

    def test_validate_subgraph_invalid_edge(self):
        """测试子图验证 - 无效边"""
        vertex1, vertex2 = self.create_simple_vertices()

        # 创建一个不在子图中的顶点
        external_vertex = FunctionVertex(id="external", task=lambda inputs, context=None: inputs)
        invalid_edge = Edge(vertex1, external_vertex, Always())

        with pytest.raises(ValueError, match="Edge .* contains vertices not in subgraph"):
            VertexGroup(id="invalid_group", subgraph_vertices=[vertex1, vertex2], subgraph_edges=[invalid_edge])

    def test_validate_subgraph_invalid_variable(self):
        """测试子图验证 - 无效变量引用"""
        vertex1, vertex2 = self.create_simple_vertices()

        variables = [{"source_scope": "nonexistent_vertex", "source_var": "some_var", "local_var": "local"}]

        with pytest.raises(ValueError, match="Variable source_scope .* not found in subgraph"):
            VertexGroup(id="invalid_group", subgraph_vertices=[vertex1, vertex2], variables=variables)

    def test_add_subgraph_vertex(self):
        """测试添加子图顶点"""
        group = VertexGroup(id="test_group")
        vertex = FunctionVertex(id="new_vertex", task=lambda inputs, context=None: inputs)

        result = group.add_subgraph_vertex(vertex)

        assert result == vertex
        assert vertex.id in group.subgraph_vertices
        assert vertex._vertex_group_ref == group

    def test_add_subgraph_edge(self):
        """测试添加子图边"""
        vertex1, vertex2 = self.create_simple_vertices()
        group = VertexGroup(id="test_group", subgraph_vertices=[vertex1, vertex2])

        edge = Edge(vertex1, vertex2, Always())
        group.add_subgraph_edge(edge)

        assert edge in group.subgraph_edges
        assert vertex2.in_degree > 0
        assert vertex1.out_degree > 0
        assert vertex1.id in vertex2.dependencies

    def test_add_subgraph_edge_invalid_vertices(self):
        """测试添加子图边 - 无效顶点"""
        vertex1, vertex2 = self.create_simple_vertices()
        external_vertex = FunctionVertex(id="external", task=lambda inputs, context=None: inputs)

        group = VertexGroup(id="test_group", subgraph_vertices=[vertex1, vertex2])

        invalid_edge = Edge(vertex1, external_vertex, Always())

        with pytest.raises(ValueError, match="Both vertices must be in the subgraph"):
            group.add_subgraph_edge(invalid_edge)

    def test_get_subgraph_sources(self):
        """测试获取子图源顶点"""
        vertex1, vertex2 = self.create_simple_vertices()
        edge = Edge(vertex1, vertex2, Always())

        group = VertexGroup(id="test_group", subgraph_vertices=[vertex1, vertex2], subgraph_edges=[edge])

        sources = group.get_subgraph_sources()
        assert len(sources) == 1
        assert sources[0] == vertex1

    def test_get_subgraph_sinks(self):
        """测试获取子图汇顶点"""
        vertex1, vertex2 = self.create_simple_vertices()
        edge = Edge(vertex1, vertex2, Always())

        group = VertexGroup(id="test_group", subgraph_vertices=[vertex1, vertex2], subgraph_edges=[edge])

        sinks = group.get_subgraph_sinks()
        assert len(sinks) == 1
        assert sinks[0] == vertex2

    def test_topological_sort_subgraph(self):
        """测试子图拓扑排序"""
        vertex1, vertex2 = self.create_simple_vertices()
        edge = Edge(vertex1, vertex2, Always())

        group = VertexGroup(id="test_group", subgraph_vertices=[vertex1, vertex2], subgraph_edges=[edge])

        order = group.topological_sort_subgraph()
        assert len(order) == 2
        assert order[0] == vertex1  # vertex1应该在vertex2之前
        assert order[1] == vertex2

    def test_topological_sort_subgraph_cycle(self):
        """测试子图拓扑排序 - 循环检测"""
        vertex1, vertex2 = self.create_simple_vertices()
        edge1 = Edge(vertex1, vertex2, Always())
        edge2 = Edge(vertex2, vertex1, Always())  # 创建循环

        group = VertexGroup(id="test_group", subgraph_vertices=[vertex1, vertex2], subgraph_edges=[edge1, edge2])

        with pytest.raises(ValueError, match="Subgraph contains a cycle"):
            group.topological_sort_subgraph()

    def test_execute_subgraph_no_vertices(self):
        """测试空子图执行"""
        group = VertexGroup(id="empty_group")

        result = group.execute_subgraph()

        # 空子图应该返回执行摘要
        assert "execution_summary" in result
        assert result["execution_summary"]["success"] is True
        assert result["execution_summary"]["total_vertices"] == 0

    def test_add_exposed_output(self):
        """测试添加暴露输出配置"""
        group = VertexGroup(id="test_group")

        group.add_exposed_output("vertex1", "var1", "exposed_var1")
        group.add_exposed_output("vertex2", "var2")  # 使用默认暴露名

        assert len(group.variables) == 2
        assert group.variables[0] == {"source_scope": "vertex1", "source_var": "var1", "local_var": "exposed_var1"}
        assert group.variables[1] == {"source_scope": "vertex2", "source_var": "var2", "local_var": "var2"}

    def test_get_methods(self):
        """测试获取方法"""
        vertex1, vertex2 = self.create_simple_vertices()
        edge = Edge(vertex1, vertex2, Always())

        group = VertexGroup(id="test_group", subgraph_vertices=[vertex1, vertex2], subgraph_edges=[edge])

        # 测试获取子图顶点
        assert group.get_subgraph_vertex("add_vertex") == vertex1
        assert group.get_subgraph_vertex("nonexistent") is None

        # 测试获取所有顶点
        vertices = group.get_subgraph_vertices()
        assert len(vertices) == 2
        assert "add_vertex" in vertices
        assert "multiply_vertex" in vertices

        # 测试获取所有边
        edges = group.get_subgraph_edges()
        assert len(edges) == 1
        assert edge in edges

    def test_str_and_repr(self):
        """测试字符串表示"""
        vertex1, vertex2 = self.create_simple_vertices()
        edge = Edge(vertex1, vertex2, Always())

        group = VertexGroup(id="test_group", subgraph_vertices=[vertex1, vertex2], subgraph_edges=[edge])

        str_repr = str(group)
        assert "VertexGroup" in str_repr
        assert "test_group" in str_repr
        assert "vertices=2" in str_repr
        assert "edges=1" in str_repr

        assert repr(group) == str(group)


if __name__ == "__main__":
    pytest.main([__file__])
