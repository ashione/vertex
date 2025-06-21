import abc
import base64
import requests
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI
from openai.types.chat.chat_completion import Choice

from vertex_flow.utils.logger import LoggerUtil
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
            
            if isinstance(message.get("content"), list):
                # 多模态消息格式
                processed_content = []
                for content_item in message["content"]:
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
                processed_messages.append({
                    "role": message["role"],
                    "content": processed_content
                })
            elif isinstance(message.get("content"), str):
                # 纯文本消息，保持原格式
                processed_messages.append(message)
            else:
                # 其他格式，尝试转换为文本
                logging.warning(f"Unknown message format: {message}")
                processed_messages.append(message)
        
        logging.debug(f"Processed messages: {processed_messages}")
        return processed_messages

    def _create_completion(self, messages, option: Optional[Dict[str, Any]] = None, stream: bool = False, tools=None):
        """Create completion with proper error handling"""
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
        filtered_option = {k: v for k, v in default_option.items() 
                          if k not in ["show_reasoning", "enable_reasoning"]}
        api_params = {"model": self.name, "messages": processed_messages, **filtered_option}
        if tools is not None and len(tools) > 0:
            api_params["tools"] = tools
        
        try:
            completion = self.client.chat.completions.create(**api_params)
            return completion
        except Exception as e:
            logging.error(f"Error creating completion: {e}")
            raise

    def chat(self, messages, option: Optional[Dict[str, Any]] = None, tools=None) -> Choice:
        completion = self._create_completion(messages, option, stream=False, tools=tools)
        return completion.choices[0]

    def chat_stream(self, messages, option: Optional[Dict[str, Any]] = None, tools=None):
        completion = self._create_completion(messages, option, stream=True, tools=tools)
        for chunk in completion:
            # 确保 chunk 对象具有 choices 属性，并正确处理增量更新内容
            if hasattr(chunk, "choices") and len(chunk.choices) > 0 and chunk.choices[0].delta:
                content = chunk.choices[0].delta.content
                if content is not None:  # 只yield非None的内容
                    yield content
            else:
                logging.debug("Chunk object does not have valid choices or delta content.")

    def chat_stream_with_reasoning(self, messages, option: Optional[Dict[str, Any]] = None):
        """
        Enhanced chat stream method with reasoning support
        
        For DeepSeek R1 models, reasoning content is automatically returned in the response
        without needing special parameters in the request.
        """
        try:
            # Create completion without reasoning parameter
            tools = option.get("tools") if option else None
            completion = self._create_completion(messages, option, stream=True, tools=tools)
            
            reasoning_buffer = ""
            content_buffer = ""
            is_reasoning_phase = True
            
            for chunk in completion:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    # Check for reasoning content (DeepSeek R1 models)
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning_buffer += delta.reasoning_content
                        if option and option.get("show_reasoning", True):
                            yield f"{delta.reasoning_content}"
                        continue
                    
                    # Regular content
                    if hasattr(delta, 'content') and delta.content:
                        # If we were in reasoning phase and now have content, add separator
                        if is_reasoning_phase and reasoning_buffer and option and option.get("show_reasoning", True):
                            yield "\n\n💭 **回答：**\n"
                            is_reasoning_phase = False
                        
                        content_buffer += delta.content
                        yield delta.content
                        
            # Log the complete reasoning and content for debugging
            if reasoning_buffer:
                logging.info(f"Reasoning length: {len(reasoning_buffer)} chars")
            if content_buffer:
                logging.info(f"Content length: {len(content_buffer)} chars")
                
        except Exception as e:
            logging.error(f"Error in chat_stream_with_reasoning: {e}")
            # Fallback to regular streaming
            logging.info("Falling back to regular chat streaming")
            for chunk in self.chat_stream(messages, option):
                yield chunk

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
    def __init__(self, name="deepseek-chat", sk=""):
        super().__init__(name=name, sk=sk, base_url="https://api.deepseek.com", provider="deepseek")


class Tongyi(ChatModel):
    def __init__(self, name="qwen-max", sk=""):
        super().__init__(
            name=name,
            sk=sk,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            provider="tongyi",
        )


class OpenRouter(ChatModel):
    def __init__(self, name="openrouter-chat", sk=""):
        super().__init__(
            name=name,
            sk=sk,
            base_url="https://openrouter.ai/api/v1",
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
