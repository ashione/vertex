import inspect
import re
import time
import traceback
import weakref
from typing import Any, Callable, Dict, Generic, List, Set, Type, TypeVar, Union

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import (
    LOCAL_VAR,
    SOURCE_SCOPE,
    SOURCE_VAR,
)
from vertex_flow.workflow.edge import (
    Edge,
    EdgeType,
)
from vertex_flow.workflow.utils import (
    get_task_module_and_function_name,
    is_lambda,
    is_method_of_class,
)

logging = LoggerUtil.get_logger()

T = TypeVar("T")  # 泛型类型变量


class VertexAroundMeta(type):
    def __new__(cls, name, bases, dct):
        # 获取execute方法
        execute = dct.get("execute", None)
        if execute is not None:
            # 如果存在execute方法，则使用装饰器包装它
            dct["execute"] = cls._wrap_execute_with_timer(execute)
        return super().__new__(cls, name, bases, dct)

    @staticmethod
    def _wrap_execute_with_timer(func):
        def wrapper(self, *args, **kwargs):
            self.success = True  # 默认认为执行成功
            self.cost_time = None
            self.error_message = None
            self.traceback = None

            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                self.on_finished()
            except Exception as e:
                self.success = False
                self.error_message = str(e)
                self.traceback = traceback.format_exc()

                self.on_failed()
                raise e from None  # 原样抛出异常
            finally:
                end_time = time.time()
                self.cost_time = end_time - start_time

            return result

        return wrapper


class Workflow(Generic[T]):
    pass


class WorkflowContext(Generic[T]):
    pass


class Vertex(Generic[T], metaclass=VertexAroundMeta):
    """基本的顶点类，可以被继承以实现具体的功能"""

    def __init__(
        self,
        id: str,
        task_type: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = [],
    ):
        self._id = id
        self._name = name or id
        self._task_type = task_type
        self._task = task
        self._params = params or {}
        self._output = None
        self._in_degree = 0
        self._out_degree = 0  # 新增属性记录出度
        self._dependencies = set()
        self._is_executed = False
        self._output_type = None  # 输出类型
        self._input_type = None  # 输入类型
        self._workflow_ref = None
        self.variables = variables if variables else []

        # 如果提供了 task，则尝试推导 input_type 和 output_type
        if task is not None:
            self._validate_task_signature(task)
            signature = inspect.signature(task)
            if len(signature.parameters) > 0:
                first_param = next(iter(signature.parameters.values()))
                self._input_type = first_param.annotation if first_param.annotation != inspect.Parameter.empty else None

            # 假设返回值类型为任务函数的返回类型注解
            self._output_type = (
                signature.return_annotation if signature.return_annotation != inspect.Signature.empty else None
            )

    def __get_state__(self):
        data = {
            "id": self._id,
            "task_type": self.task_type,
            "name": self.name,
            "params": self.params,
            "task": None,
            "dependencies": self.dependencies,
            "variables": self.variables,
            "class_module": self.__class__.__module__,  # 添加类的模块路径
            "class_name": self.__class__.__name__,  # 添加类名
        }
        if not hasattr(self, "task") or self.task is None or not callable(self.task):
            return data
        if is_method_of_class(self.task, self.__class__) or is_lambda(self.task):
            logging.warning(f"Task {self.task} is not a method of class {self.__class__}, or is a lambda function")
            return data
        task_dict = get_task_module_and_function_name(self.task)
        if task_dict:
            data["task"] = task_dict
        return data

    def __setstate__(self, state):
        # 恢复状态，并重新创建不能被序列化的属性
        self.__dict__.update(state)

    @property
    def workflow(self):
        return self._workflow_ref() if self._workflow_ref else None

    @workflow.setter
    def workflow(self, workflow):
        self._workflow_ref = weakref.ref(workflow)

    def _validate_task_signature(self, task: Callable):
        if isinstance(task, type(lambda: None)):  # 检查是否为 lambda 函数
            # 对于 lambda 函数，检查是否有 'inputs' 参数，并可选检查 'context'
            sig = inspect.signature(task)
            params = list(sig.parameters.keys())
            if "inputs" not in params:
                raise ValueError("Lambda function must accept 'inputs' parameter.")

    def add_variable(self, source_scope: str, source_var: str, local_var: str):
        """
        Adds a variable definition to the Vertex's variables list.

        Args:
            source_scope (str): The scope where the variable originates from.
            source_var (str): The name of the source variable.
            local_var (str): The local name of the variable within this Vertex.
        """
        self.variables.append(
            {
                SOURCE_SCOPE: source_scope,
                SOURCE_VAR: source_var,
                LOCAL_VAR: local_var,
            }
        )

    def add_variables(self, variables: List[Dict[str, str]]):
        """
        Adds multiple variable definitions to the Vertex's variables list.

        Args:
            variables (List[Dict[str, str]]): A list of dictionaries containing variable definitions.

        Raises:
            ValueError: If one of the dictionaries does not contain all required keys.
        """
        required_keys = {SOURCE_SCOPE, SOURCE_VAR, LOCAL_VAR}
        for var_def in variables:
            if not required_keys.issubset(var_def.keys()):
                missing_keys = required_keys - var_def.keys()
                raise ValueError(f"Variable definition missing required keys: {missing_keys}")
            self.add_variable(**var_def)

    def resolve_dependencies(self, variable_selector: Dict[str, str] = None, inputs: Dict[str, Any] = None):
        """
        Resolves dependencies for the Vertex based on the provided context.

        Args:
            variables: high prioprity variable selector
            inputs: for testing only.
        """

        def get_variable_value(var_def):
            source_value = None
            if SOURCE_SCOPE not in var_def or var_def[SOURCE_SCOPE] is None or len(var_def[SOURCE_SCOPE]) == 0:
                if inputs and var_def[SOURCE_VAR] in inputs:
                    source_value = inputs[var_def[SOURCE_VAR]]
                else:
                    raise ValueError(
                        f"No local inputs in {self.task_type}-{self.id} to search non-scope variable {var_def}"
                    )
            else:
                if self.workflow is None:
                    raise ValueError(
                        f"Vertex {self.id} has no workflow reference. Make sure the vertex is added to a workflow before resolving dependencies."
                    )
                source_vertex = self.workflow.get_vertice_by_id(var_def[SOURCE_SCOPE])
                if source_vertex is None:
                    raise ValueError(f"Source Vertex {var_def[SOURCE_SCOPE]} not found.")

                # 如果源顶点的输出不是字典类型，并且没有指定源变量，则直接返回源顶点的输出。
                if not isinstance(source_vertex.output, dict) and var_def[SOURCE_VAR] is None:
                    return source_vertex.output

                if not source_vertex.output or var_def[SOURCE_VAR] not in source_vertex.output:
                    raise ValueError(
                        f"Source Vertex {source_vertex.task_type}-{source_vertex.id} no {var_def[SOURCE_VAR]} found."
                    )
                source_value = source_vertex.output[var_def[SOURCE_VAR]]
            return source_value

        resolved_values = {}
        if variable_selector:
            logging.info(f"Only fetch variable from specific selector {variable_selector}")
            source_value = get_variable_value(variable_selector)
            resolved_values[variable_selector.get(LOCAL_VAR) or variable_selector[SOURCE_VAR]] = source_value
            return resolved_values

        for var_def in self.variables:
            source_value = get_variable_value(var_def=var_def)
            resolved_values[var_def.get(LOCAL_VAR) or var_def[SOURCE_VAR]] = source_value
        return resolved_values

    @property
    def id(self) -> str:
        return self._id

    @property
    def task_type(self) -> str:
        return self._task_type

    @property
    def task(self) -> Callable[[Dict[str, Any], WorkflowContext[T]], T]:
        return self._task

    @task.setter
    def task(self, task: Callable[[Dict[str, Any], WorkflowContext[T]], T]):
        self._task = task

    @property
    def params(self) -> Dict[str, Any]:
        return self._params

    @params.setter
    def params(self, params: Dict[str, Any]):
        self._params = params

    @property
    def output(self) -> T:
        return self._output

    @property
    def name(self) -> str:
        return self._name

    @output.setter
    def output(self, output: T):
        self._output = output

    @property
    def input_type(self) -> Type[T]:
        return self._input_type

    @input_type.setter
    def input_type(self, input_type: Type[T]):
        self._input_type = input_type

    @property
    def output_type(self) -> Type[T]:
        return self._output_type

    @output_type.setter
    def output_type(self, output_type: Type[T]):
        self._output_type = output_type

    @property
    def in_degree(self) -> int:
        return self._in_degree

    @in_degree.setter
    def in_degree(self, in_degree: int):
        self._in_degree = in_degree

    @property
    def out_degree(self) -> int:
        return self._out_degree

    @out_degree.setter
    def out_degree(self, out_degree: int):
        self._out_degree = out_degree

    @property
    def dependencies(self) -> Set[str]:
        return self._dependencies

    @dependencies.setter
    def dependencies(self, dependencies: Set[str]):
        self._dependencies = dependencies

    @property
    def is_executed(self) -> bool:
        return self._is_executed

    @is_executed.setter
    def is_executed(self, executed: bool):
        self._is_executed = executed

    def to(self, next_vertex: "Vertex[T]", edge_type: EdgeType = Edge.ALWAYS) -> "Vertex[T]":
        if not isinstance(next_vertex, Vertex):
            raise ValueError("next_vertex must be an instance of Vertex")

        # 添加边
        edge = Edge(self, next_vertex, edge_type)
        self.workflow.add_edge(edge)

        return next_vertex

    def __or__(self, other: "Vertex[T]", edge_type: EdgeType = Edge.ALWAYS) -> "Vertex[T]":
        if not isinstance(other, Vertex):
            raise ValueError("Other must be an instance of Vertex")

        return self.to(other)

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        raise NotImplementedError("Subclasses should implement this method.")

    def _replace_placeholders(self, text):
        """替换文本中的占位符"""
        logging.debug(f"Replace in {self.id}")

        # 定义支持的占位符格式
        patterns = [
            (r"\{\{\#([\w-]+)\.(.*?)#\}\}", "pattern1"),  # {{#vertex_id.var_name#}}
            (r"\{\{([\w-]+)\.([\w-]+)\}\}", "pattern2"),  # {{vertex_id.var_name}}
            (r"\{\{([\w-]+)\}\}", "pattern3"),  # {{vertex_id}}
        ]

        for pattern, pattern_name in patterns:
            text = self._process_pattern(text, pattern, pattern_name)

        return text

    def _process_pattern(self, text, pattern, pattern_name):
        """处理特定模式的占位符"""
        matches = re.finditer(pattern, text)
        for match in matches:
            vertex_id = match.group(1)
            # pattern3 ({{vertex_id}}) 没有var_name，其他模式有
            var_name = match.group(2) if len(match.groups()) > 1 else None
            logging.debug(f"match {pattern_name} {vertex_id}, {var_name}, {match.group(0)}")

            # 使用resolve_dependencies方法获取替换值
            replacement_value = self._get_replacement_value_via_dependencies(vertex_id, var_name)
            if replacement_value is not None:
                text = text.replace(match.group(0), str(replacement_value))
                logging.debug(f"replaced text : {text}")

        return text

    def _find_vertex_by_id(self, vertex_id):
        """根据ID查找顶点"""
        for vertex in self.workflow.vertices.values():
            if vertex.id == vertex_id:
                logging.debug(f"matched vertex {vertex.id} : {vertex.output}")
                return vertex

        logging.warning(f"{vertex_id} not found.")
        return None

    def _get_replacement_value_via_dependencies(self, vertex_id, var_name):
        """通过resolve_dependencies方法获取替换值"""
        try:
            # 构造variable_selector
            variable_selector = {
                SOURCE_SCOPE: vertex_id,
                SOURCE_VAR: var_name,
                LOCAL_VAR: vertex_id if var_name is None else var_name,
            }

            # 使用resolve_dependencies方法获取变量值
            resolved_values = self.resolve_dependencies(variable_selector=variable_selector)

            # 获取解析后的值
            local_var_name = var_name if var_name else vertex_id
            if local_var_name in resolved_values:
                return resolved_values[local_var_name]
            else:
                logging.warning(f"Variable {var_name} not found in vertex {vertex_id} resolved values")
                return None

        except Exception as e:
            import traceback

            logging.warning(f"Failed to resolve variable {var_name} from vertex {vertex_id}: {e}")
            logging.warning(f"Stack trace: {traceback.format_exc()}")
            return None

    def _get_replacement_value(self, vertex, var_name, vertex_id):
        """获取替换值（保留原方法以兼容性）"""
        if var_name in vertex.output:
            return str(vertex.output[var_name])
        else:
            logging.warning(f"Variable {var_name} not found in vertex {vertex_id} output")
            return None

    def __str__(self) -> str:
        """
        返回顶点的字符串表示形式。
        """
        return (
            f"Vertex(id={self._id}, task_type={self._task_type}, "
            f"params={self._params}, in_degree={self._in_degree}, out_degree={self._out_degree}, "
            f"variables={self.variables}, "
            f"input_type={self._input_type}, output_type={self._output_type})"
        )

    def on_finished(self):
        """
        在顶点成功完成任务时调用的方法。
        子类可以重写此方法以执行特定的完成逻辑。
        """
        # 在执行后触发 values 事件
        if self.workflow:
            self.workflow.emit_event("values", {"vertex_id": self.id, "output": self.output})
        pass

    def on_failed(self):
        """
        在顶点任务失败时调用的方法。
        子类可以重写此方法以执行特定的失败处理逻辑。
        """
        # 在状态变化时触发 updates 事件
        if self.workflow:
            self.workflow.emit_event("updates", {"vertex_id": self.id, "status": "failed"})
        pass

    def on_workflow_finished(self):
        """
        在整个工作流成功完成时调用的方法。
        子类可以重写此方法以执行特定的工作流完成逻辑。
        """
        pass

    def on_workflow_failed(self):
        """
        在整个工作流失败时调用的方法。
        子类可以重写此方法以执行特定的工作流失败处理逻辑。
        """
        pass


class SourceVertex(Vertex[T]):
    """数据源顶点，没有输入，只有一个输出"""

    def __init__(
        self,
        id: str,
        name: str = None,
        variables: List[Dict[str, Any]] = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
    ):
        super().__init__(
            id=id,
            name=name,
            task_type="SOURCE",
            task=task,
            params=params,
            variables=variables,
        )

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        """执行source获取数据, 如果指定输入变量则优先获取"""
        if self.variables:
            self.output = {}
            for variable_selector in self.variables:
                logging.info(f"source variable selector : {variable_selector}")
                # source节点优先从inputs中获取.
                variable_selected = self.resolve_dependencies(variable_selector=variable_selector, inputs=inputs)
                # 暂时不检查类型.
                if variable_selector["required"] and not variable_selected:
                    raise ValueError(f"No such variable {variable_selector} input, but required is true.")
                self.output.update(variable_selected)
        elif callable(self._task):
            logging.info(f"Source vertex task calling {inputs}, {self._task}.")
            try:
                self.output = self._task(inputs=inputs, context=context)
                logging.info(f"Source vertex task output {self.output}.")
            except Exception as e:
                logging.warning(f"Source running exception.", e)
                raise e
        else:
            raise ValueError("For SOURCE type, task should be a callable function.")


class SinkVertex(Vertex[T]):
    """接收数据并执行某些操作的顶点，有一个输入但没有输出"""

    def __init__(
        self,
        id: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], None] = None,
        variables: List[Dict[str, str]] = None,
        params: Dict[str, Any] = None,
    ):
        super().__init__(
            id=id,
            name=name,
            task_type="SINK",
            task=task,
            params=params,
            variables=variables,
        )

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        if self.variables:
            self.output = {}
            for variable_selector in self.variables:
                logging.info(f"sink {self.id}, variable selector : {variable_selector}")
                self.output.update(self.resolve_dependencies(variable_selector=variable_selector))
        elif callable(self._task):
            dependencies_outputs = {dep_id: context.get_output(dep_id) for dep_id in self._dependencies}
            all_inputs = {**dependencies_outputs, **(inputs or {})}
            try:
                self.output = self._task(inputs=all_inputs, context=context, **self._params)
            except BaseException as e:
                logging.info(f"execute task exception {e}.")
                traceback.print_exc()
                raise e
        else:
            raise ValueError(
                "For SINK type, task should be a callable function or no one variable selected in outputs."
            )
