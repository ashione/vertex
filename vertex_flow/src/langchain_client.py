#!/usr/bin/env python3
"""
LangChain客户端实现
"""

from typing import Generator, List
from langchain_community.llms import Ollama
from langchain_core.callbacks import StreamingStdOutCallbackHandler
from chat_util import format_history

class LangChainClient:
    def __init__(self, host: str, model: str):
        self.llm = Ollama(
            model=model,
            base_url=host,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
    
    def generate(self, prompt: str, history: List[List[str]] = None) -> Generator[str, None, None]:
        full_prompt = format_history(history) + f"\n\nHuman: {prompt}\nAssistant: " if history else f"Human: {prompt}\nAssistant: "
        
        response = ""
        for chunk in self.llm.stream(full_prompt):
            response += chunk
            yield response