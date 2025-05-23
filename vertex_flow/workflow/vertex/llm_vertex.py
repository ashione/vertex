from .vertex import (
    Vertex,
    T,
    WorkflowContext,
    Dict,
    Callable,
    Any,
)
from vertex_flow.workflow.chat import ChatModel
import inspect
import json
import traceback

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.utils import (
    env_str,
    var_str,
    compatiable_env_str,
)

logging = LoggerUtil.get_logger()


class LLMVertex(Vertex[T]):
    """语言模型顶点，有一个输入和一个输出"""

    def __init__(
        self,
        id: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
        tools: list = None,  # 新增参数
    ):
        # """如果传入task则以task为执行单元，否则执行当前llm的chat方法."""
        self.model: ChatModel = None
        self.messages = []
        self.system_message = None
        self.user_messages = []
        self.preprocess = None
        self.postprocess = None
        self.tools = tools or []  # 保存可用的function tools
        if task is None:
            logging.info("Use llm chat in task executing.")
            self.model = params["model"]
            self.system_message = params["system"] if "system" in params else ""
            self.user_messages = params["user"] if "user" in params else []
            task = self.chat
            self.preprocess = params["preprocess"] if "preprocess" in params else None
            self.postprocess = (
                params["postprocess"] if "postprocess" in params else None
            )
        super().__init__(id=id, name=name, task_type="LLM", task=task, params=params)

    def __get_state__(self):
        data = super().__get_state__()
        # 不序列化model。
        if "params" in data and "model" in data["params"]:
            del data["params"]["model"]
        data.update(
            {
                "user_messages": self.user_messages,
                "system_message": self.system_message,
                "model": self.model.__get_state__(),
            }
        )
        return data

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        if callable(self._task):
            dependencies_outputs = {
                dep_id: context.get_output(dep_id) for dep_id in self._dependencies
            }
            all_inputs = {**dependencies_outputs, **(inputs or {})}

            # 获取 task 函数的签名
            sig = inspect.signature(self._task)
            has_context = "context" in sig.parameters
            # replace all variables
            self.messages_redirect(all_inputs, context=context)
            try:
                if has_context or self._task == self.chat:
                    # 如果 task 函数定义了 context 参数，则传递 context
                    self.output = self._task(inputs=all_inputs, context=context)
                else:
                    # 否则，不传递 context 参数
                    self.output = self._task(inputs=all_inputs)
            except BaseException as e:
                print(f"Error executing vertex {self._id}: {e}")
                traceback.print_exc()
                raise e
            logging.info(f"LLM {self.id} finished, output : {self.output}.")
        else:
            raise ValueError("For LLM type, task should be a callable function.")

    def messages_redirect(self, inputs, context: WorkflowContext[T]):
        self.messages.append(
            {"role": "system", "content": self.system_message},
        )

        if self.preprocess is not None:
            self.user_messages = self.preprocess(self.user_messages, inputs, context)

        for user_message in self.user_messages:
            self.messages.append({"role": "user", "content": user_message})

        # replace by env parameters and user paramters.
        for message in self.messages:
            if "content" not in message or message["content"] is None:
                continue

            for key, value in context.get_env_parameters().items():
                value = value if isinstance(value, str) else str(value)
                message["content"] = message["content"].replace(env_str(key), value)
                # For dify workflow compatiable env.
                message["content"] = message["content"].replace(
                    compatiable_env_str(key), value
                )

            for key, value in context.get_user_parameters().items():
                value = value if isinstance(value, str) else str(value)
                message["content"] = message["content"].replace(var_str(key), value)

            message["content"] = self._replace_placeholders(message["content"])

        logging.info(f"{self}, {self.id} chat context messages {self.messages}")

    def chat(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None):
        finish_reason = None
        while finish_reason is None or finish_reason == "tool_calls":
            choice = self.model.chat(self.messages)
            finish_reason = choice.finish_reason
            if finish_reason == "tool_calls":
                self.messages.append(choice.message)
                for tool_call in choice.message.tool_calls:
                    tool_call_name = tool_call.function.name
                    tool_call_arguments = json.loads(tool_call.function.arguments)
                    # 新增：查找并执行对应的FunctionVertex
                    tool_result = None
                    for tool in self.tools:
                        if tool.name == tool_call_name:
                            tool_result = tool.execute(tool_call_arguments, context)
                            break
                    if tool_result is None:
                        tool_result = f"Error: unable to find tool by name '{tool_call_name}'"
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call_name,
                            "content": json.dumps(tool_result),
                        }
                    )
        result = (
            choice.message.content
            if self.postprocess is None
            else self.postprocess(choice.message.content, input, context)
        )
        logging.debug(f"chat bot response : {result}")

        return result
