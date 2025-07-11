import traceback
from typing import Any, Callable, Dict, List, Optional

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import ITERATION_INDEX_KEY, LOCAL_VAR, SOURCE_SCOPE, SOURCE_VAR, SUBGRAPH_SOURCE
from vertex_flow.workflow.edge import Edge

from .vertex import T, Vertex, WorkflowContext
from .vertex_group import VertexGroup
from .while_vertex import WhileCondition, WhileVertex

logging = LoggerUtil.get_logger()


class WhileVertexGroup(VertexGroup[T]):
    """
    WhileVertexGroup是VertexGroup的子类，内置WhileVertex作为循环控制机制。
    它可以包含其他Vertex，并在循环中重复执行整个子图。
    """

    def __init__(
        self,
        id: str,
        name: Optional[str] = None,
        subgraph_vertices: Optional[List[Vertex[T]]] = None,
        subgraph_edges: Optional[List[Edge[T]]] = None,
        # WhileVertex参数
        condition_task: Optional[Callable] = None,
        conditions: Optional[List[WhileCondition]] = None,
        logical_operator: str = "and",
        max_iterations: Optional[int] = None,
        # 通用参数
        params: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        exposed_variables: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        初始化WhileVertexGroup

        Args:
            id: 顶点组ID
            name: 顶点组名称
            subgraph_vertices: 子图中的顶点列表
            subgraph_edges: 子图中的边列表
            condition_task: 条件判断逻辑的函数（可选，与conditions二选一）
            conditions: 条件列表（可选，与condition_task二选一）
            logical_operator: 多个条件之间的逻辑操作符
            max_iterations: 最大迭代次数（可选）
            params: 参数字典
            variables: 变量筛选列表，用于从外部输入中筛选变量传递给子图
            exposed_variables: 变量暴露列表，用于将子图内部顶点的输出暴露给外部
        """
        execute_task = self._execute_subgraph_as_task

        # 创建内置的WhileVertex
        self.while_vertex_id = f"{id}_while_controller"

        # 准备WhileVertex的参数，处理None值
        while_vertex_params = {
            "id": self.while_vertex_id,
            "name": f"{name or id} While Controller",
            "execute_task": execute_task,
            "logical_operator": logical_operator,
        }

        # 只有当值不为None时才添加参数
        if condition_task is not None:
            while_vertex_params["condition_task"] = condition_task
        if conditions is not None:
            while_vertex_params["conditions"] = conditions
        if max_iterations is not None:
            while_vertex_params["max_iterations"] = max_iterations

        self.while_vertex = WhileVertex(**while_vertex_params)

        # 重写WhileVertex的should_continue方法，使其使用WhileVertexGroup的变量筛选逻辑
        original_should_continue = self.while_vertex.should_continue

        def while_vertex_should_continue(inputs, context):
            """自定义的should_continue方法，使用WhileVertexGroup的变量筛选逻辑"""
            # 使用WhileVertexGroup的变量筛选逻辑
            filtered_inputs = self._filter_inputs(inputs, context)
            # 合并原始输入和筛选后的输入
            final_inputs = {**(inputs or {}), **filtered_inputs}

            # 确保ITERATION_INDEX_KEY在条件检查时可用
            if ITERATION_INDEX_KEY not in final_inputs and hasattr(self.while_vertex, "_iteration_index"):
                final_inputs[ITERATION_INDEX_KEY] = self.while_vertex._iteration_index

            # 调用原始的should_continue方法
            return original_should_continue(final_inputs, context)

        self.while_vertex.should_continue = while_vertex_should_continue

        # 调用父类构造函数
        super().__init__(
            id=id,
            name=name or id,  # 确保name不为None
            subgraph_vertices=subgraph_vertices or [],
            subgraph_edges=subgraph_edges or [],
            params=params or {},
            variables=variables or [],
            exposed_variables=exposed_variables or [],
        )

        # 重写task_type为专门的WHILE_VERTEX_GROUP类型
        self._task_type = "WHILE_VERTEX_GROUP"

    def _execute_subgraph_as_task(
        self, inputs: Optional[Dict[str, Any]] = None, context: Optional[WorkflowContext[T]] = None
    ):
        """
        将子图执行包装为WhileVertex的execute_task

        Args:
            inputs: 输入数据（已包含自动注入的索引信息）
            context: 工作流上下文

        Returns:
            子图执行的结果
        """
        try:
            if self.subgraph_context.parent_context is None and context is not None:
                self.subgraph_context.parent_context = context

            # 统一用父类的变量筛选逻辑，保留索引信息
            filtered_inputs = self._filter_inputs(inputs, context)
            final_inputs = {**(inputs or {}), **filtered_inputs}

            # 确保索引信息被保留并传递到子图
            if inputs and ITERATION_INDEX_KEY in inputs:
                final_inputs[ITERATION_INDEX_KEY] = inputs[ITERATION_INDEX_KEY]

            # 执行子图，但不处理暴露的输出（由最终的execute方法处理）
            result = self._execute_subgraph_impl(inputs=final_inputs, context=context)
            return result
        except Exception as e:
            logging.error(f"Error executing subgraph in WhileVertexGroup {self.id}: {e}")
            traceback.print_exc()
            raise e

    def execute(self, inputs: Optional[Dict[str, Any]] = None, context: Optional[WorkflowContext[T]] = None):
        """
        执行WhileVertexGroup，通过内置的WhileVertex进行循环控制

        Args:
            inputs: 输入数据
            context: 工作流上下文

        Returns:
            循环执行的结果
        """
        try:
            logging.info(f"Starting WhileVertexGroup {self.id} execution, inputs: {inputs}.")
            self._current_context = context
            if hasattr(self, "workflow") and self.workflow:
                self.while_vertex.workflow = self.workflow
                for vertex in self.subgraph_vertices.values():
                    vertex.workflow = self.workflow
            elif context is not None and hasattr(context, "workflow") and context.workflow:
                self.while_vertex.workflow = context.workflow
                for vertex in self.subgraph_vertices.values():
                    vertex.workflow = context.workflow
            # 统一用父类的变量筛选逻辑
            final_inputs = {**(inputs or {}), **self._filter_inputs(inputs, context)}
            if context is not None:
                self.while_vertex.execute(inputs=final_inputs, context=context)
            else:
                self.while_vertex.execute(inputs=final_inputs, context=None)
            self.output = self.while_vertex.output
            iteration_count = self.output.get("iteration_count", 0) if self.output else 0
            logging.info(f"WhileVertexGroup {self.id} completed with {iteration_count} iterations")

            # 复用父类的变量暴露逻辑
            exposed_output = self._expose_outputs(self.output)
            if exposed_output:
                self.output = exposed_output
            return self.output
        except Exception as e:
            logging.error(f"Error executing WhileVertexGroup {self.id}: {e}")
            traceback.print_exc()
            raise e

    def add_condition(self, condition: WhileCondition):
        """
        添加循环条件

        Args:
            condition: WhileCondition实例
        """
        if self.while_vertex.conditions is None:
            self.while_vertex.conditions = []
        self.while_vertex.conditions.append(condition)

    def set_condition_task(self, condition_task: Callable):
        """
        设置条件判断函数

        Args:
            condition_task: 条件判断函数
        """
        self.while_vertex.condition_task = condition_task
        # 如果设置了condition_task，则清空conditions
        self.while_vertex.conditions = []

    def set_max_iterations(self, max_iterations: int):
        """
        设置最大迭代次数

        Args:
            max_iterations: 最大迭代次数
        """
        self.while_vertex.max_iterations = max_iterations

    def get_iteration_count(self) -> int:
        """
        获取当前迭代次数

        Returns:
            当前迭代次数
        """
        if hasattr(self.while_vertex, "output") and self.while_vertex.output:
            return self.while_vertex.output.get("iteration_count", 0)
        return 0

    def get_loop_results(self) -> List[Any]:
        """
        获取所有循环迭代的结果

        Returns:
            循环结果列表
        """
        if hasattr(self.while_vertex, "output") and self.while_vertex.output:
            return self.while_vertex.output.get("results", [])
        return []

    def __str__(self) -> str:
        max_iter = getattr(self.while_vertex, "max_iterations", None)
        return f"WhileVertexGroup(id={self.id}, vertices={len(self.subgraph_vertices)}, edges={len(self.subgraph_edges)}, max_iterations={max_iter})"

    def __repr__(self) -> str:
        return self.__str__()
