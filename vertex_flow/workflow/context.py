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