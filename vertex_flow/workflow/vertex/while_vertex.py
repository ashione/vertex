import inspect
import traceback
from typing import Any, Callable, Dict, List, Union

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import SOURCE_VAR

from .function_vertex import FunctionVertex
from .vertex import T, WorkflowContext

logging = LoggerUtil.get_logger()


class WhileCondition:
    """While循环的条件定义"""

    def __init__(self, variable_selector: Dict[str, str], operator: str, value: Any, logical_operator: str = "and"):
        """
        初始化While条件

        Args:
            variable_selector: 变量选择器，包含SOURCE_SCOPE, SOURCE_VAR, LOCAL_VAR
            operator: 比较操作符 (==, !=, >, <, >=, <=, contains, etc.)
            value: 比较值
            logical_operator: 逻辑操作符 (and, or)
        """
        self.variable_selector = variable_selector
        self.operator = operator
        self.value = value
        self.logical_operator = logical_operator


class WhileVertex(FunctionVertex):
    """While循环顶点，支持条件判断和固定次数的循环控制"""

    def __init__(
        self,
        id: str,
        name: str = None,
        execute_task: Callable[[Dict[str, Any], WorkflowContext[T]], Any] = None,
        condition_task: Callable[[Dict[str, Any], WorkflowContext[T]], bool] = None,
        conditions: List[WhileCondition] = None,
        logical_operator: str = "and",
        max_iterations: int = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    ):
        """
        初始化WhileVertex

        Args:
            id: 顶点ID
            name: 顶点名称
            execute_task: 循环体执行逻辑的函数
            condition_task: 条件判断逻辑的函数（可选，与conditions二选一）
            conditions: 条件列表（可选，与condition_task二选一）
            logical_operator: 多个条件之间的逻辑操作符
            max_iterations: 最大迭代次数（可选）
            params: 参数字典
            variables: 变量列表
        """
        # 设置默认的task为while_loop方法
        task = self.while_loop

        super().__init__(
            id=id,
            name=name,
            task=task,
            params={
                **(params or {}),
                **{FunctionVertex.SubTypeKey: self.__class__.__name__},
            },
            variables=variables,
        )

        if not execute_task:
            raise ValueError("execute_task is required for WhileVertex")

        if not condition_task and not conditions:
            raise ValueError("Either condition_task or conditions must be provided")

        if condition_task and conditions:
            raise ValueError("Cannot provide both condition_task and conditions")

        self.execute_task = execute_task
        self.condition_task = condition_task
        self.conditions = conditions or []
        self.logical_operator = logical_operator
        self.max_iterations = max_iterations
        self._validate_conditions()

    def _validate_conditions(self):
        """验证条件的有效性"""
        if self.logical_operator not in ["and", "or"]:
            raise ValueError(
                f"Unsupported logical operator: {self.logical_operator}. " f"Supported operators are 'and' and 'or'."
            )

    def evaluate_condition(self, condition: WhileCondition, inputs: Dict[str, Any]) -> bool:
        """
        评估单个条件

        Args:
            condition: WhileCondition实例
            inputs: 输入数据

        Returns:
            bool: 条件评估结果
        """
        variable_selector = condition.variable_selector
        value = condition.value
        operator = condition.operator
        variable_name = variable_selector[SOURCE_VAR]

        # 获取变量值
        variable_value = self.resolve_dependencies(variable_selector=variable_selector, inputs=inputs).get(
            variable_name
        )

        # 检查变量是否存在
        if variable_value is None:
            raise ValueError(f"Variable '{variable_name}' not found in context.")

        # 操作符映射
        operators = {
            "==": lambda v: str(variable_value) == str(v),
            "is": lambda v: str(variable_value) == str(v),
            "!=": lambda v: str(variable_value) != str(v),
            ">": lambda v: float(variable_value) > float(v),
            "<": lambda v: float(variable_value) < float(v),
            ">=": lambda v: float(variable_value) >= float(v),
            "<=": lambda v: float(variable_value) <= float(v),
            "contains": lambda v: str(v) in str(variable_value),
            "not_contains": lambda v: str(v) not in str(variable_value),
            "starts_with": lambda v: str(variable_value).startswith(str(v)),
            "ends_with": lambda v: str(variable_value).endswith(str(v)),
            "is_empty": lambda v: not variable_value,
            "is_not_empty": lambda v: bool(variable_value),
        }

        # 获取操作符对应的函数
        operation = operators.get(operator)
        if not operation:
            raise ValueError(f"Unsupported operator: {operator}")

        # 执行操作
        try:
            return operation(value)
        except (ValueError, TypeError) as e:
            logging.warning(f"Error evaluating condition: {e}")
            return False

    def evaluate_conditions(self, inputs: Dict[str, Any]) -> bool:
        """
        评估所有条件

        Args:
            inputs: 输入数据

        Returns:
            bool: 组合条件的评估结果
        """
        if not self.conditions:
            return True

        results = [self.evaluate_condition(condition, inputs) for condition in self.conditions]

        if self.logical_operator == "and":
            return all(results)
        elif self.logical_operator == "or":
            return any(results)
        else:
            raise ValueError(f"Unsupported logical operator: {self.logical_operator}")

    def should_continue(self, inputs: Dict[str, Any], context: WorkflowContext[T]) -> bool:
        """
        判断是否应该继续循环

        Args:
            inputs: 输入数据
            context: 工作流上下文

        Returns:
            bool: 是否继续循环
        """
        if self.condition_task:
            # 使用自定义条件函数
            sig = inspect.signature(self.condition_task)
            has_context = "context" in sig.parameters

            try:
                if has_context:
                    return self.condition_task(inputs=inputs, context=context)
                else:
                    return self.condition_task(inputs=inputs)
            except Exception as e:
                logging.warning(f"Error evaluating condition_task: {e}")
                return False
        else:
            # 使用条件列表
            return self.evaluate_conditions(inputs)

    def while_loop(self, inputs: Dict[str, Any] = None, context: WorkflowContext[T] = None):
        """
        While循环的主要逻辑

        Args:
            inputs: 输入数据
            context: 工作流上下文

        Returns:
            循环执行的结果
        """
        iteration_count = 0
        results = []
        current_inputs = inputs.copy() if inputs else {}

        logging.info(f"Starting while loop in vertex {self.id}")

        try:
            while True:
                # 检查最大迭代次数
                if self.max_iterations is not None and iteration_count >= self.max_iterations:
                    logging.info(f"Reached max iterations ({self.max_iterations}) in vertex {self.id}")
                    break

                # 检查循环条件
                if not self.should_continue(current_inputs, context):
                    logging.info(f"Loop condition failed in vertex {self.id} at iteration {iteration_count}")
                    break

                # 执行循环体
                sig = inspect.signature(self.execute_task)
                has_context = "context" in sig.parameters

                try:
                    if has_context:
                        result = self.execute_task(inputs=current_inputs, context=context)
                    else:
                        result = self.execute_task(inputs=current_inputs)

                    results.append(result)

                    # 更新输入数据（如果结果是字典，则合并到输入中）
                    if isinstance(result, dict):
                        current_inputs.update(result)

                    iteration_count += 1
                    logging.debug(f"Completed iteration {iteration_count} in vertex {self.id}")

                except Exception as e:
                    logging.error(f"Error in execute_task at iteration {iteration_count}: {e}")
                    traceback.print_exc()
                    break

        except Exception as e:
            logging.error(f"Error in while loop: {e}")
            traceback.print_exc()
            raise e

        logging.info(f"While loop completed in vertex {self.id} after {iteration_count} iterations")

        return {"results": results, "iteration_count": iteration_count, "final_inputs": current_inputs}
