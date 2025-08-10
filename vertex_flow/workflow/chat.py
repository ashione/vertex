import abc
import base64
from typing import Any, Dict, List, Optional, Union

import requests
from openai import OpenAI as OpenAIClient
from openai.types.chat.chat_completion import Choice

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import (
    CONTENT_ATTR,
    ENABLE_REASONING_KEY,
    ENABLE_SEARCH_KEY,
    REASONING_CONTENT_ATTR,
    SHOW_REASONING_KEY,
)
from vertex_flow.workflow.utils import factory_creator, timer_decorator

logging = LoggerUtil.get_logger()


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
        logging.info(f"Chat model : {self.name}, sk {self.sk}, provider = {self.provider}, base url {base_url}.")
        # 为序列化保存.
        self._base_url = base_url
        self.client = OpenAIClient(
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
        """
        processed_messages = []

        for message in messages:
            logging.debug(f"Processing message: {message}")

            # 根据消息角色和内容类型来处理
            role = message.get("role", "")
            content = message.get("content")

            # 助手消息且包含工具调用
            if role == "assistant" and "tool_calls" in message:
                # 工具调用消息，检查content是否为null
                if content is None:
                    logging.warning(f"Assistant message with null content detected, setting to empty string: {message}")
                    message_copy = message.copy()
                    message_copy["content"] = ""
                    processed_messages.append(message_copy)
                else:
                    processed_messages.append(message)
            # 工具响应消息
            elif role == "tool":
                # 工具响应消息，检查content是否为null
                if content is None:
                    logging.warning(f"Tool message with null content detected, setting to empty string: {message}")
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
                logging.warning(f"Message with null content detected, setting to empty string: {message}")
                message_copy = message.copy()
                message_copy["content"] = ""
                processed_messages.append(message_copy)
            else:
                # 其他格式，尝试转换为文本
                logging.warning(f"Unknown message format: {message}")
                processed_messages.append(message)

        logging.debug(f"Processed messages: {processed_messages}")
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

    def _emit_tool_call_results(self, tool_calls, messages):
        """发送工具调用结果消息"""
        if not tool_calls:
            return

        # 统一通过tool_manager访问tool_caller格式化功能
        if self.tool_manager and self.tool_manager.tool_caller:
            for message in self.tool_manager.tool_caller.format_tool_call_results(tool_calls, messages):
                yield message

    def _create_completion(self, messages, option: Optional[Dict[str, Any]] = None, stream: bool = False, tools=None):
        """Create completion with proper error handling"""
        api_params = self._build_api_params(messages, option, stream, tools)
        try:
            completion = self.client.chat.completions.create(**api_params)
            logging.info(f"show completion: {completion}")
            return completion
        except Exception as e:
            logging.error(f"Error creating completion: {e}, api_params: {api_params}")
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
        logging.info(f"usage: {usage}")
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
        logging.warning("No tool_manager.tool_caller available, using basic fragment merging")
        return fragments if isinstance(fragments, list) else [fragments]

    def chat_stream(self, messages, option: Optional[Dict[str, Any]] = None, tools=None):
        """统一的流式输出接口，处理所有内容类型包括reasoning"""
        completion = self._create_completion(messages, option, stream=True, tools=tools)

        # 统一的流式处理，根据可用的工具处理器动态选择策略
        yield from self._unified_stream_processing(completion, messages)

    def _unified_stream_processing(self, completion, messages):
        """统一的流式处理方法，动态选择工具处理策略"""
        tool_call_fragments = []
        tool_calls_detected = False
        tool_calls_completed = False
        content_after_tool_calls = False  # 新增：标记工具调用后是否有内容

        for chunk in completion:
            # 检查并记录usage信息（通用支持）
            if hasattr(chunk, "usage") and chunk.usage:
                self._set_usage(chunk)
                logging.debug(f"Streaming usage received from {self.provider}: {chunk.usage}")

            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta

                # 检查工具调用 - 使用可用的工具处理器
                tool_calls_in_chunk = self._extract_tool_calls_from_chunk(chunk)
                if tool_calls_in_chunk:
                    # 如果工具调用已完成，但又检测到新的工具调用，重置状态
                    if tool_calls_completed:
                        # 处理之前遗留的片段
                        if tool_call_fragments:
                            remaining_calls = self._merge_tool_call_fragments(tool_call_fragments)
                            if remaining_calls:
                                logging.info(f"Processing {len(remaining_calls)} remaining tool calls before new batch")
                                # 发送工具调用请求消息
                                for request_msg in self._emit_tool_call_request(remaining_calls):
                                    yield request_msg
                                # 处理工具调用
                                if self._handle_tool_calls_in_stream(remaining_calls, messages):
                                    # 发送工具调用结果消息
                                    for result_msg in self._emit_tool_call_results(remaining_calls, messages):
                                        yield result_msg

                        # 重置状态开始新的工具调用批次
                        tool_call_fragments = []
                        tool_calls_detected = False
                        tool_calls_completed = False
                        content_after_tool_calls = False
                        logging.info("Reset tool call state for new batch")

                    tool_calls_detected = True
                    tool_call_fragments.extend(tool_calls_in_chunk)
                    continue

                # 注意：移除了中途处理工具调用的逻辑
                # 现在只收集片段，不在有内容时立即处理

                # 处理reasoning内容（DeepSeek R1等模型）
                if hasattr(delta, REASONING_CONTENT_ATTR) and getattr(delta, REASONING_CONTENT_ATTR):
                    reasoning_content = getattr(delta, REASONING_CONTENT_ATTR)
                    yield reasoning_content
                    continue

                # 处理普通内容
                if hasattr(delta, CONTENT_ATTR) and getattr(delta, CONTENT_ATTR):
                    content = getattr(delta, CONTENT_ATTR)
                    # 检查是否包含推理标记
                    if any(
                        marker in content for marker in ["<thinking>", "<think>", "<reasoning>", "思考：", "分析："]
                    ):
                        # 清理推理标记
                        display_content = content
                        for tag in ["<thinking>", "</thinking>", "<think>", "</think>", "<reasoning>", "</reasoning>"]:
                            display_content = display_content.replace(tag, "")
                        yield display_content
                        continue
                    # 普通内容
                    yield content
            else:
                self._set_usage(chunk)
                logging.debug("Chunk object does not have valid choices or delta content.")

        # 流式处理结束后，统一处理所有收集到的工具调用片段
        if tool_calls_detected and tool_call_fragments:
            tool_calls = self._merge_tool_call_fragments(tool_call_fragments)

            if tool_calls:  # 只有在有有效工具调用时才处理
                logging.info(f"Processing {len(tool_calls)} tool calls after stream completion")
                # 发送工具调用请求消息
                for request_msg in self._emit_tool_call_request(tool_calls):
                    yield request_msg

                if self._handle_tool_calls_in_stream(tool_calls, messages):
                    # 发送工具调用结果消息
                    for result_msg in self._emit_tool_call_results(tool_calls, messages):
                        yield result_msg
                    logging.info(f"Tool calls completed after stream: {len(tool_calls)} calls")

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
                logging.info(f"Tool calls detected in stream, assistant message appended: {assistant_msg}")
                return True
            else:
                logging.info(f"Tool calls detected in stream, but identical assistant message already exists, skipping")
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
            logging.info(f"Tongyi enable_search requested: {default_option[ENABLE_SEARCH_KEY]}")
            api_params["extra_body"] = {
                "extra_body": {ENABLE_SEARCH_KEY: default_option[ENABLE_SEARCH_KEY], "search_options": True}
            }

        try:
            completion = self.client.chat.completions.create(**api_params)
            return completion
        except Exception as e:
            logging.error(f"Error creating completion: {e}")
            raise


class OpenAI(ChatModel):
    def __init__(self, name="gpt-4o-mini", sk="", base_url="https://api.openai.com/v1"):
        super().__init__(
            name=name,
            sk=sk,
            base_url=base_url,
            provider="openai",
        )


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
