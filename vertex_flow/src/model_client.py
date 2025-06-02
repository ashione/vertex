#!/usr/bin/env python3
"""
通用模型API客户端实现
"""

from typing import Generator, List, Optional

from openai import OpenAI

from vertex_flow.utils.logger import get_logger

from .chat_util import format_history

logger = get_logger()


class ModelClient:
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, history: Optional[List[List[str]]] = None) -> Generator[str, None, None]:
        full_prompt = (
            format_history(history) + f"\n\nHuman: {prompt}\nAssistant: "
            if history
            else f"Human: {prompt}\nAssistant: "
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": full_prompt}],
                stream=True,
            )

            accumulated_response = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    accumulated_response += chunk.choices[0].delta.content
                    yield accumulated_response

        except Exception as e:
            logger.error(f"请求错误: {str(e)}")
            yield f"请求错误: {str(e)}"
