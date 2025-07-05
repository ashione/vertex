#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词管理包

本包包含各种工作流和功能的提示词模板，用于统一管理和优化提示词。
提供统一的提示词获取和格式化接口。
"""

from typing import Any, Dict, Optional

from .base import BasePromptTemplate
from .deep_research import DeepResearchPrompts

# 导入所有提示词模板类
__all__ = ["BasePromptTemplate", "DeepResearchPrompts", "PromptManager", "get_prompt", "format_prompt"]


class PromptManager:
    """统一的提示词管理器"""

    def __init__(self):
        self.prompts = {
            "deep_research": DeepResearchPrompts(),
        }

    def get_prompt(self, category: str, prompt_type: str, prompt_name: str) -> Optional[str]:
        """
        获取指定类别的提示词

        Args:
            category: 提示词类别 (如 'deep_research')
            prompt_type: 提示词类型 (如 'system', 'user')
            prompt_name: 提示词名称 (如 'topic_analysis')

        Returns:
            提示词内容或None
        """
        if category not in self.prompts:
            return None

        prompt_class = self.prompts[category]
        method_name = f"get_{prompt_name}_{prompt_type}_prompt"

        if hasattr(prompt_class, method_name):
            return getattr(prompt_class, method_name)()

        return None

    def format_prompt(
        self, category: str, prompt_type: str, prompt_name: str, variables: Dict[str, Any]
    ) -> Optional[str]:
        """
        获取并格式化提示词

        Args:
            category: 提示词类别
            prompt_type: 提示词类型
            prompt_name: 提示词名称
            variables: 变量字典

        Returns:
            格式化后的提示词或None
        """
        prompt = self.get_prompt(category, prompt_type, prompt_name)
        if prompt:
            return DeepResearchPrompts.format_prompt(prompt, variables)
        return None


# 全局提示词管理器实例
_prompt_manager = PromptManager()


def get_prompt(category: str, prompt_type: str, prompt_name: str) -> Optional[str]:
    """
    获取提示词的便捷函数

    Args:
        category: 提示词类别
        prompt_type: 提示词类型
        prompt_name: 提示词名称

    Returns:
        提示词内容或None
    """
    return _prompt_manager.get_prompt(category, prompt_type, prompt_name)


def format_prompt(category: str, prompt_type: str, prompt_name: str, variables: Dict[str, Any]) -> Optional[str]:
    """
    格式化提示词的便捷函数

    Args:
        category: 提示词类别
        prompt_type: 提示词类型
        prompt_name: 提示词名称
        variables: 变量字典

    Returns:
        格式化后的提示词或None
    """
    return _prompt_manager.format_prompt(category, prompt_type, prompt_name, variables)
