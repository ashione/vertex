#!/usr/bin/env python3
"""
原生Ollama客户端实现
"""

import json
from typing import Any, Dict, Generator, List

import requests

from vertex_flow.utils.logger import get_logger

logger = get_logger()


class OllamaClient:
    def __init__(self, host: str, model: str):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/generate"

    def check_connection(self) -> bool:
        """检查与Ollama服务的连接"""
        try:
            response = requests.get(f"{self.host}/api/tags")
            return response.status_code == 200
        except requests.RequestException:
            return False

    def generate(self, prompt: str, system: str = None, context: List[int] = None) -> Generator[str, None, None]:
        """生成文本"""
        data = {"model": self.model, "prompt": prompt, "stream": True}

        if system:
            data["system"] = system

        if context:
            data["context"] = context

        try:
            response = requests.post(
                self.api_url,
                json=data,
                stream=True,
                timeout=30,
                headers={},  # 确保不发送任何认证头
            )

            if response.status_code != 200:
                logger.warning(f"错误: 状态码 {response.status_code} - {response.text}")
                yield f"错误: 状态码 {response.status_code} - {response.text}"
                return
        except requests.RequestException as e:
            logger.error(f"错误: 状态码 {response.status_code} - {response.text}, {str(e)}")
            yield f"请求错误: {str(e)}"
            return

        response_text = ""
        context = None

        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    response_text += chunk.get("response", "")
                    if "context" in chunk:
                        context = chunk["context"]
                    yield response_text
                except json.JSONDecodeError:
                    yield f"错误: 无法解析JSON响应: {line}"

        return context
