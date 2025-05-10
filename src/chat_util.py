#!/usr/bin/env python3
"""
通用工具函数
"""

from typing import List

def format_history(history: List[List[str]]) -> str:
    """将聊天历史格式化为单个提示"""
    formatted = ""
    for human, assistant in history:
        formatted += f"Human: {human}\nAssistant: {assistant}\n\n"
    return formatted.strip()