from unittest.mock import Mock

import pytest

from vertex_flow.workflow.constants import LOCAL_VAR, SOURCE_SCOPE, SOURCE_VAR
from vertex_flow.workflow.vertex import WhileCondition, WhileVertex
from vertex_flow.workflow.workflow import Workflow, WorkflowContext


class TestWhileVertex:
    """WhileVertex的测试类"""

    def test_while_vertex_with_condition_task(self):
        """测试使用condition_task的WhileVertex"""
        # 创建工作流
        workflow = Workflow("test_while_workflow")

        # 创建计数器变量
        counter = {"count": 0}

        def execute_logic(inputs):
            """执行逻辑：计数器加1"""
            counter["count"] += 1
            return {"count": counter["count"]}

        def condition_logic(inputs):
            """条件逻辑：计数器小于3时继续"""
            return counter["count"] < 3

        # 创建WhileVertex
        while_vertex = WhileVertex(
            id="while_test", name="While Test", execute_task=execute_logic, condition_task=condition_logic
        )

        # 添加到工作流
        workflow.add_vertex(while_vertex)

        # 创建上下文
        context = WorkflowContext(workflow)

        # 执行
        while_vertex.execute(inputs={}, context=context)

        # 验证结果
        result = while_vertex.output
        assert result["iteration_count"] == 3
        assert len(result["results"]) == 3
        assert result["results"][-1]["count"] == 3

    def test_while_vertex_with_conditions_list(self):
        """测试使用conditions列表的WhileVertex"""
        # 创建工作流
        workflow = Workflow("test_while_workflow")

        # 创建源顶点提供计数器
        from vertex_flow.workflow.vertex import SourceVertex

        source_vertex = SourceVertex(id="counter_source", name="Counter Source")
        source_vertex.output = {"count": 0}
        workflow.add_vertex(source_vertex)

        def execute_logic(inputs):
            """执行逻辑：计数器加1"""
            current_count = inputs.get("count", 0)
            new_count = current_count + 1
            # 更新源顶点的输出
            source_vertex.output = {"count": new_count}
            return {"count": new_count}

        # 创建条件：count < 5
        condition = WhileCondition(
            variable_selector={SOURCE_SCOPE: "counter_source", SOURCE_VAR: "count", LOCAL_VAR: "count"},
            operator="<",
            value=5,
        )

        # 创建WhileVertex
        while_vertex = WhileVertex(
            id="while_test",
            name="While Test",
            execute_task=execute_logic,
            conditions=[condition],
            variables=[{SOURCE_SCOPE: "counter_source", SOURCE_VAR: "count", LOCAL_VAR: "count"}],
        )

        # 添加到工作流
        workflow.add_vertex(while_vertex)

        # 创建上下文
        context = WorkflowContext(workflow)

        # 执行
        while_vertex.execute(inputs={"count": 0}, context=context)

        # 验证结果
        result = while_vertex.output
        assert result["iteration_count"] == 5
        assert len(result["results"]) == 5
        assert result["results"][-1]["count"] == 5

    def test_while_vertex_with_max_iterations(self):
        """测试最大迭代次数限制"""
        # 创建工作流
        workflow = Workflow("test_while_workflow")

        def execute_logic(inputs):
            """执行逻辑：简单返回"""
            return {"executed": True}

        def condition_logic(inputs):
            """条件逻辑：总是返回True（无限循环）"""
            return True

        # 创建WhileVertex，设置最大迭代次数为3
        while_vertex = WhileVertex(
            id="while_test",
            name="While Test",
            execute_task=execute_logic,
            condition_task=condition_logic,
            max_iterations=3,
        )

        # 添加到工作流
        workflow.add_vertex(while_vertex)

        # 创建上下文
        context = WorkflowContext(workflow)

        # 执行
        while_vertex.execute(inputs={}, context=context)

        # 验证结果
        result = while_vertex.output
        assert result["iteration_count"] == 3
        assert len(result["results"]) == 3

    def test_while_vertex_validation_errors(self):
        """测试WhileVertex的验证错误"""
        # 测试缺少execute_task
        with pytest.raises(ValueError, match="execute_task is required"):
            WhileVertex(id="test", execute_task=None, condition_task=lambda inputs: True)

        # 测试缺少条件
        with pytest.raises(ValueError, match="Either condition_task or conditions must be provided"):
            WhileVertex(id="test", execute_task=lambda inputs: {}, condition_task=None, conditions=None)

        # 测试同时提供两种条件
        with pytest.raises(ValueError, match="Cannot provide both condition_task and conditions"):
            WhileVertex(
                id="test",
                execute_task=lambda inputs: {},
                condition_task=lambda inputs: True,
                conditions=[WhileCondition({SOURCE_VAR: "test"}, "==", "value")],
            )

        # 测试无效的逻辑操作符
        with pytest.raises(ValueError, match="Unsupported logical operator"):
            WhileVertex(
                id="test",
                execute_task=lambda inputs: {},
                condition_task=lambda inputs: True,
                logical_operator="invalid",
            )

    def test_while_condition_operators(self):
        """测试WhileCondition的各种操作符"""
        # 创建工作流
        workflow = Workflow("test_while_workflow")

        # 创建源顶点
        from vertex_flow.workflow.vertex import SourceVertex

        source_vertex = SourceVertex(id="test_source", name="Test Source")
        source_vertex.output = {"value": "hello world"}
        workflow.add_vertex(source_vertex)

        def execute_logic(inputs):
            return {"executed": True}

        # 测试contains操作符
        condition = WhileCondition(
            variable_selector={SOURCE_SCOPE: "test_source", SOURCE_VAR: "value", LOCAL_VAR: "value"},
            operator="contains",
            value="world",
        )

        while_vertex = WhileVertex(
            id="while_test",
            execute_task=execute_logic,
            conditions=[condition],
            max_iterations=1,  # 只执行一次
            variables=[{SOURCE_SCOPE: "test_source", SOURCE_VAR: "value", LOCAL_VAR: "value"}],
        )

        workflow.add_vertex(while_vertex)
        context = WorkflowContext(workflow)

        # 执行
        while_vertex.execute(inputs={}, context=context)

        # 验证结果
        result = while_vertex.output
        assert result["iteration_count"] == 1
        assert len(result["results"]) == 1
