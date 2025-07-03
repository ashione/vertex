import ast
import inspect
import traceback
from functools import partial
from types import FunctionType

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import LOCAL_VAR, SOURCE_VAR

from .vertex import (
    Any,
    Callable,
    Dict,
    List,
    T,
    Union,
    Vertex,
    WorkflowContext,
)

logging = LoggerUtil.get_logger()


class FunctionVertex(Vertex[T]):
    """通用函数顶点，有一个输入和一个输出"""

    SubTypeKey = "SubType"

    def __init__(
        self,
        id: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    ):
        subtype = None
        if params and FunctionVertex.SubTypeKey in params:
            subtype = params[FunctionVertex.SubTypeKey]
        super().__init__(
            id=id,
            name=name,
            task_type=subtype or "FUNCTION",
            task=task,
            params=params,
            variables=variables,
        )

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        if callable(self._task):
            dependencies_outputs = {dep_id: context.get_output(dep_id) for dep_id in self._dependencies}
            local_inputs = {**dependencies_outputs, **(inputs or {})}
            all_inputs = {**self.resolve_dependencies(inputs=local_inputs), **(inputs or {})}
            # 获取 task 函数的签名
            sig = inspect.signature(self._task)
            has_context = "context" in sig.parameters

            try:
                if has_context:
                    # 如果 task 函数定义了 context 参数，则传递 context
                    self.output = self._task(inputs=all_inputs, context=context)
                else:
                    logging.info(f"no context, inputs: {all_inputs}")
                    # 否则，不传递 context 参数
                    self.output = self._task(inputs=all_inputs)
                output_str = str(self.output)
                if len(output_str) > 256:
                    output_str = output_str[:250] + "..."
                logging.info(f"Function {self.id}, output {output_str} after executed.")
                return self.output
            except BaseException as e:
                logging.warning(f"Error executing vertex {self._id}: {e}")
                traceback.print_exc()
                raise e
        else:
            raise ValueError("For FUNCTION type, task should be a callable function.")


class IfCase:
    def __init__(
        self,
        conditions: List[Dict[str, Union[str, Callable[[str], bool]]]],
        logical_operator: str = "and",
        id: str = "true",
    ):
        self.id = id
        self.conditions = conditions
        self.logical_operator = logical_operator

    def __repr__(self):
        return f"IfCase id({self.id}," f"conditions={self.conditions}, " f"logical_operator={self.logical_operator}"


class IfElseVertex(FunctionVertex):
    def __init__(
        self,
        id: str,
        name: str = None,
        cases: List[IfCase] = [],
        params: Dict[str, Any] = None,
    ):
        task = self.expression
        super().__init__(
            id=id,
            name=name,
            task=task,
            params={
                **(params or {}),
                **{FunctionVertex.SubTypeKey: self.__class__.__name__},
            },
        )
        if not cases:
            raise ValueError("cases list can not be empty.")
        self.cases = cases
        self._case_validate()

    def _case_validate(self):
        for if_case in self.cases:
            # 检查逻辑运算符是否有效
            if if_case.logical_operator not in ["and", "or"]:
                raise ValueError(
                    f"Unsupported logical operator: {if_case.logical_operator}. Supported operators are 'and' and 'or'."
                )

    def evaluate_condition(self, condition: Dict[str, Union[str, Callable[[str], bool]]], inputs) -> bool:
        """
        Evaluates a single condition using the context.

        Args:
            condition (Dict[str, Union[str, Callable[[str], bool]]]): A dictionary containing the condition details.
            context (WorkflowContext): The context containing other Vertices.

        Returns:
            bool: The result of the condition evaluation.
        """
        variable_selector = condition["variable_selector"]
        value = condition["value"]
        operator = condition["operator"]
        variable_name = variable_selector[SOURCE_VAR]

        # 获取变量值
        variable_value = self.resolve_dependencies(variable_selector=variable_selector, inputs=inputs).get(
            variable_name
        )

        # 检查变量是否存在
        if variable_value is None:
            raise ValueError(f"Variable '{variable_name}' not found in context.")

        # 字符串操作映射
        operators = {
            "==": partial(str.__eq__, variable_value),
            "is": partial(str.__eq__, variable_value),
            "!=": partial(str.__ne__, variable_value),
            "contains": partial(str.__contains__, variable_value),
            "not_contains": lambda v: not variable_value.__contains__(v),
            "starts_with": partial(str.startswith, variable_value),
            "start with": partial(str.startswith, variable_value),
            "ends_with": partial(str.endswith, variable_value),
            "end with": partial(str.endswith, variable_value),
            "is_empty": lambda: not variable_value,
            "is_not_empty": lambda: bool(variable_value),
        }

        # 获取操作符对应的函数
        operation = operators.get(operator)
        if not operation:
            raise ValueError(f"Unsupported operator: {operator}")

        # 执行操作
        return operation(value)

    def evaluate_conditions(self, if_case, inputs) -> bool:
        """
        Evaluates all conditions using the specified logical operator.

        Args:
            context (WorkflowContext): The context containing other Vertices.

        Returns:
            bool: The combined result of all conditions.
        """
        results = [self.evaluate_condition(condition, inputs) for condition in if_case.conditions]

        if if_case.logical_operator == "and":
            return all(results)
        elif if_case.logical_operator == "or":
            return any(results)
        else:
            # 这里理论上不会触发，因为我们已经在构造函数中做了检查
            raise ValueError(f"Unsupported logical operator: {if_case.logical_operator}")

    def expression(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        """
        Executes the logic of the IfElseVertex based on the given inputs and context.

        Args:
            inputs (Dict[str, Any]): Input variables for the Vertex.
            context (WorkflowContext): The context containing other Vertices.
        """
        for if_case in self.cases:
            condition_result = self.evaluate_conditions(if_case, inputs)
            if condition_result:
                return {if_case.id: True}
        return {"false": True}

    def iftrue(self, case_id: str = "true"):
        return self.output[case_id] if case_id in self.output else False


class CodeVertex(FunctionVertex):
    CodeKey = "code"

    def __init__(
        self,
        id: str,
        name: str = None,
        params: Dict[str, Any] = None,
    ):
        code = params[self.CodeKey]
        assert code
        task = self.code_execute
        super().__init__(
            id=id,
            name=name,
            task=task,
            params={
                **(params or {}),
                **{FunctionVertex.SubTypeKey: self.__class__.__name__},
            },
        )
        self._only_main_func = True
        if "only_main" in params:
            self._only_main_func = params["only_main"]
        self._func = self._compile_code(code)

    def _compile_code(self, code: str) -> FunctionType:
        """编译用户提供的代码，并返回一个可调用的函数"""
        try:
            # 安全检查：仅允许函数定义，并且只能有一个名为 main 的函数
            tree = ast.parse(code)
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            if self._only_main_func:
                if len(functions) != 1 or functions[0].name != "main":
                    raise ValueError("Only one function named 'main' is allowed.")
            else:
                logging.warning("any expression will be executed.")
            from vertex_flow.workflow.utils import safe_globals

            # 编译代码
            compiled_func = compile(tree, filename="", mode="exec")
            local_vars = {}

            # 执行函数定义
            exec(compiled_func, safe_globals, local_vars)

            # 获取函数
            func_name = "main"
            if func_name not in local_vars:
                raise ValueError("Function definition 'main' not found.")
            func = local_vars[func_name]

            return func
        except Exception as e:
            logging.error(f"Error compiling code: {e}")
            raise

    def code_execute(self, inputs: Dict[str, Any]):
        """执行编译后的函数，并返回结果"""
        try:
            # 限制执行环境
            safe_locals = self.resolve_dependencies(inputs=inputs)

            # 设置输入参数
            # for key, value in inputs.items():
            #     safe_locals[key] = value
            print(f"safe_locals : {safe_locals}")
            logging.info(f"safe_locals : {safe_locals}")
            # 执行函数
            result = self._func(**safe_locals)
            logging.info(f"code executed result : {result}")
            return result
        except Exception as e:
            logging.error(f"Error executing code: {e}")
            raise
