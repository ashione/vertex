import logging
import traceback
from collections import deque
from typing import Any, Dict, List, Optional, Set

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import LOCAL_VAR, SOURCE_SCOPE, SOURCE_VAR
from vertex_flow.workflow.edge import Edge, EdgeType

from .vertex import T, Vertex, WorkflowContext

logging = LoggerUtil.get_logger()


class SubgraphContext:
    """子图上下文，用于管理子图内部的变量和输出"""

    def __init__(self, parent_context: WorkflowContext[T] = None):
        self.parent_context = parent_context
        self.internal_outputs = {}  # 子图内部顶点的输出
        self.exposed_variables = {}  # 暴露给外部的变量

    def store_internal_output(self, vertex_id: str, output_data: T):
        """存储子图内部顶点的输出"""
        self.internal_outputs[vertex_id] = output_data

    def get_internal_output(self, vertex_id: str) -> T:
        """获取子图内部顶点的输出"""
        return self.internal_outputs.get(vertex_id, None)

    def expose_variable(self, internal_vertex_id: str, variable_name: str, exposed_name: str = None):
        """暴露子图内部变量给外部"""
        exposed_name = exposed_name or variable_name
        if internal_vertex_id in self.internal_outputs:
            output = self.internal_outputs[internal_vertex_id]
            if isinstance(output, dict) and variable_name in output:
                self.exposed_variables[exposed_name] = output[variable_name]
            elif variable_name is None:
                self.exposed_variables[exposed_name] = output

    def get_exposed_variables(self) -> Dict[str, Any]:
        """获取所有暴露的变量"""
        return self.exposed_variables.copy()


class VertexGroup(Vertex[T]):
    """顶点组，包含一个子图，作为一个Vertex的子图/Subgraph"""

    def __init__(
        self,
        id: str,
        name: str = None,
        subgraph_vertices: List[Vertex[T]] = None,
        subgraph_edges: List[Edge[T]] = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    ):
        """
        初始化VertexGroup

        Args:
            id: 顶点组ID
            name: 顶点组名称
            subgraph_vertices: 子图中的顶点列表
            subgraph_edges: 子图中的边列表
            params: 参数字典
            variables: 变量列表，用于定义暴露给外部的输出
                格式: [{"source_scope": "内部顶点ID", "source_var": "变量名", "local_var": "暴露名称"}]
        """
        super().__init__(
            id=id,
            name=name,
            task_type="VERTEX_GROUP",
            task=self.execute_subgraph,
            params=params,
            variables=variables,
        )

        # 用add_subgraph_vertex方法注册所有子图顶点，保证依赖查找优先在子图内
        self.subgraph_vertices = {}
        for v in (subgraph_vertices or []):
            self.add_subgraph_vertex(v)
        self.subgraph_edges = set(subgraph_edges or [])
        self.subgraph_context = SubgraphContext()

        # 为子图中的顶点设置引用（已在add_subgraph_vertex中处理，无需重复）

        self._validate_subgraph()

    @property
    def workflow(self):
        """获取workflow引用"""
        return getattr(self, "_workflow", None)

    @workflow.setter
    def workflow(self, workflow):
        """设置workflow引用，并传递给所有子图vertex"""
        self._workflow = workflow
        # 更新所有子图vertex的workflow引用
        for vertex in self.subgraph_vertices.values():
            vertex.workflow = workflow

    def _validate_subgraph(self):
        """验证子图的有效性"""
        # 检查边的顶点是否都在子图中
        for edge in self.subgraph_edges:
            if (
                edge.source_vertex.id not in self.subgraph_vertices
                or edge.target_vertex.id not in self.subgraph_vertices
            ):
                raise ValueError(
                    f"Edge {edge} contains vertices not in subgraph: "
                    f"source={edge.source_vertex.id}, target={edge.target_vertex.id}"
                )

        # 检查variables中引用的顶点是否都在子图中
        for var_def in self.variables:
            source_scope = var_def.get(SOURCE_SCOPE)
            if source_scope and source_scope not in self.subgraph_vertices:
                raise ValueError(f"Variable source_scope '{source_scope}' not found in subgraph")

    def add_subgraph_vertex(self, vertex: Vertex[T]) -> Vertex[T]:
        """添加顶点到子图"""
        self.subgraph_vertices[vertex.id] = vertex
        vertex._vertex_group_ref = self
        # 如果VertexGroup已经有workflow引用，则传递给子图vertex
        if hasattr(self, "workflow") and self.workflow:
            vertex.workflow = self.workflow

        # 重写子图vertex的resolve_dependencies方法，使其使用vertex_group的resolve_dependencies
        original_resolve_dependencies = vertex.resolve_dependencies

        def vertex_group_resolve_dependencies(inputs=None, variables=None):
            return self.resolve_dependencies(vertex, inputs, getattr(self, "_current_context", None))

        vertex.resolve_dependencies = vertex_group_resolve_dependencies

        return vertex

    def add_subgraph_edge(self, edge: Edge[T]):
        """添加边到子图"""
        if edge.source_vertex.id not in self.subgraph_vertices or edge.target_vertex.id not in self.subgraph_vertices:
            raise ValueError("Both vertices must be in the subgraph before adding edge")

        self.subgraph_edges.add(edge)

        # 更新子图内顶点的度数和依赖关系
        target_vertex = self.subgraph_vertices[edge.target_vertex.id]
        source_vertex = self.subgraph_vertices[edge.source_vertex.id]

        target_vertex.in_degree += 1
        target_vertex.dependencies.add(edge.source_vertex.id)
        source_vertex.out_degree += 1

    def get_subgraph_sources(self) -> List[Vertex[T]]:
        """获取子图的源顶点（入度为0的顶点）"""
        sources = []
        for vertex in self.subgraph_vertices.values():
            # 计算在子图内的实际入度
            internal_in_degree = sum(1 for edge in self.subgraph_edges if edge.target_vertex.id == vertex.id)
            if internal_in_degree == 0:
                sources.append(vertex)
        return sources

    def get_subgraph_sinks(self) -> List[Vertex[T]]:
        """获取子图的汇顶点（出度为0的顶点）"""
        sinks = []
        for vertex in self.subgraph_vertices.values():
            # 计算在子图内的实际出度
            internal_out_degree = sum(1 for edge in self.subgraph_edges if edge.source_vertex.id == vertex.id)
            if internal_out_degree == 0:
                sinks.append(vertex)
        return sinks

    def topological_sort_subgraph(self) -> List[Vertex[T]]:
        """对子图进行拓扑排序"""
        # 创建顶点的入度副本（仅考虑子图内的边）
        in_degrees = {}
        for vertex_id in self.subgraph_vertices:
            in_degrees[vertex_id] = sum(1 for edge in self.subgraph_edges if edge.target_vertex.id == vertex_id)

        # 获取入度为0的顶点
        queue = deque([self.subgraph_vertices[vertex_id] for vertex_id, degree in in_degrees.items() if degree == 0])

        topological_order = []

        while queue:
            vertex = queue.popleft()
            topological_order.append(vertex)

            # 减少相邻顶点的入度
            for edge in self.subgraph_edges:
                if edge.source_vertex.id == vertex.id:
                    target_id = edge.target_vertex.id
                    in_degrees[target_id] -= 1
                    if in_degrees[target_id] == 0:
                        queue.append(self.subgraph_vertices[target_id])

        if len(topological_order) != len(self.subgraph_vertices):
            raise ValueError(
                f"Subgraph contains a cycle, cannot perform topological sort. "
                f"Sorted: {len(topological_order)}, Total: {len(self.subgraph_vertices)}"
            )

        return topological_order

    def resolve_subgraph_dependencies(self, vertex: Vertex[T], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """解析子图内顶点的依赖关系"""

        # 如果顶点没有变量定义，直接返回原始输入
        if not vertex.variables:
            return inputs

        resolved_values = {}

        for variable in vertex.variables:
            source_scope = variable[SOURCE_SCOPE]
            source_var = variable[SOURCE_VAR]
            local_var = variable[LOCAL_VAR]

            if source_scope == "source":
                # 从输入中获取变量
                if source_var in inputs:
                    resolved_values[local_var] = inputs[source_var]
            else:
                # 从子图内其他顶点的输出中获取变量
                source_vertex = self.get_subgraph_vertex(source_scope)
                if source_vertex and hasattr(source_vertex, "output") and source_vertex.output:
                    if source_var in source_vertex.output:
                        resolved_values[local_var] = source_vertex.output[source_var]

        # 合并输入和解析的变量
        final_inputs = {**inputs, **resolved_values}

        return final_inputs

    def resolve_dependencies(
        self, vertex: Vertex[T], inputs: Dict[str, Any] = None, context: WorkflowContext[T] = None
    ) -> Dict[str, Any]:
        """解析顶点的依赖关系，包括外部输入和子图内部变量"""
        resolved_values = {}

        # 获取顶点的变量定义
        vertex_variables = getattr(vertex, "variables", []) or []

        for variable in vertex_variables:
            source_scope = variable[SOURCE_SCOPE]
            source_var = variable[SOURCE_VAR]
            local_var = variable[LOCAL_VAR]

            source_value = None

            # 首先检查是否是外部输入（通过VertexGroup传递）
            if source_scope in ["source", None]:
                if inputs and source_var in inputs:
                    source_value = inputs[source_var]
                logging.info(f"Source value for {local_var} is {source_value}, {inputs}")

            # 如果外部输入中没有找到，尝试从子图内部获取
            if source_value is None:
                source_vertex = self.get_subgraph_vertex(source_scope)
                if source_vertex and hasattr(source_vertex, "output") and source_vertex.output:
                    if isinstance(source_vertex.output, dict) and source_var in source_vertex.output:
                        source_value = source_vertex.output[source_var]
                    elif source_var is None:
                        source_value = source_vertex.output
                elif source_vertex is None:
                    # 如果在子图中找不到source_vertex，记录错误但继续尝试从全局获取
                    logging.warning(f"Source vertex '{source_var}' in '{source_scope}' to {local_var} not found in subgraph {self.id}")

                # 如果子图中没有找到，再从全局workflow中获取
                if source_value is None and hasattr(self, "workflow") and self.workflow:
                    try:
                        global_vertex = self.workflow.get_vertice_by_id(source_scope)
                        if global_vertex and hasattr(global_vertex, "output") and global_vertex.output:
                            if isinstance(global_vertex.output, dict) and source_var in global_vertex.output:
                                source_value = global_vertex.output[source_var]
                            elif source_var is None:
                                source_value = global_vertex.output
                    except:
                        pass

                    # 如果还是没有找到，尝试直接从context的输出中获取
                    if source_value is None and context:
                        try:
                            global_output = context.get_output(source_scope)
                            if global_output:
                                if isinstance(global_output, dict) and source_var in global_output:
                                    source_value = global_output[source_var]
                                elif source_var is None:
                                    source_value = global_output
                        except:
                            pass

            if source_value is not None:
                resolved_values[local_var] = source_value

        # 合并输入和解析的变量
        final_inputs = {**(inputs or {}), **resolved_values}

        return final_inputs

    def execute_subgraph(self, inputs: Dict[str, Any] = None, context: WorkflowContext[T] = None):
        """执行子图"""
        logging.info(f"Starting execution of VertexGroup {self.id}")

        try:
            # 设置子图上下文
            self.subgraph_context = SubgraphContext(context)
            # 设置当前context供子图vertex使用
            self._current_context = context

            # 处理外部输入，将VertexGroup的variables中定义的外部输入传递给子图
            external_inputs = {}
            for var_def in self.variables:
                source_scope = var_def.get(SOURCE_SCOPE)
                source_var = var_def.get(SOURCE_VAR)
                local_var = var_def.get(LOCAL_VAR)
                # 如果source_scope不在子图中，说明是外部输入
                if source_scope not in self.subgraph_vertices:
                    value = None
                    if context:
                        # 从context中获取外部顶点的输出
                        external_output = context.get_output(source_scope)
                        if external_output and isinstance(external_output, dict) and source_var in external_output:
                            value = external_output[source_var]
                        elif external_output and source_var is None:
                            value = external_output
                    # 支持变量名映射：将外部变量赋值到local_var
                    if value is not None:
                        external_inputs[local_var] = value

            # 合并外部输入和原始输入
            all_inputs = {**(inputs or {}), **external_inputs}

            # 获取拓扑排序
            execution_order = self.topological_sort_subgraph()
            logging.info(f"Subgraph execution order: {[v.id for v in execution_order]}")

            # 按拓扑顺序执行顶点
            for vertex in execution_order:
                logging.info(f"Executing subgraph vertex: {vertex.id}")

                try:
                    # 解析顶点的依赖关系
                    vertex_inputs = self.resolve_dependencies(vertex, all_inputs, context)

                    # 执行顶点
                    vertex.execute(inputs=vertex_inputs, context=context)

                    # 存储输出到子图上下文
                    if vertex.output is not None:
                        self.subgraph_context.store_internal_output(vertex.id, vertex.output)

                    # 标记为已执行
                    vertex.is_executed = True

                    logging.info(f"Subgraph vertex {vertex.id} executed successfully")

                except Exception as e:
                    logging.error(f"Error executing subgraph vertex {vertex.id}: {e}")
                    traceback.print_exc()
                    raise e

            # 处理暴露的输出
            self._process_exposed_outputs()

            # 构建最终输出 - 直接返回暴露的变量
            exposed_vars = self.subgraph_context.get_exposed_variables()

            # 如果没有暴露的变量，返回执行摘要
            if not exposed_vars:
                result = {
                    "execution_summary": {
                        "executed_vertices": [v.id for v in execution_order],
                        "total_vertices": len(self.subgraph_vertices),
                        "success": True,
                    }
                }
            else:
                # 返回暴露的变量作为主要输出
                result = exposed_vars.copy()

            logging.info(f"VertexGroup {self.id} execution completed successfully")
            return result

        except Exception as e:
            logging.error(f"Error executing VertexGroup {self.id}: {e}")
            traceback.print_exc()

            # 重新抛出异常，让上层处理
            raise e

    def _process_exposed_outputs(self):
        """处理暴露给外部的输出"""
        for var_def in self.variables:
            source_scope = var_def.get(SOURCE_SCOPE)
            source_var = var_def.get(SOURCE_VAR)
            local_var = var_def.get(LOCAL_VAR, source_var)

            if source_scope and source_scope in self.subgraph_vertices:
                self.subgraph_context.expose_variable(source_scope, source_var, local_var)

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        """执行VertexGroup"""
        if self._task and callable(self._task):
            # 获取依赖顶点的输出
            dependencies_outputs = {}
            if context:
                dependencies_outputs = {dep_id: context.get_output(dep_id) for dep_id in self._dependencies}

            all_inputs = {**dependencies_outputs, **(inputs or {})}

            try:
                self.output = self._task(inputs=all_inputs, context=context)
                logging.info(f"VertexGroup {self.id} executed with output: {self.output}")
            except Exception as e:
                logging.error(f"Error executing VertexGroup {self.id}: {e}")
                traceback.print_exc()
                raise e
        else:
            # 执行子图
            try:
                self.execute_subgraph(inputs, context)

                # 处理暴露输出
                exposed_outputs = {}
                for var_def in self.variables:
                    source_vertex_id = var_def[SOURCE_SCOPE]
                    source_var = var_def[SOURCE_VAR]
                    local_var = var_def[LOCAL_VAR]

                    source_vertex = self.get_subgraph_vertex(source_vertex_id)
                    if source_vertex and hasattr(source_vertex, "output") and source_vertex.output:
                        if source_var in source_vertex.output:
                            exposed_outputs[local_var] = source_vertex.output[source_var]
                        else:
                            logging.warning(f"Variable '{source_var}' not found in vertex '{source_vertex_id}' output")
                    else:
                        logging.warning(f"Vertex '{source_vertex_id}' not found or has no output")

                self.output = exposed_outputs
                logging.info(f"VertexGroup {self.id} executed subgraph with exposed outputs: {self.output}")

            except Exception as e:
                logging.error(f"Error executing VertexGroup {self.id} subgraph: {e}")
                traceback.print_exc()
                raise e

    def get_subgraph_vertex(self, vertex_id: str) -> Optional[Vertex[T]]:
        """获取子图中的顶点"""
        return self.subgraph_vertices.get(vertex_id)

    def get_subgraph_vertices(self) -> Dict[str, Vertex[T]]:
        """获取所有子图顶点"""
        return self.subgraph_vertices.copy()

    def get_subgraph_edges(self) -> Set[Edge[T]]:
        """获取所有子图边"""
        return self.subgraph_edges.copy()

    def add_exposed_output(self, vertex_id: str, variable: str = None, exposed_as: str = None):
        """添加暴露输出配置"""
        var_def = {SOURCE_SCOPE: vertex_id, SOURCE_VAR: variable, LOCAL_VAR: exposed_as or variable}
        self.variables.append(var_def)

    def __str__(self) -> str:
        return f"VertexGroup(id={self.id}, vertices={len(self.subgraph_vertices)}, edges={len(self.subgraph_edges)})"

    def __repr__(self) -> str:
        return self.__str__()
