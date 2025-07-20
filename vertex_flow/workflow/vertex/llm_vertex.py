import asyncio
import inspect
import json
import traceback
from typing import List, Optional

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.stream_data import StreamData

logger = LoggerUtil.get_logger(__name__)
from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.constants import (
    CONTENT_KEY,
    CONVERSATION_HISTORY,
    DEFAULT_MAX_TOOL_ROUNDS,
    ENABLE_REASONING_KEY,
    ENABLE_SEARCH_KEY,
    ENABLE_STREAM,
    MESSAGE_KEY,
    MESSAGE_TYPE_END,
    MESSAGE_TYPE_ERROR,
    MESSAGE_TYPE_REASONING,
    MESSAGE_TYPE_REGULAR,
    MODEL,
    POSTPROCESS,
    PREPROCESS,
    REASONING_CONTENT_ATTR,
    SHOW_REASONING,
    SHOW_REASONING_KEY,
    SOURCE_SCOPE,
    SOURCE_VAR,
    SYSTEM,
    TYPE_KEY,
    USER,
    VERTEX_ID_KEY,
)
from vertex_flow.workflow.event_channel import EventType
from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall, create_tool_caller
from vertex_flow.workflow.tools.tool_manager import ToolManager
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
        task: Optional[Callable[[Dict[str, Any], WorkflowContext[T]], T]] = None,
        params: Dict[str, Any] = None,
        tools: list = None,  # 新增参数
        variables: List[Dict[str, Any]] = None,
        model: ChatModel = None,  # 添加model参数
        tool_caller=None,  # 新增tool_caller参数
    ):
        # """如果传入task则以task为执行单元，否则执行当前llm的chat方法."""
        self.model: ChatModel = model  # 优先使用传入的model
        self.messages = []
        self.system_message = None
        self.user_messages = []
        self.preprocess = None
        self.postprocess = None
        self.tools = tools or []  # 保存可用的function tools
        self.tool_caller = tool_caller  # 保存工具调用器
        self.enable_stream = params.get(ENABLE_STREAM, False) if params else False  # 使用常量 ENABLE_STREAM
        self.enable_reasoning = params.get(ENABLE_REASONING_KEY, False) if params else False  # 支持思考过程
        self.show_reasoning = (
            params.get(SHOW_REASONING_KEY, SHOW_REASONING) if params else SHOW_REASONING
        )  # 是否显示思考过程
        self.token_usage = {}  # 添加token统计属性
        self.usage_history = []  # 添加usage历史记录，用于多轮对话统计

        # 初始化统一工具管理器
        self.tool_manager = ToolManager(tool_caller, tools or [])

        # 如果没有传入tool_caller，则根据模型提供商创建默认的tool_caller
        if self.tool_caller is None and self.model:
            provider = getattr(self.model, "provider", "openai")
            self.tool_caller = create_tool_caller(provider, self.tools)

        # 为模型设置统一工具管理器
        if self.model:
            if not self.model.tool_manager:
                self.model.tool_manager = self.tool_manager

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

            # 更精确的清空策略：只在没有conversation_history时清空，避免影响多轮对话
            if not (inputs and CONVERSATION_HISTORY in inputs):
                self.messages = []

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

        logging.debug(f"{self.id} chat context inputs {inputs}")

        # Add system message if provided
        if self.system_message:
            self.messages.append(
                {"role": "system", "content": self.system_message},
            )

        if self.preprocess is not None:
            self.user_messages = self.preprocess(self.user_messages, inputs, context)

        # Handle conversation history if provided in inputs
        if inputs and CONVERSATION_HISTORY in inputs:
            conversation_history = inputs[CONVERSATION_HISTORY]
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
                    multimodal_content.append({"type": "text", "text": str(current_message)})
                elif inputs.get("text"):
                    multimodal_content.append({"type": "text", "text": str(inputs["text"])})

                # 添加图片内容
                multimodal_content.append({"type": "image_url", "image_url": {"url": image_url}})

                # 替换或添加多模态消息
                if self.messages and self.messages[-1]["role"] == "user":
                    # 替换最后一个用户消息
                    self.messages[-1]["content"] = multimodal_content
                else:
                    # 添加新的多模态消息
                    self.messages.append({"role": "user", "content": multimodal_content})
            else:
                # 只有文本消息
                if isinstance(current_message, dict) and "content" in current_message:
                    # 多模态消息格式
                    self.messages.append(current_message)
                else:
                    # 纯文本消息
                    self.messages.append({"role": "user", "content": str(current_message)})

        system_contains = False
        # replace by env parameters, user parameters and inputs.
        for message in self.messages:
            if message["role"] == "system":
                if system_contains:
                    continue
                system_contains = True

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
                                if key in [CONVERSATION_HISTORY, "current_message", "image_url", "text"]:
                                    continue  # Skip special keys that we've already handled
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
                        if key in [CONVERSATION_HISTORY, "current_message", "image_url", "text"]:
                            continue  # Skip special keys that we've already handled
                        value = value if isinstance(value, str) else str(value)
                        # Support {{inputs.key}} format
                        input_placeholder = "{{" + key + "}}"
                        text_content = text_content.replace(input_placeholder, value)

                text_content = self._replace_placeholders(text_content)
                message["content"] = text_content

        logging.debug(f"{self}, {self.id} chat context messages {self.messages}")

    def _handle_token_usage(self):
        """处理token使用统计的通用方法，供子类调用"""
        # 记录token使用情况
        if hasattr(self.model, "get_usage"):
            usage = self.model.get_usage()
            self.usage_history.append(usage)  # 添加到历史记录
            self.token_usage = usage  # 当前轮次
            logging.info(f"LLM {self.id} token usage: {self.token_usage}")

    def chat(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None):
        """Chat with LLM and handle token usage"""
        if self.enable_stream and hasattr(self.model, "chat_stream"):
            return self._chat_stream(inputs, context)

        # 非流式处理：直接使用模型的chat方法并处理工具调用
        option = self._build_llm_option(inputs, context)
        llm_tools = self._build_llm_tools()

        # 使用tool_manager处理工具调用循环
        if self.tool_manager and llm_tools:
            choice = self.tool_manager.handle_tool_calls_complete(
                None, context, self.messages, lambda: self.model.chat(self.messages, option=option, tools=llm_tools)
            )
            content = (
                choice.message.content
                if hasattr(choice, "message") and hasattr(choice.message, "content")
                else str(choice)
            )
        else:
            choice = self.model.chat(self.messages, option=option, tools=llm_tools)
            content = choice.message.content if hasattr(choice.message, "content") else str(choice)

        # 应用postprocess处理
        result = content if self.postprocess is None else self.postprocess(content, inputs, context)
        self.output = result

        # Handle token usage
        self._handle_token_usage()

        logging.debug(f"chat bot response : {result}")
        return result

    def chat_stream_generator(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None):
        """返回流式输出的生成器，支持reasoning和工具调用"""
        if not (self.enable_stream and hasattr(self.model, "chat_stream")):
            # 如果不支持流式输出，回退到普通模式
            result = self.chat(inputs, context)
            yield result
            return

        # 使用专门的流式生成器逻辑，不发送事件但支持工具调用
        for chunk in self._stream_generator_core(inputs, context):
            yield chunk

    def _chat_stream(self, inputs: Dict[str, Any], context: WorkflowContext[T] = None):
        """基于事件的流式聊天（用于workflow）"""
        full_content = ""
        for chunk in self._stream_chat_core(inputs, context, emit_events=True):
            full_content += chunk

        # 应用postprocess处理
        result = full_content if self.postprocess is None else self.postprocess(full_content, inputs, context)

        self.output = result
        # 结束事件现在由_unified_stream_core统一处理
        logging.debug(f"chat bot response : {result}")
        return result

    def _stream_generator_core(self, inputs: Dict[str, Any], context: WorkflowContext):
        """
        专门用于chat_stream_generator的核心逻辑，支持reasoning和工具调用
        不发送事件，只返回流式内容
        """
        # 使用统一的流式核心方法，但不发送事件
        for chunk in self._unified_stream_core(inputs, context, emit_events=False):
            yield chunk

    def _stream_chat_core(self, inputs: Dict[str, Any], context: WorkflowContext, emit_events: bool = True):
        """
        Core streaming chat method with reasoning support and tool calling
        """
        # 使用统一的流式核心方法，可选择是否发送事件
        for chunk in self._unified_stream_core(inputs, context, emit_events=emit_events):
            yield chunk

    def _unified_stream_core(self, inputs: Dict[str, Any], context: WorkflowContext, emit_events: bool = True):
        """
        统一的流式核心逻辑，支持多轮工具调用直到stop
        根据emit_events参数决定是否发送事件
        """
        try:
            # Build LLM options
            option = self._build_llm_option(inputs, context)
            llm_tools = self._build_llm_tools()

            # 检查是否启用reasoning（用于消息类型判断）
            enable_reasoning = self.params.get(ENABLE_REASONING_KEY, False)
            message_type = MESSAGE_TYPE_REASONING if enable_reasoning else MESSAGE_TYPE_REGULAR

            # 确保只在流式模式下使用此方法
            if not (self.enable_stream and hasattr(self.model, "chat_stream")):
                raise ValueError(
                    f"_unified_stream_core requires streaming mode, but enable_stream={self.enable_stream} or model doesn't support chat_stream"
                )

            # 多轮对话循环，直到没有工具调用为止
            # 支持通过参数配置最大工具调用轮数，默认使用常量值
            max_tool_rounds = self.params.get("max_tool_rounds", DEFAULT_MAX_TOOL_ROUNDS)
            tool_round_count = 0

            while True:
                # 开始新一轮流式对话
                has_tool_calls = False

                # 处理单轮流式对话
                for content_chunk in self._process_single_stream_round(
                    option, llm_tools, message_type, emit_events, context
                ):
                    if content_chunk == "__TOOL_CALLS_DETECTED__":
                        has_tool_calls = True
                        break
                    else:
                        yield content_chunk

                # 如果没有工具调用，结束对话
                if not has_tool_calls:
                    break

                # 检查工具调用次数保护
                tool_round_count += 1
                if tool_round_count >= max_tool_rounds:
                    warning_msg = f"⚠️ 工具调用已达到最大轮数限制 ({max_tool_rounds})，停止继续调用"
                    logger.warning(warning_msg)
                    if emit_events and self.workflow:
                        self.workflow.emit_event(
                            EventType.MESSAGES,
                            {
                                VERTEX_ID_KEY: self.id,
                                CONTENT_KEY: warning_msg,
                                TYPE_KEY: MESSAGE_TYPE_ERROR,
                            },
                        )
                    yield warning_msg
                    break

                # 如果有工具调用，继续下一轮（工具结果已经被tool_manager添加到messages中）
                logger.info(
                    f"Starting tool round {tool_round_count}/{max_tool_rounds}, messages count: {len(self.messages)}"
                )

        except Exception as e:
            error_msg = f"LLM processing error: {str(e)}"
            logging.error(error_msg)
            if emit_events and self.workflow:
                self.workflow.emit_event(
                    EventType.MESSAGES, {VERTEX_ID_KEY: self.id, "error": error_msg, TYPE_KEY: MESSAGE_TYPE_ERROR}
                )
            yield error_msg
        finally:
            # Handle token usage after processing is complete
            self._handle_token_usage()

            # Send end event when processing is complete (only for event-based streaming)
            if emit_events and self.workflow:
                self.workflow.emit_event(
                    EventType.MESSAGES, {VERTEX_ID_KEY: self.id, MESSAGE_KEY: None, "status": MESSAGE_TYPE_END}
                )

    def _process_single_stream_round(
        self, option: Dict[str, Any], llm_tools, message_type: str, emit_events: bool, context: WorkflowContext
    ):
        """
        处理单轮流式对话，返回内容块或工具调用信号
        """
        # 使用 ChatModel 的 chat_stream 接口获取流式生成器
        stream_generator = self.model.chat_stream(self.messages, option, llm_tools)

        for stream_data in stream_generator:
            if stream_data is None:
                continue

            # 如果是StreamData对象，按照预期处理
            if isinstance(stream_data, StreamData):
                data_type = stream_data.type.value
                data_content = stream_data.get_data()

                if data_type == "content" or data_type == "reasoning":
                    # 处理内容数据
                    self._emit_content_event(data_content, message_type, emit_events)
                    yield data_content
                elif data_type == "tool_calls":
                    # 处理工具调用
                    if data_content and self._handle_tool_calls(data_content, context, emit_events):
                        yield "__TOOL_CALLS_DETECTED__"
                        return
                elif data_type == "error":
                    # 处理错误数据
                    self._emit_error_event(data_content, emit_events)
                    yield f"\n⚠️ {data_content}\n"
                elif data_type == "usage":
                    # 处理使用统计数据，累加到历史中
                    self._accumulate_usage(data_content)
                    continue
            else:
                # 处理非StreamData对象
                content_str = str(stream_data) if stream_data else ""
                if content_str:
                    self._emit_content_event(content_str, message_type, emit_events)
                    yield content_str

    def _emit_content_event(self, content: str, message_type: str, emit_events: bool):
        """发送内容事件"""
        if emit_events and self.workflow:
            self.workflow.emit_event(
                EventType.MESSAGES,
                {
                    VERTEX_ID_KEY: self.id,
                    CONTENT_KEY: content,
                    TYPE_KEY: message_type,
                },
            )

    def _emit_error_event(self, error_content: str, emit_events: bool):
        """发送错误事件"""
        if emit_events and self.workflow:
            self.workflow.emit_event(
                EventType.MESSAGES,
                {
                    VERTEX_ID_KEY: self.id,
                    "error": error_content,
                    TYPE_KEY: MESSAGE_TYPE_ERROR,
                },
            )

    def _handle_tool_calls(self, tool_calls_data, context: WorkflowContext, emit_events: bool) -> bool:
        """处理工具调用，返回是否成功执行了工具"""
        # 发送工具调用事件，让前端知道工具调用的参数
        if emit_events and self.workflow:
            for tool_call in tool_calls_data:
                self.workflow.emit_event(
                    EventType.MESSAGES,
                    {
                        VERTEX_ID_KEY: self.id,
                        "tool_call": tool_call,
                        TYPE_KEY: "tool_call",
                    },
                )

        # 实际执行工具调用
        if hasattr(self, "tool_manager") and self.tool_manager:
            tool_executed = self.tool_manager.handle_tool_calls_complete(tool_calls_data, context, self.messages)
            if tool_executed:
                logger.info(f"Tool executed successfully, messages updated to {len(self.messages)} entries")
                return True
        else:
            # 如果没有工具管理器，至少添加assistant消息到对话历史
            assistant_msg = {"role": "assistant", "content": "", "tool_calls": tool_calls_data}
            if assistant_msg not in self.messages:
                self.messages.append(assistant_msg)
                logger.info(f"Tool calls detected, assistant message appended: {assistant_msg}")

        return False

    def _accumulate_usage(self, usage_data):
        """累加token使用量"""
        if usage_data and isinstance(usage_data, dict):
            # 将使用统计添加到历史记录中
            self.usage_history.append(usage_data)
            logger.debug(f"Token usage accumulated: {usage_data}")

    def _build_llm_tools(self):
        if not self.tools:
            return None  # Return None instead of empty list to avoid API error

        # 如果有tool_caller，确保其工具列表是最新的
        if self.tool_caller:
            self.tool_caller.tools = self.tools

        # 初始化或更新统一工具管理器
        if not hasattr(self, "tool_manager"):
            self.tool_manager = ToolManager(self.tool_caller, self.tools)
        else:
            self.tool_manager.update_tools(self.tools)

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

    def _build_llm_option(self, inputs: Dict[str, Any], context: Optional[WorkflowContext] = None) -> Dict[str, Any]:
        """Build LLM options from inputs and context"""
        option = {}

        # Add standard parameters
        if "temperature" in self.params:
            option["temperature"] = self.params["temperature"]
        if "max_tokens" in self.params:
            option["max_tokens"] = self.params["max_tokens"]
        if "top_p" in self.params:
            option["top_p"] = self.params["top_p"]

        # Add reasoning parameters (for display control)
        if SHOW_REASONING_KEY in self.params:
            option[SHOW_REASONING_KEY] = self.params[SHOW_REASONING_KEY]

        # Add enable_search parameter for web search
        if ENABLE_SEARCH_KEY in self.params:
            option[ENABLE_SEARCH_KEY] = self.params[ENABLE_SEARCH_KEY]

        # Add tools if available
        if self.tools:
            option["tools"] = [tool.to_dict() for tool in self.tools]

        return option

    def get_total_usage(self) -> dict:
        """
        获取多轮对话的总token消耗统计
        """
        total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        for usage in self.usage_history:
            for key in total:
                if usage.get(key) is not None:
                    total[key] += usage[key]
        return total

    def reset_usage_history(self):
        """
        重置usage历史记录
        """
        self.usage_history = []
        self.token_usage = {}
