#!/usr/bin/env python3
"""
通用日志工具模块
"""

import logging
from typing import Optional
import sys

def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_str: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    file_path: Optional[str] = None
) -> logging.Logger:
    """
    配置并返回一个logger实例
    
    参数:
        name: logger名称
        level: 日志级别 (默认: logging.INFO)
        format_str: 日志格式字符串
        file_path: 日志文件路径 (如果不提供则只输出到控制台)
    
    返回:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(format_str)
    
    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件handler (如果提供了文件路径)
    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """
    获取一个logger实例
    
    参数:
        name: logger名称 (如果不提供则返回root logger)
    
    返回:
        Logger实例
    """
    return logging.getLogger(name)