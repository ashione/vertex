import os
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import List, Optional

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.utils import factory_creator

logging = LoggerUtil.get_logger(__name__)

# 从环境变量中读取配置
API_KEY = os.getenv("DASHSCOPE_API_KEY")
MODEL_NAME = os.getenv("DASHSCOPE_MODEL_NAME", "text-embedding-v1")


# Abstract base class defining the interface for text embedding providers.
@factory_creator
class TextEmbeddingProvider(ABC):
    """
    文本嵌入服务抽象类，定义了获取文本嵌入向量的统一接口。
    """

    @abstractmethod
    def embedding(self, text: str) -> Optional[List[float]]:
        pass


# Class that implements the TextEmbeddingProvider abstract class to use the DashScope service for text embedding.
class DashScopeEmbedding(TextEmbeddingProvider):
    def __init__(self, api_key: str = API_KEY, model_name: str = MODEL_NAME):
        """
        初始化 DashScopeEmbedding 实例，配置 DashScope API key 和使用的模型名称。

        @param api_key: 从 DashScope 平台获取的 API key。
        @param model_name: 要使用的 DashScope 文本嵌入模型名称，默认为 "text-embedding-v1"。
        """
        self.api_key = api_key
        self.model_name = model_name

    def __get_state__(self):
        return {
            "class_name": self.__class__.__name__.lower(),
            "api_key": self.api_key,
            "model_name": self.model_name,
        }

    @lru_cache(maxsize=100)
    def embedding(self, text: str) -> Optional[List[float]]:
        """
        通过 DashScope 使用指定模型获取给定文本的嵌入向量，实现抽象类中定义的接口。

        @param text: 要获取嵌入向量的文本内容。
        @return: 对应于文本的嵌入向量（以浮点数列表形式），如果请求失败或发生异常则返回 None。
        """
        try:
            import dashscope
            dashscope.api_key = self.api_key
            response = dashscope.TextEmbedding.call(model=self.model_name, input=text)
            if response["status_code"] == 200:
                logging.debug(response)
                return response["output"]["embeddings"][0]["embedding"]
            else:
                # 记录请求失败的错误信息
                logging.error(f"请求失败。错误代码: {response['status_code']}，错误信息: {response['message']}")
                return None
        except ImportError:
            logging.error("请安装dashscope: pip install dashscope")
            return None
        except Exception as e:
            # 记录详细的异常信息
            logging.exception(f"发生异常: {e}")
            return None


# 定义 BCEEmbedding 类
class BCEEmbedding(TextEmbeddingProvider):
    def __init__(self, api_key: str, model_name: str, endpoint: str):
        """
        初始化 BCEEmbedding 实例，配置 BCE API key、模型名称和 endpoint。

        @param api_key: 从 BCE 平台获取的 API key。
        @param model_name: 要使用的 BCE 文本嵌入模型名称。
        @param endpoint: BCE 服务的 endpoint。
        """
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = endpoint
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    @lru_cache(maxsize=100)
    def embedding(self, text: str) -> Optional[List[float]]:
        """
        通过 BCE 使用指定模型获取给定文本的嵌入向量，实现抽象类中定义的接口。

        @param text: 要获取嵌入向量的文本内容。
        @return: 对应于文本的嵌入向量（以浮点数列表形式），如果请求失败或发生异常则返回 None。
        """
        try:
            import requests
            payload = {
                "model": self.model_name,
                "input": text,
                "encoding_format": "float",
            }

            response = requests.request("POST", self.endpoint, json=payload, headers=self._headers)
            if response.status_code == 200:
                response_data = response.json()
                logging.info(response_data)
                return response_data["data"][0]["embedding"]
            else:
                # 记录请求失败的错误信息
                logging.error(f"请求失败。错误代码: {response.status_code}，错误信息: {response.text}")
                return None
        except ImportError:
            logging.error("请安装requests: pip install requests")
            return None
        except Exception as e:
            # 记录详细的异常信息
            logging.exception(f"发生异常: {e}")
            return None


class LocalEmbeddingProvider(TextEmbeddingProvider):
    """本地嵌入提供者，使用sentence-transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化本地嵌入提供者
        
        Args:
            model_name: 使用的模型名称，默认为all-MiniLM-L6-v2
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logging.info(f"初始化本地嵌入模型: {model_name}")
        except ImportError:
            raise ImportError("请安装sentence-transformers: pip install sentence-transformers")
    
    def embedding(self, text: str) -> Optional[List[float]]:
        """
        生成文本嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量列表
        """
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logging.error(f"生成嵌入向量失败: {e}")
            return None
    
    def __get_state__(self):
        return {
            "class_name": self.__class__.__name__.lower(),
            "model_name": self.model_name,
        } 