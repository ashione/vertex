#!/usr/bin/env python3
"""
错误处理工具模块
提供统一的错误格式化和处理功能
"""

import re
from typing import Dict, Any, Optional
import requests


class ErrorHandler:
    """统一的错误处理工具类"""
    
    @staticmethod
    def format_api_error(
        service_name: str, 
        error: Exception, 
        response: Optional[requests.Response] = None
    ) -> Dict[str, Any]:
        """
        格式化API错误信息
        
        Args:
            service_name: 服务名称 (如 "OKX", "Binance")
            error: 异常对象
            response: HTTP响应对象 (可选)
            
        Returns:
            格式化的错误信息字典
        """
        error_info = {
            "error": True,
            "service": service_name,
            "type": type(error).__name__,
            "message": str(error)
        }
        
        if isinstance(error, requests.exceptions.RequestException):
            error_info["category"] = "network"
            
            if hasattr(error, 'response') and error.response is not None:
                response = error.response
                error_info["status_code"] = response.status_code
                
                # 根据状态码提供更友好的错误信息
                if response.status_code == 401:
                    error_info["user_message"] = "API密钥无效或已过期，请检查配置"
                elif response.status_code == 403:
                    error_info["user_message"] = "API权限不足，请检查API密钥权限设置"
                elif response.status_code == 429:
                    error_info["user_message"] = "请求频率过高，请稍后重试"
                elif response.status_code >= 500:
                    error_info["user_message"] = f"{service_name}服务器暂时不可用，请稍后重试"
                else:
                    error_info["user_message"] = f"{service_name}API请求失败 (状态码: {response.status_code})"
                
                # 处理响应内容
                content_type = response.headers.get('content-type', '').lower()
                if 'html' in content_type:
                    error_info["response_type"] = "html"
                    error_info["user_message"] += " - 服务器返回了错误页面"
                elif response.text:
                    error_info["response_type"] = "text"
                    # 只保留前100个字符的有用信息
                    clean_text = ErrorHandler._clean_error_text(response.text)
                    if clean_text:
                        error_info["response_preview"] = clean_text[:100]
            else:
                error_info["user_message"] = f"网络连接失败，无法访问{service_name}服务"
                
        elif "json" in str(error).lower() or "JSONDecodeError" in type(error).__name__:
            error_info["category"] = "parsing"
            error_info["user_message"] = f"{service_name}返回了无效的数据格式"
            
            if response:
                content_type = response.headers.get('content-type', '').lower()
                if 'html' in content_type:
                    error_info["user_message"] += " (服务器返回了HTML页面)"
                    
        else:
            error_info["category"] = "unknown"
            error_info["user_message"] = f"{service_name}服务出现未知错误"
        
        return error_info
    
    @staticmethod
    def _clean_error_text(text: str) -> str:
        """
        清理错误文本，移除HTML标签和多余的空白字符
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # 移除多余的空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # 如果文本太长，只保留开头部分
        if len(clean_text) > 200:
            clean_text = clean_text[:200] + "..."
        
        return clean_text
    
    @staticmethod
    def get_user_friendly_message(error_info: Dict[str, Any]) -> str:
        """
        获取用户友好的错误信息
        
        Args:
            error_info: 错误信息字典
            
        Returns:
            用户友好的错误消息
        """
        return error_info.get("user_message", error_info.get("message", "未知错误"))
    
    @staticmethod
    def is_retryable_error(error_info: Dict[str, Any]) -> bool:
        """
        判断错误是否可以重试
        
        Args:
            error_info: 错误信息字典
            
        Returns:
            是否可以重试
        """
        status_code = error_info.get("status_code")
        
        # 网络错误通常可以重试
        if error_info.get("category") == "network":
            # 401, 403 等认证错误不应该重试
            if status_code in [401, 403]:
                return False
            # 429 (频率限制) 可以重试，但需要等待
            # 5xx 服务器错误可以重试
            return status_code is None or status_code >= 429
        
        # 解析错误通常不需要重试
        if error_info.get("category") == "parsing":
            return False
        
        # 其他错误可以尝试重试
        return True
    
    @staticmethod
    def format_simple_error(service_name: str, message: str) -> Dict[str, Any]:
        """
        格式化简单错误信息
        
        Args:
            service_name: 服务名称
            message: 错误消息
            
        Returns:
            格式化的错误信息
        """
        return {
            "error": True,
            "service": service_name,
            "message": message,
            "user_message": message
        }