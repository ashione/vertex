from typing import Any, Dict, Generic, Optional, TypeVar, cast

T = TypeVar("T")  # 泛型类型变量


class WorkflowContext(Generic[T]):
    """工作流上下文，用于存储环境参数和输出数据"""

    def __init__(
        self,
        env_parameters: Optional[Dict[str, Any]] = None,
        user_parameters: Optional[Dict[str, Any]] = None,
    ):
        self.env_parameters = env_parameters or {}
        self.user_parameters = user_parameters or {}
        self.outputs = {}  # 新增属性来存储顶点的输出

    def get_env_parameter(self, key: str, default: T = None) -> T:
        return cast(T, self.env_parameters.get(key, default))

    def get_env_parameters(self) -> Dict[str, Any]:
        return self.env_parameters

    def get_user_parameter(self, key: str, default: T = None) -> T:
        return cast(T, self.user_parameters.get(key, default))

    def get_user_parameters(self) -> Dict[str, Any]:
        return self.user_parameters

    def store_output(self, vertex_id: str, output_data: T):
        """存储顶点的输出数据"""
        self.outputs[vertex_id] = output_data

    def get_output(self, vertex_id: str) -> T:
        """从上下文中获取指定顶点的输出数据"""
        return cast(T, self.outputs.get(vertex_id, None))

    def get_outputs(self) -> Dict[str, Any]:
        """从上下文中获取所有顶点的输出数据"""
        return self.outputs


class SubgraphContext(Generic[T]):
    """子图上下文，用于管理子图内部的变量和输出，实现透明代理机制"""

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

    # 核心透明代理方法 - 只保留真正需要的
    def store_output(self, vertex_id: str, output_data: T):
        """透明代理：存储输出，优先存储到内部输出"""
        # 优先存储到子图内部输出
        self.store_internal_output(vertex_id, output_data)
        # 同时存储到父上下文（如果需要的话）
        if self.parent_context:
            self.parent_context.store_output(vertex_id, output_data)

    def get_output(self, vertex_id: str) -> T:
        """透明代理：优先查找自身，找不到时代理到父上下文"""
        # 首先查找子图内部输出
        internal_output = self.get_internal_output(vertex_id)
        if internal_output is not None:
            return cast(T, internal_output)
        
        # 如果子图中没有找到，代理到父上下文
        if self.parent_context:
            return self.parent_context.get_output(vertex_id)
        
        return cast(T, None)

    def __str__(self) -> str:
        return f"SubgraphContext(internal_outputs={len(self.internal_outputs)}, exposed_variables={len(self.exposed_variables)}, has_parent={self.parent_context is not None})"

    def __repr__(self) -> str:
        return self.__str__()
