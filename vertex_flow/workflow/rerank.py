from abc import ABC, abstractmethod
from typing import List, Optional

import requests

from vertex_flow.utils.logger import LoggerUtil

logging = LoggerUtil.get_logger()


class RerankProvider(ABC):
    """
    重排序服务抽象类，定义了获取重排序结果的统一接口。
    """

    @abstractmethod
    def rerank(self, query: str, documents: List[str], top_n: int = 3) -> List[str]:
        pass


class BCERerankProvider(RerankProvider):
    def __init__(self, api_key: str, model_name: str, endpoint: str):
        """
        初始化 BCERerankProvider 实例，配置 BCE API key、模型名称和 endpoint。

        @param api_key: 从 BCE 平台获取的 API key。
        @param model_name: 要使用的 BCE 重排序模型名称。
        @param endpoint: BCE 服务的 endpoint。
        """
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = endpoint
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def rerank(self, query: str, documents: List[str], top_n: int = 3) -> List[str]:
        """
        通过 BCE 使用指定模型获取给定查询和文档的重排序结果，实现抽象类中定义的接口。

        @param query: 查询文本。
        @param documents: 待重排序的文档列表。
        @param top_n: 重排序结果的数量，默认为 3。
        @return: 重排序后的文档列表，如果请求失败或发生异常则返回 None。
        """
        try:
            data = {"query": query, "documents": documents}
            payload = {
                "model": self.model_name,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            }
            response = requests.request("POST", self.endpoint, json=payload, headers=self._headers)

            if response.status_code == 200:
                response_data = response.json()
                logging.info(response_data)
                return response_data["results"]
            else:
                # 记录请求失败的错误信息
                logging.error(
                    f"请求失败。错误代码: {
                        response.status_code}，错误信息: {
                        response.text}"
                )
                return None
        except Exception as e:
            # 记录详细的异常信息
            logging.exception(f"发生异常: {e}")
            return None
