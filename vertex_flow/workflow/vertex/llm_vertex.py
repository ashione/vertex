import asyncio
import inspect
import json
import traceback
from typing import List

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
        variables: List[Dict[str, Any]] = None,
        model: ChatModel = None,  # 添加model参数
    ):
        # """如果传入task则以task为执行单元，否则执行当前llm的chat方法."""
        self.model: ChatModel = model  # 优先使用传入的model
        self.messages = []
        self.system_message = None
        self.user_messages = []
        self.preprocess = None
        self.postprocess = None
        self.tools = tools or []  # 保存可用的function tools
        self.enable_stream = params.get(ENABLE_STREAM, False) if params else False  # 使用常量 ENABLE_STREAM

        if task is None:
            logging.info("Use llm chat in task executing.")
            # 如果没有传入model，则从params中获取
            if self.model is None:
                self.model = params[MODEL]  # 使用常量 MODEL
            self.system_message = params[SYSTEM] if SYSTEM in params else ""  # 使用常量 SYSTEM
            self.user_messages = params[USER] if USER in params else []  # 使用常量 USER
            task = self.chat
            self.preprocess = params[PREPROCESS] if PREPROCESS in params else None  # 使用常量 PREPROCESS
            self.postprocess = params[POSTPROCESS] if POSTPROCESS in params else None  # 使用常量 POSTPROCESS
        super().__init__(id=id, name=name, task_type="LLM", task=task, params=params, variables=variables or [])

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

        # Add system message if provided
        if self.system_message:
            self.messages.append(
                {"role": "system", "content": self.system_message},
            )

        if self.preprocess is not None:
            self.user_messages = self.preprocess(self.user_messages, inputs, context)

        # Handle conversation history if provided in inputs
        if inputs and "conversation_history" in inputs:
            conversation_history = inputs["conversation_history"]
            if isinstance(conversation_history, list):
                # Add each message in the conversation history
                for msg in conversation_history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        # 标准消息格式
                        self.messages.append(msg)
                    elif isinstance(msg, (tuple, list)) and len(msg) == 2:
                        # Handle (user_msg, assistant_msg) tuple/list format
                        user_msg, assistant_msg = msg
                        self.messages.append({"role": "user", "content": str(user_msg)})
                        self.messages.append({"role": "assistant", "content": str(assistant_msg)})
            elif isinstance(conversation_history, str):
                # Handle string format conversation history (fallback)
                self.messages.append({"role": "user", "content": conversation_history})
        else:
            # Handle traditional user_messages format
            for user_message in self.user_messages:
                self.messages.append({"role": "user", "content": user_message})

        # Handle current user message if provided separately
        current_message = inputs.get("current_message") if inputs else None
        image_url = inputs.get("image_url") if inputs else None
        
        if current_message or image_url:
            if image_url:
                # 有图片，创建多模态消息
                multimodal_content = []
                
                # 添加文本内容（如果有的话）
                if current_message:
                    multimodal_content.append({
                        "type": "text",
                        "text": str(current_message)
                    })
                elif inputs.get("text"):
                    multimodal_content.append({
                        "type": "text", 
                        "text": str(inputs["text"])
                    })
                
                # 添加图片内容
                multimodal_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })
                
                # 替换或添加多模态消息
                if self.messages and self.messages[-1]["role"] == "user":
                    # 替换最后一个用户消息
                    self.messages[-1]["content"] = multimodal_content
                else:
                    # 添加新的多模态消息
                    self.messages.append({
                        "role": "user",
                        "content": multimodal_content
                    })
            else:
                # 只有文本消息
                if isinstance(current_message, dict) and "content" in current_message:
                    # 多模态消息格式
                    self.messages.append(current_message)
                else:
                    # 纯文本消息
                    self.messages.append({"role": "user", "content": str(current_message)})

        # replace by env parameters, user parameters and inputs.
        for message in self.messages:
            if "content" not in message or message["content"] is None:
                continue

            # 处理多模态消息
            if isinstance(message["content"], list):
                # 多模态消息，只处理文本部分
                for content_item in message["content"]:
                    if content_item.get("type") == "text":
                        text_content = content_item["text"]
                        # 替换环境变量
                        for key, value in context.get_env_parameters().items():
                            value = value if isinstance(value, str) else str(value)
                            text_content = text_content.replace(env_str(key), value)
                            text_content = text_content.replace(compatiable_env_str(key), value)
                        
                        # 替换用户参数
                        for key, value in context.get_user_parameters().items():
                            value = value if isinstance(value, str) else str(value)
                            text_content = text_content.replace(var_str(key), value)
                        
                        # 替换输入参数
                        if inputs:
                            for key, value in inputs.items():
                                if key in ["conversation_history", "current_message", "image_url", "text"]:
                                    continue  # Skip special keys
                                value = value if isinstance(value, str) else str(value)
                                input_placeholder = "{{" + key + "}}"
                                text_content = text_content.replace(input_placeholder, value)
                        
                        text_content = self._replace_placeholders(text_content)
                        content_item["text"] = text_content
            else:
                # 纯文本消息
                text_content = message["content"]
                for key, value in context.get_env_parameters().items():
                    value = value if isinstance(value, str) else str(value)
                    text_content = text_content.replace(env_str(key), value)
                    # For dify workflow compatiable env.
                    text_content = text_content.replace(compatiable_env_str(key), value)

                for key, value in context.get_user_parameters().items():
                    value = value if isinstance(value, str) else str(value)
                    text_content = text_content.replace(var_str(key), value)

                # replace by inputs parameters
                if inputs:
                    for key, value in inputs.items():
                        if key in ["conversation_history", "current_message", "image_url", "text"]:
                            continue  # Skip special keys that we've already handled
                        value = value if isinstance(value, str) else str(value)
                        # Support {{inputs.key}} format
                        input_placeholder = "{{" + key + "}}"
                        text_content = text_content.replace(input_placeholder, value)

                text_content = self._replace_placeholders(text_content)
                message["content"] = text_content

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

    def chat_stream_generator(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None):
        """返回流式输出的生成器"""
        if not (self.enable_stream and hasattr(self.model, "chat_stream")):
            # 如果不支持流式输出，回退到普通模式
            result = self.chat(inputs, context)
            yield result
            return
        
        # 使用统一的流式聊天核心逻辑
        for chunk in self._stream_chat_core(inputs, context, emit_events=False):
            yield chunk

    def _chat_stream(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None):
        """基于事件的流式聊天（用于workflow）"""
        full_content = ""
        for chunk in self._stream_chat_core(inputs, context, emit_events=True):
            full_content += chunk
        
        # 应用postprocess处理
        result = full_content if self.postprocess is None else self.postprocess(full_content, inputs, context)
        
        self.output = result
        if self.workflow:
            self.workflow.emit_event("messages", {"vertex_id": self.id, "message": None, "status": "end"})
        logging.debug(f"chat bot response : {result}")
        return result
    
    def _stream_chat_core(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None, emit_events: bool = False):
        """流式聊天的核心逻辑，统一处理tools和streaming"""
        llm_tools = self._build_llm_tools()
        option = self._build_llm_option()
        finish_reason = None

        while finish_reason is None or finish_reason == "tool_calls":
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
                    # 没有tool调用，直接返回结果
                    if choice.message.content:
                        if emit_events and self.workflow:
                            self.workflow.emit_event(
                                "messages",
                                {"vertex_id": self.id, "message": choice.message.content, "status": "running"},
                            )
                        yield choice.message.content
            else:
                # 没有tools，直接使用流式输出
                for msg in self.model.chat_stream(self.messages, option=option):
                    if msg:
                        if emit_events and self.workflow:
                            self.workflow.emit_event(
                                "messages",
                                {"vertex_id": self.id, "message": msg, "status": "running"},
                            )
                        yield msg
                finish_reason = "stop"  # 流式输出完成

            break  # 退出while循环

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
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(f"Error: unable to find tool by name '{tool_call.function.name}'"),
                    }
                )
        results = await asyncio.gather(*tasks) if tasks else []
        for tool_call, tool_result in results:
            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": json.dumps(tool_result),
                }
            )

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
