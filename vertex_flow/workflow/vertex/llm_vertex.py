import asyncio
import inspect
import json
import traceback
from typing import List, Optional

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.constants import (
    CONTENT_KEY,
    CONVERSATION_HISTORY,
    ENABLE_REASONING_KEY,
    ENABLE_SEARCH_KEY,
    ENABLE_STREAM,
    ITERATION_INDEX_KEY,
    LOCAL_VAR,
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
        finish_reason = None
        if self.enable_stream and hasattr(self.model, "chat_stream"):
            return self._chat_stream(inputs, context)

        # Build LLM options
        option = self._build_llm_option(inputs, context)
        llm_tools = self._build_llm_tools()

        # Handle tool calls in a loop
        max_iterations = 10  # 防止无限循环
        iteration_count = 0

        while (finish_reason is None or finish_reason == "tool_calls") and iteration_count < max_iterations:
            iteration_count += 1
            choice = self.model.chat(self.messages, option=option, tools=llm_tools)
            finish_reason = choice.finish_reason

            if finish_reason == "tool_calls":
                # Handle tool calls
                logging.info(f"LLM {self.id} wants to call tools (iteration {iteration_count})")

                # 检查是否有工具调用
                if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                    # 使用统一工具管理器处理工具调用
                    success = self.tool_manager.handle_tool_calls_complete(choice, context, self.messages)
                    if not success:
                        logging.warning(f"Tool call handling failed for LLM {self.id}")
                        break
                else:
                    logging.warning(f"No tool calls found in choice for LLM {self.id}")
                    break

                # Reset finish_reason to continue the loop and get the final response after tool calls
                finish_reason = None
                continue
            else:
                # No tool calls, process the final response
                content = choice.message.content or ""
                result = content if self.postprocess is None else self.postprocess(content, inputs, context)
                self.output = result

                # Handle token usage
                self._handle_token_usage()

                logging.debug(f"chat bot response : {result}")
                return result

        if iteration_count >= max_iterations:
            logging.error(f"LLM {self.id} exceeded maximum iterations ({max_iterations}), stopping")
            return "Error: Maximum tool call iterations exceeded"

        return "Error: Unexpected end of chat loop"

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
        统一的流式核心逻辑，支持reasoning和工具调用
        根据emit_events参数决定是否发送事件
        """
        try:
            # Build LLM options
            option = self._build_llm_option(inputs, context)
            llm_tools = self._build_llm_tools()

            # Handle tool calls in a loop
            finish_reason = None
            while finish_reason is None or finish_reason == "tool_calls":

                # 检查是否启用reasoning（用于消息类型判断）
                enable_reasoning = self.params.get(ENABLE_REASONING_KEY, False)
                message_type = MESSAGE_TYPE_REASONING if enable_reasoning else MESSAGE_TYPE_REGULAR

                # 在流式模式下，坚持使用流式处理
                if self.enable_stream and hasattr(self.model, "chat_stream"):
                    try:
                        # 使用流式模式
                        stream_option = option.copy() if option else {}
                        if llm_tools:
                            stream_option["tools"] = llm_tools

                        # 检查messages中是否已经有未处理的assistant/tool_calls消息
                        pending_tool_calls = []
                        for msg in self.messages:
                            if (
                                msg.get("role") == "assistant"
                                and msg.get("tool_calls")
                                and not any(
                                    tool_msg.get("tool_call_id") == tc.get("id")
                                    for tc in msg["tool_calls"]
                                    for tool_msg in self.messages
                                    if tool_msg.get("role") == "tool"
                                )
                            ):
                                pending_tool_calls.extend(msg["tool_calls"])

                        if pending_tool_calls:
                            # 有未处理的工具调用，直接处理
                            logging.info(f"Found {len(pending_tool_calls)} pending tool calls, processing directly")

                            # 发送工具调用请求事件（pending calls）
                            if emit_events and self.workflow:
                                if self.tool_manager and self.tool_manager.tool_caller:
                                    for request_msg in self.tool_manager.tool_caller.format_tool_call_request(pending_tool_calls):
                                        self.workflow.emit_event(
                                            EventType.MESSAGES,
                                            {VERTEX_ID_KEY: self.id, CONTENT_KEY: request_msg, TYPE_KEY: message_type},
                                        )

                            # 使用统一工具管理器执行工具调用
                            tool_messages = self.tool_manager.execute_tool_calls(pending_tool_calls, context)
                            # 确保所有工具消息的content不为null
                            for tool_msg in tool_messages:
                                if tool_msg.get("content") is None:
                                    tool_msg["content"] = ""
                            self.messages.extend(tool_messages)

                            # 发送工具调用结果事件（pending calls）
                            if emit_events and self.workflow:
                                if self.tool_manager and self.tool_manager.tool_caller:
                                    for result_msg in self.tool_manager.tool_caller.format_tool_call_results(pending_tool_calls, self.messages):
                                        self.workflow.emit_event(
                                            EventType.MESSAGES,
                                            {VERTEX_ID_KEY: self.id, CONTENT_KEY: result_msg, TYPE_KEY: message_type},
                                        )

                            # 继续循环以获取最终响应
                            finish_reason = None
                            continue
                        else:
                            # 使用改进的流式处理，支持实时工具调用检测和多轮处理
                            has_content = False
                            tool_calls_detected = False
                            
                            # 记录流式处理开始前的消息数量
                            messages_before_stream = len(self.messages)

                            # 使用流式处理，实时检测工具调用和内容
                            for chunk in self.model.chat_stream(self.messages, option=stream_option):
                                if chunk:
                                    # 检查是否为工具调用相关的输出
                                    if self._is_tool_call_chunk(chunk):
                                        tool_calls_detected = True
                                        # 工具调用内容不需要输出给用户
                                        continue
                                    else:
                                        # 普通内容，输出给用户
                                        has_content = True
                                        # Emit event if requested
                                        if emit_events and self.workflow:
                                            self.workflow.emit_event(
                                                EventType.MESSAGES,
                                                {VERTEX_ID_KEY: self.id, CONTENT_KEY: chunk, TYPE_KEY: message_type},
                                            )
                                        yield chunk

                            # 检查是否有新增的工具调用需要执行
                            new_tool_calls = self._extract_new_tool_calls(messages_before_stream)

                            if new_tool_calls:
                                # 有新的工具调用需要执行
                                logging.info(f"LLM {self.id} executing {len(new_tool_calls)} tools after streaming")

                                # 发送工具调用请求事件
                                if emit_events and self.workflow:
                                    if self.tool_manager and self.tool_manager.tool_caller:
                                        for request_msg in self.tool_manager.tool_caller.format_tool_call_request(new_tool_calls):
                                            self.workflow.emit_event(
                                                EventType.MESSAGES,
                                                {VERTEX_ID_KEY: self.id, CONTENT_KEY: request_msg, TYPE_KEY: message_type},
                                            )

                                # 使用统一工具管理器执行工具调用
                                tool_messages = self.tool_manager.execute_tool_calls(new_tool_calls, context)
                                # 确保所有工具消息的content不为null
                                for tool_msg in tool_messages:
                                    if tool_msg.get("content") is None:
                                        tool_msg["content"] = ""
                                self.messages.extend(tool_messages)

                                # 发送工具调用结果事件
                                if emit_events and self.workflow:
                                    if self.tool_manager and self.tool_manager.tool_caller:
                                        for result_msg in self.tool_manager.tool_caller.format_tool_call_results(new_tool_calls, self.messages):
                                            self.workflow.emit_event(
                                                EventType.MESSAGES,
                                                {VERTEX_ID_KEY: self.id, CONTENT_KEY: result_msg, TYPE_KEY: message_type},
                                            )

                                # 继续循环以获取最终响应或处理更多工具调用
                                finish_reason = None
                                continue
                            elif has_content or tool_calls_detected:
                                # 有内容输出或处理了工具调用，结束当前轮次
                                finish_reason = "stop"
                            else:
                                # 没有输出内容也没有工具调用，尝试获取最终响应
                                logging.info(f"LLM {self.id} no content or tool calls found, getting final response")
                                final_choice = self.model.chat(self.messages, option=option, tools=llm_tools)

                                if final_choice.finish_reason == "tool_calls":
                                    # 还有工具调用，继续循环
                                    finish_reason = None
                                    continue
                                else:
                                    # 获取最终内容
                                    content = final_choice.message.content or ""
                                    if content:
                                        if emit_events and self.workflow:
                                            self.workflow.emit_event(
                                                EventType.MESSAGES,
                                                {
                                                    VERTEX_ID_KEY: self.id,
                                                    CONTENT_KEY: content,
                                                    TYPE_KEY: message_type,
                                                },
                                            )
                                        yield content
                                    finish_reason = "stop"

                    except Exception as stream_error:
                        # 流式处理失败，记录错误但继续流式模式
                        logging.error(f"Streaming error occurred: {stream_error}")
                        import traceback

                        logging.error(f"Streaming error details: {traceback.format_exc()}")

                        # 在流式模式下优雅地处理错误
                        error_message = f"流式处理遇到错误: {str(stream_error)}"
                        if emit_events and self.workflow:
                            self.workflow.emit_event(
                                EventType.MESSAGES,
                                {VERTEX_ID_KEY: self.id, CONTENT_KEY: error_message, TYPE_KEY: message_type},
                            )
                        yield error_message
                        finish_reason = "stop"  # 结束当前循环，不回退到非流式

                # 非流式模式处理（仅在明确非流式模式下使用）
                if not self.enable_stream and (finish_reason == "tool_calls" or not hasattr(self.model, "chat_stream")):
                    if llm_tools:
                        choice = self.model.chat(self.messages, option=option, tools=llm_tools)
                        finish_reason = choice.finish_reason

                        if finish_reason == "tool_calls":
                            # Handle tool calls
                            logging.info(f"LLM {self.id} wants to call tools")
                            
                            # 发送工具调用请求事件（非流式模式）
                            if self.workflow:
                                tool_calls = choice.message.tool_calls if hasattr(choice.message, "tool_calls") else []
                                if tool_calls and self.tool_manager and self.tool_manager.tool_caller:
                                    for request_msg in self.tool_manager.tool_caller.format_tool_call_request(tool_calls):
                                        self.workflow.emit_event(
                                            EventType.MESSAGES,
                                            {VERTEX_ID_KEY: self.id, CONTENT_KEY: request_msg, TYPE_KEY: message_type},
                                        )
                            
                            # 执行工具调用
                            self.tool_manager.handle_tool_calls_complete(choice, context, self.messages)
                            
                            # 发送工具调用结果事件（非流式模式）
                            if self.workflow:
                                tool_calls = choice.message.tool_calls if hasattr(choice.message, "tool_calls") else []
                                if tool_calls and self.tool_manager and self.tool_manager.tool_caller:
                                    for result_msg in self.tool_manager.tool_caller.format_tool_call_results(tool_calls, self.messages):
                                        self.workflow.emit_event(
                                            EventType.MESSAGES,
                                            {VERTEX_ID_KEY: self.id, CONTENT_KEY: result_msg, TYPE_KEY: message_type},
                                        )
                            # Get the response after tool calls (may contain more tool calls)
                            final_choice = self.model.chat(self.messages, option=option, tools=llm_tools)
                            finish_reason = final_choice.finish_reason

                            if finish_reason == "tool_calls":
                                # More tool calls, continue the loop
                                logging.info(f"LLM {self.id} has more tool calls after previous ones (non-streaming)")
                                finish_reason = None
                                continue
                            else:
                                # No more tool calls, yield the final response
                                content = final_choice.message.content or ""
                                if not content and final_choice.finish_reason == "stop":
                                    # LLM没有自动总结，补一条user消息重试
                                    max_retry = 2
                                    retry_count = 0
                                    while retry_count < max_retry and not content:
                                        self.messages.append({"role": "user", "content": "请根据工具结果继续总结"})
                                        retry_choice = self.model.chat(self.messages, option=option, tools=llm_tools)
                                        content = retry_choice.message.content or ""
                                        retry_count += 1
                                        if content:
                                            break
                                    if not content:
                                        content = "工具调用已完成，但LLM未返回总结内容。"
                                if content:
                                    if emit_events and self.workflow:
                                        self.workflow.emit_event(
                                            EventType.MESSAGES,
                                            {VERTEX_ID_KEY: self.id, CONTENT_KEY: content, TYPE_KEY: message_type},
                                        )
                                    yield content
                                    logging.info(
                                        f"LLM {self.id} yielded final response after tool calls (non-streaming): {content[:100]}..."
                                    )
                                finish_reason = "stop"
                        else:
                            # No tool calls, yield the content
                            content = choice.message.content or ""
                            if content:
                                if emit_events and self.workflow:
                                    self.workflow.emit_event(
                                        EventType.MESSAGES,
                                        {VERTEX_ID_KEY: self.id, CONTENT_KEY: content, TYPE_KEY: message_type},
                                    )
                                yield content
                            finish_reason = "stop"
                    else:
                        choice = self.model.chat(self.messages, option=option)
                        content = choice.message.content or ""
                        if content:
                            if emit_events and self.workflow:
                                self.workflow.emit_event(
                                    EventType.MESSAGES,
                                    {VERTEX_ID_KEY: self.id, CONTENT_KEY: content, TYPE_KEY: message_type},
                                )
                            yield content
                        finish_reason = "stop"

        except Exception as e:
            error_msg = f"LLM streaming error: {str(e)}"
            logging.error(error_msg)
            if emit_events and self.workflow:
                self.workflow.emit_event(
                    EventType.MESSAGES, {VERTEX_ID_KEY: self.id, "error": error_msg, TYPE_KEY: MESSAGE_TYPE_ERROR}
                )
            yield error_msg
        finally:
            # Handle token usage after streaming is complete
            self._handle_token_usage()

        # Send end event when streaming is complete (only for event-based streaming)
        if emit_events and self.workflow:
            self.workflow.emit_event(
                EventType.MESSAGES, {VERTEX_ID_KEY: self.id, MESSAGE_KEY: None, "status": MESSAGE_TYPE_END}
            )

    def _is_tool_call_chunk(self, chunk: str) -> bool:
        """检查chunk是否包含工具调用相关内容，这些内容不应输出给用户
        
        注意：这个方法目前返回False，让ChatModel的流式处理自行处理工具调用。
        因为ChatModel已经有完善的工具调用处理逻辑，我们不需要在这里过滤。
        """
        # 暂时返回False，让所有内容都正常输出
        # ChatModel的chat_stream方法会正确处理工具调用和内容的分离
        return False

    def _extract_new_tool_calls(self, messages_before_stream: int) -> List[Dict[str, Any]]:
        """提取流式处理后新增的工具调用"""
        new_tool_calls = []
        
        # 只检查流式处理后新增的消息
        for msg in self.messages[messages_before_stream:]:
            if (
                msg.get("role") == "assistant"
                and msg.get("tool_calls")
                and not any(
                    tool_msg.get("tool_call_id") == tc.get("id")
                    for tc in msg["tool_calls"]
                    for tool_msg in self.messages
                    if tool_msg.get("role") == "tool"
                )
            ):
                new_tool_calls.extend(msg["tool_calls"])
                 
        return new_tool_calls

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

    async def _handle_tool_calls_async(self, choice, context):
        # Convert ChatCompletionMessage to dict format
        content = choice.message.content
        message_dict = {
            "role": choice.message.role,
            "content": content if content is not None else "",  # 确保content不为null
        }
        # Add tool_calls if present
        if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
            message_dict["tool_calls"] = choice.message.tool_calls

        self.messages.append(message_dict)

        # 统一转换tool_calls为对象格式
        normalized_tool_calls = RuntimeToolCall.normalize_list(choice.message.tool_calls)

        async def call_tool(tool, tool_call, context):
            # 现在tool_call一定是对象格式
            tool_call_name = tool_call.function.name
            tool_call_arguments = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id
            return tool_call, await asyncio.to_thread(tool.execute, tool_call_arguments, context)

        tasks = []
        for tool_call in normalized_tool_calls:
            tool_call_name = tool_call.function.name
            for tool in self.tools:
                if tool.name == tool_call_name:
                    tasks.append(call_tool(tool, tool_call, context))
                    break
            else:
                # 未找到tool
                error_content = json.dumps(f"Error: unable to find tool by name '{tool_call.function.name}'")
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": error_content if error_content is not None else "",
                    }
                )
        results = await asyncio.gather(*tasks) if tasks else []
        for tool_call, tool_result in results:
            # 确保content不为null
            content = json.dumps(tool_result)
            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": content if content is not None else "",
                }
            )

    def _handle_tool_calls(self, choice, context):
        # 优先使用tool_caller处理工具调用
        if self.tool_caller:
            # 使用tool_caller处理
            tool_calls = self.tool_caller.extract_tool_calls_from_choice(choice)
            if tool_calls:
                # 添加assistant消息
                assistant_message = self.tool_caller.create_assistant_message(tool_calls)
                # 确保assistant消息的content不为null
                if assistant_message.get("content") is None:
                    assistant_message["content"] = ""
                self.messages.append(assistant_message)

                # 执行工具调用
                tool_messages = self.tool_caller.execute_tool_calls_sync(tool_calls, context)

                # 添加工具响应消息 - 确保所有工具消息的content不为null
                for tool_msg in tool_messages:
                    if tool_msg.get("content") is None:
                        tool_msg["content"] = ""
                self.messages.extend(tool_messages)
            return

        # 回退到原有逻辑
        # 兼容同步/异步环境
        try:
            loop = asyncio.get_running_loop()
            # 已在事件循环中
            coro = self._handle_tool_calls_async(choice, context)
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()
            loop.run_until_complete(coro)
        except RuntimeError:
            # 不在事件循环中
            asyncio.run(self._handle_tool_calls_async(choice, context))

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
