import inspect
import json
import traceback
import asyncio

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.constants import (
    ENABLE_STREAM,
    MODEL,
    POSTPROCESS,
    PREPROCESS,
    SYSTEM,
    USER,
)
from vertex_flow.workflow.utils import (
    compatiable_env_str,
    env_str,
    var_str,
)

from .vertex import (
    Any,
    Callable,
    Dict,
    T,
    Vertex,
    WorkflowContext,
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
        self.enable_stream = params.get(ENABLE_STREAM, False) if params else False  # 使用常量 ENABLE_STREAM

        if task is None:
            logging.info("Use llm chat in task executing.")
            self.model = params[MODEL]  # 使用常量 MODEL
            self.system_message = params[SYSTEM] if SYSTEM in params else ""  # 使用常量 SYSTEM
            self.user_messages = params[USER] if USER in params else []  # 使用常量 USER
            task = self.chat
            self.preprocess = params[PREPROCESS] if PREPROCESS in params else None  # 使用常量 PREPROCESS
            self.postprocess = params[POSTPROCESS] if POSTPROCESS in params else None  # 使用常量 POSTPROCESS
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
            dependencies_outputs = {dep_id: context.get_output(dep_id) for dep_id in self._dependencies}
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

        logging.info(f"{self.id} chat context inputs {inputs}")

        self.messages.append(
            {"role": "system", "content": self.system_message},
        )

        if self.preprocess is not None:
            self.user_messages = self.preprocess(self.user_messages, inputs, context)

        for user_message in self.user_messages:
            self.messages.append({"role": "user", "content": user_message})

        # replace by env parameters, user parameters and inputs.
        for message in self.messages:
            if "content" not in message or message["content"] is None:
                continue

            for key, value in context.get_env_parameters().items():
                value = value if isinstance(value, str) else str(value)
                message["content"] = message["content"].replace(env_str(key), value)
                # For dify workflow compatiable env.
                message["content"] = message["content"].replace(compatiable_env_str(key), value)

            for key, value in context.get_user_parameters().items():
                value = value if isinstance(value, str) else str(value)
                message["content"] = message["content"].replace(var_str(key), value)

            # replace by inputs parameters
            if inputs:
                for key, value in inputs.items():
                    value = value if isinstance(value, str) else str(value)
                    # Support {{inputs.key}} format
                    input_placeholder = "{{" + key + "}}"
                    message["content"] = message["content"].replace(input_placeholder, value)

            message["content"] = self._replace_placeholders(message["content"])

        logging.info(f"{self}, {self.id} chat context messages {self.messages}")

    def chat(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None):
        finish_reason = None
        if self.enable_stream and hasattr(self.model, "chat_stream"):
            return self._chat_stream(inputs, context)
        llm_tools = self._build_llm_tools()
        option = self._build_llm_option()
        while finish_reason is None or finish_reason == "tool_calls":
            choice = self.model.chat(self.messages, option=option, tools=llm_tools)
            finish_reason = choice.finish_reason
            if finish_reason == "tool_calls":
                self._handle_tool_calls(choice, context)
        result = (
            choice.message.content
            if self.postprocess is None
            else self.postprocess(choice.message.content, inputs, context)
        )
        logging.debug(f"chat bot response : {result}")
        return result

    def _chat_stream(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None):
        llm_tools = self._build_llm_tools()
        option = self._build_llm_option()
        finish_reason = None

        while finish_reason is None or finish_reason == "tool_calls":
            full_content = ""
            choice = None

            # 如果有tools，先尝试非流式调用检查是否需要tool_calls
            if llm_tools:
                choice = self.model.chat(self.messages, option=option, tools=llm_tools)
                finish_reason = choice.finish_reason

                if finish_reason == "tool_calls":
                    # 处理tool调用
                    self._handle_tool_calls(choice, context)
                    continue
                else:
                    # 没有tool调用，使用流式输出已获得的内容
                    if choice.message.content:
                        if self.workflow:
                            self.workflow.emit_event(
                                "messages",
                                {"vertex_id": self.id, "message": choice.message.content, "status": "running"},
                            )
                        full_content = choice.message.content
            else:
                # 没有tools，直接使用流式输出
                for msg in self.model.chat_stream(self.messages, option=option):
                    if self.workflow:
                        self.workflow.emit_event(
                            "messages",
                            {"vertex_id": self.id, "message": msg, "status": "running"},
                        )
                    full_content += msg
                finish_reason = "stop"  # 流式输出完成

            break  # 退出while循环

        # 应用postprocess处理
        result = full_content if self.postprocess is None else self.postprocess(full_content, inputs, context)

        self.output = result
        if self.workflow:
            self.workflow.emit_event("messages", {"vertex_id": self.id, "message": None, "status": "end"})
        logging.debug(f"chat bot response : {result}")
        return result

    def _build_llm_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.schema,
                },
            }
            for tool in self.tools
        ]

    def _build_llm_option(self):
        """构建LLM调用的option参数，从params中提取temperature、max_tokens等参数"""
        option = {}
        if self._params:
            # 提取LLM相关参数
            llm_params = [
                "temperature",
                "max_tokens",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
                "response_format",
            ]
            for param in llm_params:
                if param in self._params:
                    option[param] = self._params[param]
        return option

    async def _handle_tool_calls_async(self, choice, context):
        self.messages.append(choice.message)
        async def call_tool(tool, tool_call, context):
            tool_call_name = tool_call.function.name
            tool_call_arguments = json.loads(tool_call.function.arguments)
            return tool_call, await asyncio.to_thread(tool.execute, tool_call_arguments, context)
        tasks = []
        for tool_call in choice.message.tool_calls:
            for tool in self.tools:
                if tool.name == tool_call.function.name:
                    tasks.append(call_tool(tool, tool_call, context))
                    break
            else:
                # 未找到tool
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": json.dumps(f"Error: unable to find tool by name '{tool_call.function.name}'"),
                })
        results = await asyncio.gather(*tasks) if tasks else []
        for tool_call, tool_result in results:
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": json.dumps(tool_result),
            })

    def _handle_tool_calls(self, choice, context):
        # 兼容同步/异步环境
        try:
            loop = asyncio.get_running_loop()
            # 已在事件循环中
            coro = self._handle_tool_calls_async(choice, context)
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                loop.run_until_complete(coro)
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
            # 不在事件循环中
            asyncio.run(self._handle_tool_calls_async(choice, context))
