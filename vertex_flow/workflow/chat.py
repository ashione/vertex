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
from vertex_flow.workflow.utils import factory_creator, timer_decorator

logging = LoggerUtil.get_logger()


@factory_creator
class ChatModel(abc.ABC):
    """
    这是一个抽象基类示例。
    """

    def __init__(self, name: str, sk: str, base_url: str, provider: str):
        self.name = name
        self.sk = sk
        self.provider = provider
        self._usage = {}  # 存储最新的usage信息
        logging.info(f"Chat model : {self.name}, sk {self.sk}, provider = {self.provider}, base url {base_url}.")
        # 为序列化保存.
        self._base_url = base_url
        self.client = OpenAI(
            base_url=self._base_url,
            api_key=sk,
        )

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
                # 工具调用消息，保持原格式
                processed_messages.append(message)
            # 工具响应消息
            elif role == "tool":
                # 工具响应消息，保持原格式
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
            elif isinstance(content, str) or content is None:
                # 纯文本消息或空内容，保持原格式
                processed_messages.append(message)
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
        return api_params

    def _create_completion(self, messages, option: Optional[Dict[str, Any]] = None, stream: bool = False, tools=None):
        """Create completion with proper error handling"""
        api_params = self._build_api_params(messages, option, stream, tools)
        try:
            completion = self.client.chat.completions.create(**api_params)
            logging.info(f"show completion: {completion}")
            return completion
        except Exception as e:
            logging.error(f"Error creating completion: {e}")
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
        合并分片为一个标准的tool_call dict列表（只处理第一个tool_call）
        """
        tool_call = {"id": "", "function": {"name": "", "arguments": ""}, "type": "function"}
        for frag in fragments:
            # 支持对象或dict
            frag_dict = frag if isinstance(frag, dict) else getattr(frag, "__dict__", frag)
            if frag_dict.get("id"):
                tool_call["id"] = frag_dict["id"]
            if frag_dict.get("function"):
                func = frag_dict["function"]
                func_dict = func if isinstance(func, dict) else getattr(func, "__dict__", func)
                if func_dict.get("name"):
                    tool_call["function"]["name"] = func_dict["name"]
                if func_dict.get("arguments"):
                    tool_call["function"]["arguments"] += func_dict["arguments"]
            if frag_dict.get("type"):
                tool_call["type"] = frag_dict["type"]
        return [tool_call]

    def chat_stream(self, messages, option: Optional[Dict[str, Any]] = None, tools=None):
        """统一的流式输出接口，处理所有内容类型包括reasoning"""
        completion = self._create_completion(messages, option, stream=True, tools=tools)

        # 收集工具调用分片
        tool_call_fragments = []
        tool_calls_detected = False
        tool_calls_completed = False

        for chunk in completion:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta

                # 检查工具调用
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    tool_calls_detected = True
                    tool_call_fragments.extend(delta.tool_calls)
                    continue

                # 如果已经检测到工具调用，且分片收集结束（即遇到下一个非tool_calls分片），则补全assistant消息
                if tool_calls_detected and not tool_calls_completed:
                    # 拼接完整的assistant消息（转为标准dict）
                    tool_calls = self._merge_tool_call_fragments(tool_call_fragments)
                    assistant_msg = {"role": "assistant", "content": "", "tool_calls": tool_calls}

                    # 检查是否已经存在相同的assistant消息，避免重复添加
                    last_msg = messages[-1] if messages else None
                    if not (last_msg and last_msg.get("role") == "assistant" and last_msg.get("tool_calls")):
                        messages.append(assistant_msg)  # 关键：补全到messages
                        logging.info(f"Tool calls detected in stream, assistant message appended: {assistant_msg}")
                    else:
                        logging.info(
                            f"Tool calls detected in stream, but assistant message already exists, skipping duplicate"
                        )

                    tool_calls_completed = True
                    # 不break，继续处理后续内容

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

        # 流式处理结束后，检查是否有未处理的工具调用
        if tool_calls_detected and tool_call_fragments:
            # 确保工具调用已经被处理
            if not tool_calls_completed:
                tool_calls = self._merge_tool_call_fragments(tool_call_fragments)
                assistant_msg = {"role": "assistant", "content": "", "tool_calls": tool_calls}

                # 检查是否已经存在相同的assistant消息，避免重复添加
                last_msg = messages[-1] if messages else None
                if not (last_msg and last_msg.get("role") == "assistant" and last_msg.get("tool_calls")):
                    messages.append(assistant_msg)
                    logging.info(f"Tool calls completed after stream, assistant message appended: {assistant_msg}")
                else:
                    logging.info(
                        f"Tool calls completed after stream, but assistant message already exists, skipping duplicate"
                    )

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
