import abc
from typing import Any, Dict

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

    def _create_completion(self, messages, option: Dict[str, Any] = None, stream: bool = False, tools=None) -> Choice:
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
        # 构建API调用参数
        api_params = {"model": self.name, "messages": messages, **default_option}
        if tools is not None and len(tools) > 0:
            api_params["tools"] = tools

        completion = self.client.chat.completions.create(**api_params)
        return completion

    def chat(self, messages, option: Dict[str, Any] = None, tools=None) -> Choice:
        completion = self._create_completion(messages, option, stream=False, tools=tools)
        return completion.choices[0]

    def chat_stream(self, messages, option: Dict[str, Any] = None, tools=None):
        completion = self._create_completion(messages, option, stream=True, tools=tools)
        for chunk in completion:
            # 确保 chunk 对象具有 choices 属性，并正确处理增量更新内容
            if hasattr(chunk, "choices") and chunk.choices[0].delta:
                yield chunk.choices[0].delta.content
            else:
                logging.error("Chunk object does not have 'choices' attribute or delta is missing.")

    def model_name(self) -> str:
        return self.name

    def __str__(self):
        return self.model_name()

    # search 工具的具体实现，这里我们只需要返回参数即可
    def search_impl(self, arguments: Dict[str, Any]) -> Any:
        """
        但如果你想使用其他模型，并保留联网搜索的功能，那你只需要修改这里的实现（例如调用搜索
        和获取网页内容等），函数签名不变，依然是 work 的。

        这最大程度保证了兼容性，允许你在不同的模型间切换，并且不需要对代码有破坏性的修改。
        """
        return arguments


class MoonshotChat(ChatModel):
    def __init__(
        self,
        name="moonshot-v1-128k",
        sk="",
    ):
        super().__init__(name=name, sk=sk, base_url="https://api.moonshot.cn/v1", provider="moonshot")

    @timer_decorator
    def chat(self, messages, option: Dict[str, Any] = None, tools: list = None) -> Choice:
        completion = self.client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages,
            temperature=0.8,
            stream=True,
            tools=[
                {
                    "type": "builtin_function",
                    "function": {
                        "name": "$web_search",
                    },
                }
            ],
        )
        for chunk in completion:
            # 确保正确处理生成器对象的内容
            yield chunk.choices[0].delta.content if chunk.choices[0].delta else ""


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
