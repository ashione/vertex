#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号插件 for Vertex Flow

这个插件允许用户通过微信公众号与部署在Google Cloud上的Vertex Flow聊天应用进行交互。

主要功能：
- 微信公众号消息接收和验证
- 与Vertex Flow Chat API集成
- 支持文本和图片消息处理
- 用户会话管理
- 多模态支持
- MCP和搜索功能集成
"""

__version__ = "1.0.0"
__author__ = "Vertex Flow Team"
__description__ = "微信公众号插件 for Vertex Flow"

from .config import config
from .message_processor import MessageProcessor
from .wechat_handler import WeChatHandler
from .wechat_server import app

__all__ = [
    "config",
    "MessageProcessor", 
    "WeChatHandler",
    "app"
]