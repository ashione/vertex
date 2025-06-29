#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词模板基类

提供通用的提示词管理功能，包括格式化、验证和缓存等。
"""

import re
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class BasePromptTemplate(ABC):
    """提示词模板基类"""
    
    def __init__(self):
        self._cache = {}
    
    @abstractmethod
    def get_prompt_names(self) -> List[str]:
        """获取所有可用的提示词名称"""
        pass
    
    @abstractmethod
    def get_prompt_types(self) -> List[str]:
        """获取所有可用的提示词类型"""
        pass
    
    def format_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """
        格式化提示词模板
        
        Args:
            template: 提示词模板
            variables: 变量字典
            
        Returns:
            格式化后的提示词
        """
        if not variables:
            return template
            
        # 使用简单的字符串替换
        result = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        return result
    
    def validate_variables(self, template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证变量是否完整
        
        Args:
            template: 提示词模板
            variables: 变量字典
            
        Returns:
            验证结果，包含缺失的变量
        """
        # 提取模板中的所有变量占位符
        pattern = r'\{\{(\w+)\}\}'
        required_vars = set(re.findall(pattern, template))
        
        # 检查提供的变量
        provided_vars = set(variables.keys())
        missing_vars = required_vars - provided_vars
        
        return {
            "required": list(required_vars),
            "provided": list(provided_vars),
            "missing": list(missing_vars),
            "is_complete": len(missing_vars) == 0
        }
    
    def get_cached_prompt(self, key: str) -> Optional[str]:
        """获取缓存的提示词"""
        return self._cache.get(key)
    
    def cache_prompt(self, key: str, prompt: str):
        """缓存提示词"""
        self._cache[key] = prompt
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
    
    def get_prompt_methods(self) -> Dict[str, str]:
        """
        获取所有提示词方法
        
        Returns:
            方法名到提示词内容的映射
        """
        methods = {}
        for method_name in dir(self):
            if method_name.startswith('get_') and method_name.endswith('_prompt'):
                if callable(getattr(self, method_name)):
                    try:
                        prompt = getattr(self, method_name)()
                        methods[method_name] = prompt
                    except Exception:
                        continue
        return methods
    
    def list_available_prompts(self) -> Dict[str, List[str]]:
        """
        列出所有可用的提示词
        
        Returns:
            按类型分组的提示词列表
        """
        methods = self.get_prompt_methods()
        prompts_by_type = {}
        
        for method_name, prompt in methods.items():
            # 解析方法名: get_{name}_{type}_prompt
            parts = method_name.replace('get_', '').replace('_prompt', '').split('_')
            if len(parts) >= 2:
                prompt_type = parts[-1]  # 最后一个部分是类型
                prompt_name = '_'.join(parts[:-1])  # 前面的是名称
                
                if prompt_type not in prompts_by_type:
                    prompts_by_type[prompt_type] = []
                prompts_by_type[prompt_type].append(prompt_name)
        
        return prompts_by_type 