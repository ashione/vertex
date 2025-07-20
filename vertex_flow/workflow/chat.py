import abc
import base64
from typing import Any, Dict, List, Optional, Union

import requests
from openai import OpenAI
from openai.types.chat.chat_completion import Choice

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import (
    CONTENT_ATTR,
    ENABLE_REASONING_KEY,
    ENABLE_SEARCH_KEY,
    REASONING_CONTENT_ATTR,
    SHOW_REASONING_KEY,
)
from vertex_flow.workflow.stream_data import StreamData, StreamDataType
from vertex_flow.workflow.utils import factory_creator, timer_decorator

logger = LoggerUtil.get_logger(__name__)


class StreamProcessor:
    """流式处理器，负责解析流式响应并返回结构化数据"""

    def __init__(self, chat_model, messages):
        self.chat_model = chat_model
        self.messages = messages
        self.tool_call_fragments = []
        self.tool_calls_detected = False
        self.tool_calls_completed = False

        # 增量状态管理：避免重复合并操作
        self.merged_tool_calls = {}  # {call_id: merged_call_dict}
        self.executed_call_ids = set()  # 已执行的工具调用ID
        self.last_fragment_count = 0  # 上次处理时的分片数量

    def process_stream(self, completion):
        """处理流式响应，返回结构化数据"""
        chunk_count = 0

        for chunk in completion:
            chunk_count += 1
            yield from self._process_chunk(chunk)

        # 流式处理结束后，处理剩余的工具调用
        yield from self._finalize_tool_calls()

    def _process_chunk(self, chunk):
        """处理单个响应块，返回结构化数据"""
        # 处理usage信息
        self._handle_usage(chunk)

        if not (chunk.choices and len(chunk.choices) > 0):
            return

        delta = chunk.choices[0].delta

        # 处理工具调用
        tool_call_results = self._handle_tool_calls_in_chunk(chunk)
        if tool_call_results:
            yield from tool_call_results
            return

        # 处理内容
        content_results = self._handle_content(delta)
        if content_results:
            yield from content_results

    def _handle_usage(self, chunk):
        """处理usage信息"""
        if hasattr(chunk, "usage") and chunk.usage:
            self.chat_model._set_usage(chunk)
            logger.debug(f"Streaming usage received from {self.chat_model.provider}: {chunk.usage}")

    def _handle_tool_calls_in_chunk(self, chunk):
        """处理块中的工具调用，返回结构化的工具调用数据"""
        tool_calls_in_chunk = self.chat_model._extract_tool_calls_from_chunk(chunk)
        if not tool_calls_in_chunk:
            return []

        results = []

        # 如果工具调用已完成但又检测到新的工具调用，先处理之前的
        if self.tool_calls_completed:
            remaining_results = list(self._process_remaining_tool_calls())
            self._reset_tool_call_state()
            results.extend(remaining_results)

        self.tool_calls_detected = True
        self.tool_call_fragments.extend(tool_calls_in_chunk)

        # 尝试合并当前的工具调用分片，如果可以合并成完整调用则返回结构化数据
        complete_tool_results = list(self._try_execute_complete_tool_calls())
        results.extend(complete_tool_results)

        return results

    def _process_remaining_tool_calls(self):
        """处理剩余的工具调用片段，返回结构化数据"""
        if not self.tool_call_fragments:
            return

        remaining_calls = self.chat_model._merge_tool_call_fragments(self.tool_call_fragments)
        if remaining_calls:
            logger.info(f"Processing {len(remaining_calls)} remaining tool calls before new batch")
            # 返回结构化的工具调用数据
            yield StreamData.create_tool_calls(remaining_calls)

    def _reset_tool_call_state(self):
        """重置工具调用状态"""
        self.tool_call_fragments = []
        self.tool_calls_detected = False
        self.tool_calls_completed = False
        logger.info("Reset tool call state for new batch")

    def _handle_content(self, delta):
        """处理内容，返回结构化的内容数据"""
        # 处理reasoning内容
        reasoning_content = self._extract_reasoning_content(delta)
        if reasoning_content:
            yield StreamData.create_reasoning(reasoning_content)
            return

        # 处理普通内容
        content = self._extract_regular_content(delta)
        if content:
            yield StreamData.create_content(content)

    def _extract_reasoning_content(self, delta):
        """提取reasoning内容"""
        if hasattr(delta, REASONING_CONTENT_ATTR) and getattr(delta, REASONING_CONTENT_ATTR):
            return getattr(delta, REASONING_CONTENT_ATTR)
        return None

    def _extract_regular_content(self, delta):
        """提取并处理普通内容"""
        if not (hasattr(delta, CONTENT_ATTR) and getattr(delta, CONTENT_ATTR)):
            return None

        content = getattr(delta, CONTENT_ATTR)

        # 检查是否包含推理标记
        reasoning_markers = ["<thinking>", "<think>", "<reasoning>", "思考：", "分析："]
        if any(marker in content for marker in reasoning_markers):
            return self._clean_reasoning_markers(content)

        return content

    def _clean_reasoning_markers(self, content):
        """清理推理标记"""
        display_content = content
        tags_to_remove = ["<thinking>", "</thinking>", "<think>", "</think>", "<reasoning>", "</reasoning>"]
        for tag in tags_to_remove:
            display_content = display_content.replace(tag, "")
        return display_content

    def _try_execute_complete_tool_calls(self):
        """尝试识别已完整的工具调用，返回结构化数据"""
        if not self.tool_call_fragments:
            logger.debug("No tool call fragments to process")
            return

        # 检查是否有新的分片需要处理
        current_fragment_count = len(self.tool_call_fragments)
        if current_fragment_count == self.last_fragment_count:
            logger.debug(
                f"No new fragments to process (current: {current_fragment_count}, last: {self.last_fragment_count})"
            )
            return  # 没有新分片，无需重新处理

        # 只处理新增的分片
        new_fragments = self.tool_call_fragments[self.last_fragment_count :]
        logger.debug(f"Processing {len(new_fragments)} new fragments (total: {current_fragment_count})")
        self._update_merged_calls_incrementally(new_fragments)
        self.last_fragment_count = current_fragment_count

        # 检查哪些工具调用现在是完整的且未标记过
        complete_calls = []
        for call_id, merged_call in self.merged_tool_calls.items():
            if call_id not in self.executed_call_ids:
                is_complete = self._is_tool_call_complete(merged_call)
                logger.debug(
                    f"Tool call {call_id} complete: {is_complete}, arguments: {merged_call.get('function', {}).get('arguments', 'N/A')}"
                )
                if is_complete:
                    complete_calls.append(merged_call)
                    self.executed_call_ids.add(call_id)
                    logger.info(f"Marking tool call {call_id} as identified (not executed by StreamProcessor)")

        # 如果有完整的工具调用，返回结构化数据
        if complete_calls:
            logger.info(f"Found {len(complete_calls)} complete tool calls, sending to LLM layer for execution")
            # 返回结构化的工具调用数据，由上层LLM负责实际执行
            yield StreamData.create_tool_calls(complete_calls)
        else:
            logger.debug(
                f"No complete tool calls found (merged: {len(self.merged_tool_calls)}, identified: {len(self.executed_call_ids)})"
            )

    def _update_merged_calls_incrementally(self, new_fragments):
        """增量更新合并的工具调用状态"""
        for fragment in new_fragments:
            if not hasattr(fragment, "id") or not fragment.id:
                continue

            call_id = fragment.id

            # 如果是新的工具调用，初始化
            if call_id not in self.merged_tool_calls:
                self.merged_tool_calls[call_id] = {
                    "id": call_id,
                    "function": {
                        "name": getattr(fragment.function, "name", "") if hasattr(fragment, "function") else "",
                        "arguments": "",
                    },
                }

            # 增量更新function信息
            if hasattr(fragment, "function") and fragment.function:
                current_call = self.merged_tool_calls[call_id]

                # 更新function name（如果有）
                if hasattr(fragment.function, "name") and fragment.function.name:
                    current_call["function"]["name"] = fragment.function.name

                # 增量拼接arguments
                if hasattr(fragment.function, "arguments") and fragment.function.arguments:
                    current_call["function"]["arguments"] += fragment.function.arguments

    def _is_tool_call_complete(self, tool_call):
        """检查工具调用是否完整"""
        if not tool_call or not isinstance(tool_call, dict):
            return False

        # 检查必要字段
        if not tool_call.get("id") or not tool_call.get("function"):
            return False

        function = tool_call.get("function", {})
        if not function.get("name"):
            return False

        # 检查arguments是否存在（允许空字符串）
        arguments = function.get("arguments")
        if arguments is None:
            return False

        # 放宽JSON完整性检查：允许空字符串、空对象或看起来完整的JSON
        arguments_str = str(arguments).strip()

        # 允许空参数
        if arguments_str == "" or arguments_str == "{}":
            return True

        # 检查是否看起来像完整的JSON（以}、]、"或数字结尾）
        if (
            arguments_str.endswith("}")
            or arguments_str.endswith("]")
            or arguments_str.endswith('"')
            or arguments_str.endswith("'")
            or arguments_str[-1].isdigit()
            or arguments_str.lower() in ["true", "false", "null"]
        ):
            return True

        # 尝试解析JSON来验证完整性
        try:
            import json

            json.loads(arguments_str)
            return True
        except (json.JSONDecodeError, ValueError):
            # JSON不完整，但记录日志以便调试
            logger.debug(f"Tool call {tool_call.get('id')} arguments incomplete: {arguments_str}")
            return False

    def _finalize_tool_calls(self):
        """在流式处理结束时，清理残留状态"""
        # 处理所有剩余的分片（如果有新的）
        if len(self.tool_call_fragments) > self.last_fragment_count:
            new_fragments = self.tool_call_fragments[self.last_fragment_count :]
            self._update_merged_calls_incrementally(new_fragments)

        # 检查是否有未执行的工具调用，记录警告但不执行
        remaining_calls = []
        incomplete_calls = []

        for call_id, merged_call in self.merged_tool_calls.items():
            if call_id not in self.executed_call_ids:
                # 检查工具调用是否完整
                if self._is_tool_call_complete(merged_call):
                    remaining_calls.append(merged_call)
                    logger.warning(
                        f"Found unidentified complete tool call {call_id} at stream end: {merged_call.get('function', {}).get('name', 'unknown')}"
                    )
                else:
                    incomplete_calls.append((call_id, merged_call))
                    logger.warning(f"Found incomplete tool call {call_id} at stream end: {merged_call}")

        # 记录统计信息
        if remaining_calls:
            logger.warning(f"Stream ended with {len(remaining_calls)} unidentified complete tool calls")

        if incomplete_calls:
            logger.warning(f"Stream ended with {len(incomplete_calls)} incomplete tool calls")
            for call_id, incomplete_call in incomplete_calls:
                function_name = incomplete_call.get("function", {}).get("name", "unknown")
                arguments = incomplete_call.get("function", {}).get("arguments", "")
                logger.debug(f"Incomplete tool call {call_id}: function={function_name}, arguments={arguments}")

        # 清理所有状态，避免后续调用时状态残留
        self._reset_all_state()

        # 流式处理结束，不返回任何数据
        return
        yield  # 使这个方法成为生成器，但不产生任何数据

    def _reset_all_state(self):
        """重置所有状态，避免后续调用时状态残留"""
        self.tool_call_fragments = []
        self.tool_calls_detected = False
        self.tool_calls_completed = True

        # 清理增量状态管理相关的状态
        self.merged_tool_calls.clear()
        self.executed_call_ids.clear()
        self.last_fragment_count = 0


@factory_creator
class ChatModel(abc.ABC):
    """
    这是一个抽象基类示例。
    """

    def __init__(self, name: str, sk: str, base_url: str, provider: str, tool_manager=None, tool_caller=None):
        self.name = name
        self.sk = sk
        self.provider = provider
        self._usage = {}  # 存储最新的usage信息
        logger.info(f"Chat model : {self.name}, sk {self.sk}, provider = {self.provider}, base url {base_url}.")
        # 为序列化保存.
        self._base_url = base_url
        self.client = OpenAI(
            base_url=self._base_url,
            api_key=sk,
        )

        # 工具管理器
        self.tool_manager = tool_manager

        # 工具调用器
        self.tool_caller = tool_caller
        if self.tool_caller is None:
            from vertex_flow.workflow.tools.tool_caller import create_tool_caller

            self.tool_caller = create_tool_caller(provider, [])

    def __get_state__(self):
        return {
            "class_name": self.__class__.__name__.lower(),
            "base_url": self._base_url,
            "name": self.name,
            "sk": self.sk,
            "provider": self.provider,
        }

    def _process_multimodal_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理多模态消息，将文本和图片URL转换为OpenAI兼容的格式
        同时验证消息序列的完整性
        """
        processed_messages = []

        # 首先收集所有可用的tool_call_ids
        available_tool_call_ids = set()
        for message in messages:
            role = message.get("role", "")
            if role == "assistant" and "tool_calls" in message:
                tool_calls = message.get("tool_calls", [])
                for tc in tool_calls:
                    tc_id = tc.get("id")
                    if tc_id:
                        available_tool_call_ids.add(tc_id)

        # 然后处理所有消息
        for message in messages:
            logger.debug(f"Processing message: {message}")

            # 根据消息角色和内容类型来处理
            role = message.get("role", "")
            content = message.get("content")

            # 助手消息且包含工具调用
            if role == "assistant" and "tool_calls" in message:
                # 工具调用消息，检查content是否为null
                if content is None:
                    logger.warning(f"Assistant message with null content detected, setting to empty string: {message}")
                    message_copy = message.copy()
                    message_copy["content"] = ""
                    processed_messages.append(message_copy)
                else:
                    processed_messages.append(message)
            # 工具响应消息
            elif role == "tool":
                tool_call_id = message.get("tool_call_id")

                # 验证tool消息是否有对应的tool_calls
                if tool_call_id and tool_call_id not in available_tool_call_ids:
                    logger.error(
                        f"Tool message with tool_call_id '{tool_call_id}' has no corresponding tool_calls message. Skipping this message."
                    )
                    continue  # 跳过这个无效的tool消息

                # 工具响应消息，检查content是否为null
                if content is None:
                    logger.warning(f"Tool message with null content detected, setting to empty string: {message}")
                    message_copy = message.copy()
                    message_copy["content"] = ""
                    processed_messages.append(message_copy)
                else:
                    processed_messages.append(message)
            elif isinstance(content, list):
                # 多模态消息格式
                processed_content = []
                for content_item in content:
                    if content_item.get("type") == "text":
                        processed_content.append(content_item)
                    elif content_item.get("type") == "image_url":
                        image_url = content_item["image_url"]["url"]
                        # 检查是否是base64编码的图片
                        if image_url.startswith("data:image"):
                            processed_content.append(content_item)
                        else:
                            # 对于网络URL，保持原格式
                            processed_content.append(content_item)
                processed_messages.append({"role": role, "content": processed_content})
            elif isinstance(content, str):
                # 纯文本消息，保持原格式
                processed_messages.append(message)
            elif content is None:
                # 空内容，设置为空字符串避免序列化问题
                logger.warning(f"Message with null content detected, setting to empty string: {message}")
                message_copy = message.copy()
                message_copy["content"] = ""
                processed_messages.append(message_copy)
            else:
                # 其他格式，尝试转换为文本
                logger.warning(f"Unknown message format: {message}")
                processed_messages.append(message)

        logger.debug(f"Processed messages: {processed_messages}")
        return processed_messages

    def _build_api_params(self, messages, option: Optional[Dict[str, Any]] = None, stream: bool = False, tools=None):
        """构建API调用参数的基础方法，供子类调用"""
        default_option = {
            "temperature": 1.0,
            "max_tokens": 4096,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "stream": stream,
            "response_format": {"type": "text"},
        }
        if option:
            default_option.update(option)

        # 处理多模态消息
        processed_messages = self._process_multimodal_messages(messages)

        # 构建API调用参数 - 过滤掉自定义参数
        filtered_option = {
            k: v
            for k, v in default_option.items()
            if k not in [SHOW_REASONING_KEY, ENABLE_REASONING_KEY, ENABLE_SEARCH_KEY]
        }
        api_params = {"model": self.name, "messages": processed_messages, **filtered_option}
        if tools is not None and len(tools) > 0:
            api_params["tools"] = tools

        # 通用的流式usage统计支持（适用于支持OpenAI格式的提供商）
        if stream and self._should_include_stream_usage():
            api_params["stream_options"] = {"include_usage": True}

        return api_params

    def _should_include_stream_usage(self) -> bool:
        """判断是否应该在流式调用中包含usage统计，子类可重写此方法"""
        # 默认对大多数支持OpenAI格式的提供商启用
        supported_providers = ["openai", "deepseek", "tongyi", "openrouter"]
        return self.provider in supported_providers

    def _emit_tool_call_request(self, tool_calls):
        """发送工具调用请求消息"""
        if not tool_calls:
            return

        # 统一通过tool_manager访问tool_caller格式化功能
        if self.tool_manager and self.tool_manager.tool_caller:
            for message in self.tool_manager.tool_caller.format_tool_call_request(tool_calls):
                yield message
        else:
            # 回退实现：确保即使没有tool_manager也能发送基本的工具调用请求消息
            logger.warning("No tool_manager.tool_caller available, using fallback tool call request format")
            for tool_call in tool_calls:
                tool_name = (
                    tool_call.get("function", {}).get("name", "")
                    if isinstance(tool_call, dict)
                    else tool_call.function.name
                )
                yield f"\n🔧 调用工具: {tool_name}\n"

    def _emit_tool_call_results(self, tool_calls, messages):
        """发送工具调用结果消息"""
        if not tool_calls:
            return

        # 统一通过tool_manager访问tool_caller格式化功能
        if self.tool_manager and self.tool_manager.tool_caller:
            for message in self.tool_manager.tool_caller.format_tool_call_results(tool_calls, messages):
                yield message
        else:
            # 回退实现：确保即使没有tool_manager也能发送基本的工具调用结果消息
            logger.warning("No tool_manager.tool_caller available, using fallback tool call results format")
            for tool_call in tool_calls:
                tool_call_id = tool_call.get("id", "") if isinstance(tool_call, dict) else tool_call.id
                tool_name = (
                    tool_call.get("function", {}).get("name", "")
                    if isinstance(tool_call, dict)
                    else tool_call.function.name
                )
                # 查找对应的工具响应
                for msg in reversed(messages):
                    if msg.get("role") == "tool" and msg.get("tool_call_id") == tool_call_id:
                        result_content = msg.get("content", "")
                        yield f"\n✅ 工具 {tool_name} 执行结果:\n```\n{result_content}\n```\n"
                        break

    def _create_completion(self, messages, option: Optional[Dict[str, Any]] = None, stream: bool = False, tools=None):
        """Create completion with proper error handling"""
        api_params = self._build_api_params(messages, option, stream, tools)
        try:
            completion = self.client.chat.completions.create(**api_params)
            logger.info(f"show completion: {completion}")
            return completion
        except Exception as e:
            logger.error(f"Error creating completion: {e}, api_params: {api_params}")
            raise

    def chat(self, messages, option: Optional[Dict[str, Any]] = None, tools=None) -> Choice:
        completion = self._create_completion(messages, option, stream=False, tools=tools)
        # 记录usage信息
        self._set_usage(completion)
        return completion.choices[0]

    def _set_usage(self, completion=None):
        """
        默认实现：适配 OpenAI/通义等主流 usage 字段。
        子类可重写以适配特定的 usage 字段结构。
        """
        usage = {}
        if hasattr(completion, "usage") and completion.usage:
            usage = {
                "input_tokens": getattr(completion.usage, "prompt_tokens", None),
                "output_tokens": getattr(completion.usage, "completion_tokens", None),
                "total_tokens": getattr(completion.usage, "total_tokens", None),
            }
        logger.info(f"usage: {usage}")
        self._usage = usage

    def get_usage(self) -> dict:
        return self._usage

    def _merge_tool_call_fragments(self, fragments):
        """
        合并分片为标准的tool_call dict列表，统一使用ToolManager中的ToolCaller
        """
        if not fragments:
            return []

        # 统一通过tool_manager访问tool_caller的合并逻辑
        if self.tool_manager and self.tool_manager.tool_caller:
            return self.tool_manager.tool_caller.merge_tool_call_fragments(fragments)

        # 回退到简单的默认实现（保持向后兼容）
        logger.warning("No tool_manager.tool_caller available, using basic fragment merging")
        return fragments if isinstance(fragments, list) else [fragments]

    def chat_stream(self, messages, option: Optional[Dict[str, Any]] = None, tools=None):
        """统一的流式输出接口，处理所有内容类型包括reasoning"""
        completion = self._create_completion(messages, option, stream=True, tools=tools)

        # 统一的流式处理，根据可用的工具处理器动态选择策略
        yield from self._unified_stream_processing(completion, messages)

    def _unified_stream_processing(self, completion, messages):
        """统一的流式处理方法，动态选择工具处理策略"""
        processor = StreamProcessor(self, messages)
        yield from processor.process_stream(completion)

    def _extract_tool_calls_from_chunk(self, chunk):
        """从流式响应块中提取工具调用，统一使用ToolManager中的ToolCaller"""
        # 统一通过tool_manager访问tool_caller
        if self.tool_manager and self.tool_manager.tool_caller and self.tool_manager.tool_caller.can_handle_streaming():
            if self.tool_manager.tool_caller.is_tool_call_chunk(chunk):
                return self.tool_manager.tool_caller.extract_tool_calls_from_stream(chunk)

        # 回退到传统方法
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                return delta.tool_calls

        return []

    def _handle_tool_calls_in_stream(self, tool_calls, messages):
        """在流式处理中处理工具调用，统一使用tool_manager"""
        # 统一使用工具管理器处理工具调用
        if self.tool_manager:
            return self.tool_manager.handle_tool_calls_complete(tool_calls, None, messages)

        # 如果没有工具管理器，回退到传统方法（仅添加assistant消息）
        else:
            assistant_msg = {"role": "assistant", "content": "", "tool_calls": tool_calls}
            if self._should_append_assistant_message(messages, tool_calls):
                messages.append(assistant_msg)
                logger.info(f"Tool calls detected in stream, assistant message appended: {assistant_msg}")
                return True
            else:
                logger.info(f"Tool calls detected in stream, but identical assistant message already exists, skipping")
                return True

    def _should_append_assistant_message(self, messages, tool_calls):
        """检查是否应该添加assistant消息，避免重复"""
        if not messages:
            return True

        last_msg = messages[-1]
        if (
            last_msg.get("role") == "assistant"
            and last_msg.get("tool_calls")
            and len(last_msg["tool_calls"]) == len(tool_calls)
        ):
            # 检查工具调用是否相同
            existing_ids = {tc.get("id") for tc in last_msg["tool_calls"]}
            new_ids = {tc.get("id") for tc in tool_calls}
            if existing_ids == new_ids:
                return False

        return True

    def model_name(self) -> str:
        return self.name

    def __str__(self):
        return self.model_name() or f"{self.__class__.__name__}({self.provider})"

    # search 工具的具体实现，这里我们只需要返回参数即可
    def search_impl(self, arguments: Dict[str, Any]) -> Any:
        """
        但如果你想使用其他模型，并保留联网搜索的功能，那你只需要修改这里的实现（例如调用搜索
        和获取网页内容等），函数签名不变，依然是 work 的。

        这最大程度保证了兼容性，允许你在不同的模型间切换，并且不需要对代码有破坏性的修改。
        """
        return arguments


class DeepSeek(ChatModel):
    def __init__(self, name="deepseek-chat", sk="", base_url="https://api.deepseek.com"):
        super().__init__(name=name, sk=sk, base_url=base_url, provider="deepseek")


class Tongyi(ChatModel):
    def __init__(self, name="qwen-max", sk="", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"):
        super().__init__(
            name=name,
            sk=sk,
            base_url=base_url,
            provider="tongyi",
        )

    def _create_completion(self, messages, option: Optional[Dict[str, Any]] = None, stream: bool = False, tools=None):
        """Tongyi专属：流式时自动加stream_options.include_usage，并处理enable_search参数"""
        # 先构建基础API参数
        default_option = {
            "temperature": 1.0,
            "max_tokens": 4096,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "stream": stream,
            "response_format": {"type": "text"},
        }
        if option:
            default_option.update(option)

        # 处理多模态消息
        processed_messages = self._process_multimodal_messages(messages)

        # 构建API调用参数 - 过滤掉自定义参数，但保留enable_search
        filtered_option = {
            k: v
            for k, v in default_option.items()
            if k not in [SHOW_REASONING_KEY, ENABLE_REASONING_KEY, ENABLE_SEARCH_KEY]
        }
        api_params = {"model": self.name, "messages": processed_messages, **filtered_option}
        if tools is not None and len(tools) > 0:
            api_params["tools"] = tools

        # 仅Tongyi流式加usage
        if stream:
            api_params["stream_options"] = {"include_usage": True}

        # 处理enable_search参数（通义千问支持）
        if ENABLE_SEARCH_KEY in default_option:
            logger.info(f"Tongyi enable_search requested: {default_option[ENABLE_SEARCH_KEY]}")
            api_params["extra_body"] = {
                "extra_body": {ENABLE_SEARCH_KEY: default_option[ENABLE_SEARCH_KEY], "search_options": True}
            }

        try:
            completion = self.client.chat.completions.create(**api_params)
            return completion
        except Exception as e:
            logger.error(f"Error creating completion: {e}")
            raise


class OpenRouter(ChatModel):
    def __init__(self, name="google/gemini-2.5-pro", sk="", base_url="https://openrouter.ai/api/v1"):
        super().__init__(
            name=name,
            sk=sk,
            base_url=base_url,
            provider="openrouter",
        )


class Ollama(ChatModel):
    def __init__(self, name="qwen:7b", sk="ollama-local", base_url="http://localhost:11434"):
        # Ollama不需要真实的API key，使用占位符
        super().__init__(
            name=name,
            sk=sk,
            base_url=f"{base_url}/v1",
            provider="ollama",
        )

    def model_name(self) -> str:
        return self.name


class Doubao(ChatModel):
    def __init__(self, name="doubao-seed-1.6", sk="", base_url="https://ark.cn-beijing.volces.com/api/v3"):
        super().__init__(
            name=name,
            sk=sk,
            base_url=base_url,
            provider="doubao",
        )

    def model_name(self) -> str:
        return self.name


class Other(ChatModel):
    """
    其他自定义LLM提供商类
    支持每个模型单独配置provider、model name和base_url
    适用于自定义API端点、私有部署模型等场景
    """

    def __init__(self, name="custom-model", sk="", base_url="", provider="other"):
        super().__init__(
            name=name,
            sk=sk,
            base_url=base_url,
            provider=provider,
        )

    def model_name(self) -> str:
        return self.name
