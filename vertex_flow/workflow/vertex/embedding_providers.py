import abc
import base64
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import requests

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.utils import factory_creator, retryable

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

    def supports_batch(self) -> bool:
        """是否支持批量嵌入，默认不支持，子类可覆盖"""
        return False

    def get_batch_size(self) -> int:
        """获取每批次的文档数量，默认返回 1，子类可覆盖"""
        return 1

    @abstractmethod
    def embedding(self, text: Union[str, List[str]]) -> Any:
        pass


# Class that implements the TextEmbeddingProvider abstract class to use the DashScope service for text embedding.
class DashScopeEmbedding(TextEmbeddingProvider):
    """DashScope 嵌入提供者"""

    def __init__(self, api_key: str, model_name: str = "text-embedding-v1", endpoint: str = "default"):
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = endpoint
        self.dimension = 1536  # DashScope 嵌入维度

    def supports_batch(self) -> bool:
        return True

    def get_batch_size(self) -> int:
        """DashScope 嵌入的默认批次大小，考虑到 API 限制和性能"""
        return 5

    def __get_state__(self):
        return {
            "class_name": self.__class__.__name__.lower(),
            "api_key": self.api_key,
            "model_name": self.model_name,
        }

    @lru_cache(maxsize=100)
    @retryable(
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
        exceptions=(requests.exceptions.RequestException,),
        retry_on_status_codes=[429, 500, 502, 503, 504],
        log_prefix="[DashScope] ",
    )
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
                # 创建一个模拟的 response 对象，包含 status_code 属性
                mock_response = type("MockResponse", (), {"status_code": response["status_code"]})()
                return mock_response

        except ImportError:
            logging.error("请安装dashscope: pip install dashscope")
            return None
        except Exception as e:
            # 记录详细的异常信息
            logging.exception(f"发生异常: {e}")
            raise


# 定义 BCEEmbedding 类
class BCEEmbedding(TextEmbeddingProvider):
    """BCE 嵌入提供者"""

    def __init__(
        self,
        api_key: str,
        endpoint: str = "https://api.siliconflow.cn/v1/embeddings",
        model_name: str = "netease-youdao/bce-embedding-base_v1",
        dimension: int = 768,
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model_name = model_name
        self.dimension = dimension  # BCE 嵌入维度
        self.max_tokens = 512  # BCE 最大 token 数
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def supports_batch(self) -> bool:
        return True

    def get_batch_size(self) -> int:
        """BCE 嵌入的默认批次大小，考虑到 token 限制和性能"""
        return 5

    def _truncate_text_to_tokens(self, text: str, max_tokens: int = 512) -> str:
        """
        将文本截断到指定的 token 数量

        Args:
            text: 输入文本
            max_tokens: 最大 token 数量，默认为 512

        Returns:
            截断后的文本
        """
        # 简单的 token 估算：按空格和标点符号分割
        # 这是一个粗略的估算，实际 token 数量可能不同
        tokens = re.findall(r"\b\w+\b|[^\w\s]", text)

        if len(tokens) <= max_tokens:
            return text

        # 如果 token 数量超过限制，截断文本
        logging.warning(f"文本 token 数量 ({len(tokens)}) 超过限制 ({max_tokens})，将进行截断")

        # 按字符截断，但尽量在词边界处截断
        char_count = 0
        for i, token in enumerate(tokens[:max_tokens]):
            char_count += len(token)
            if i < max_tokens - 1:
                char_count += 1  # 添加分隔符

        truncated_text = text[:char_count].strip()

        # 确保截断后的文本不以不完整的词结尾
        if truncated_text and not truncated_text.endswith((" ", ".", "!", "?", ",", ";", ":")):
            # 找到最后一个完整的词
            last_space = truncated_text.rfind(" ")
            if last_space > 0:
                truncated_text = truncated_text[:last_space].strip()

        logging.info(f"文本已截断: {len(text)} -> {len(truncated_text)} 字符")
        return truncated_text

    @lru_cache(maxsize=100)
    @retryable(
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
        exceptions=(requests.exceptions.RequestException,),
        retry_on_status_codes=[429, 500, 502, 503, 504],
        log_prefix="[BCE] ",
    )
    def embedding(self, text: str) -> Optional[List[float]]:
        """
        使用 BCE API 生成文本嵌入

        Args:
            text: 要嵌入的文本

        Returns:
            嵌入向量列表，失败时返回 None
        """
        # 截断文本到最大 token 数
        truncated_text = self._truncate_text_to_tokens(text, self.max_tokens)

        payload = {"model": self.model_name, "input": truncated_text}

        response = requests.request("POST", self.endpoint, json=payload, headers=self._headers)

        if response.status_code == 200:
            result = response.json()

            if "data" in result and len(result["data"]) > 0:
                embedding = result["data"][0]["embedding"]
                return embedding
            else:
                logging.error(f"BCE API 返回格式异常: {result}")
                return None
        else:
            # 记录请求失败的错误信息
            logging.error(f"BCE API 请求失败，状态码: {response.status_code}，响应: {response.text}")
            # 返回 response 对象，让装饰器处理重试
            return response

    def __get_state__(self):
        return {
            "class_name": self.__class__.__name__.lower(),
            "api_key": self.api_key,
            "endpoint": self.endpoint,
            "model_name": self.model_name,
        }


class LocalEmbeddingProvider(TextEmbeddingProvider):
    """本地嵌入提供者，使用 sentence-transformers"""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
        use_mirror: bool = True,
        mirror_url: str = "https://hf-mirror.com",
    ):
        self.model_name = model_name
        self.dimension = dimension
        self.use_mirror = use_mirror
        self.mirror_url = mirror_url
        self._model = None
        self._lock = threading.Lock()

        # 初始化模型
        self._initialize_model()

    def _initialize_model(self):
        """初始化 sentence-transformers 模型"""
        try:
            import os

            # 根据配置决定是否使用镜像源
            if self.use_mirror and self.mirror_url:
                original_endpoint = os.environ.get("HF_ENDPOINT", "")
                os.environ["HF_ENDPOINT"] = self.mirror_url
                logging.info(f"使用Hugging Face镜像源: {self.mirror_url}")
            elif self.use_mirror and not self.mirror_url:
                # 如果启用镜像但没有指定URL，使用默认镜像
                original_endpoint = os.environ.get("HF_ENDPOINT", "")
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                logging.info("使用默认Hugging Face镜像源: https://hf-mirror.com")
            else:
                logging.info("不使用镜像源，直接访问Hugging Face官方")

            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            logging.info(f"初始化本地嵌入模型: {self.model_name}")

        except ImportError:
            raise ImportError("请安装sentence-transformers: pip install sentence-transformers")
        except Exception as e:
            logging.error(f"初始化本地嵌入模型失败: {e}")
            raise

    def supports_batch(self) -> bool:
        return True

    def get_batch_size(self) -> int:
        """本地嵌入的默认批次大小，考虑到内存和性能"""
        return 10

    def embedding(self, text: str) -> Optional[List[float]]:
        """
        使用本地 sentence-transformers 模型生成文本嵌入

        Args:
            text: 要嵌入的文本

        Returns:
            嵌入向量列表，失败时返回 None
        """
        try:
            # 对输入文本进行编码异常处理
            safe_text = self._safe_encode_text(text)

            with self._lock:
                if self._model is None:
                    self._initialize_model()

                # 生成嵌入向量
                embedding = self._model.encode(safe_text, convert_to_tensor=False)
                return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)

        except Exception as e:
            logging.error(f"生成嵌入向量失败: {e}")
            return None

    def _safe_encode_text(self, text: str) -> str:
        """
        安全处理输入文本，避免编码异常

        Args:
            text: 原始文本

        Returns:
            处理后的安全文本
        """
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return ""

        try:
            # 尝试编码和解码，以确保文本可以安全处理
            text.encode("utf-8")
            return text
        except UnicodeEncodeError:
            # 如果编码失败，使用忽略错误的方式处理
            try:
                safe_bytes = text.encode("utf-8", errors="ignore")
                safe_text = safe_bytes.decode("utf-8")
                logging.warning("输入文本包含无法编码的字符，已忽略相关字符")
                return safe_text
            except Exception:
                logging.error("文本编码处理失败，返回空文本")
                return ""
        except Exception as e:
            logging.error(f"文本处理异常: {e}")
            return ""

    def __get_state__(self):
        return {
            "class_name": self.__class__.__name__.lower(),
            "model_name": self.model_name,
            "use_mirror": self.use_mirror,
            "mirror_url": self.mirror_url,
        }
