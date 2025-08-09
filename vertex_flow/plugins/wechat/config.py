#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号插件配置管理
"""

import os
from typing import Optional
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class WeChatConfig:
    """微信公众号配置类"""
    
    def __init__(self):
        # 微信公众号基础配置
        self.wechat_token = os.getenv('WECHAT_TOKEN', '')
        self.wechat_app_id = os.getenv('WECHAT_APP_ID', '')
        self.wechat_app_secret = os.getenv('WECHAT_APP_SECRET', '')
        self.wechat_encoding_aes_key = os.getenv('WECHAT_ENCODING_AES_KEY', '')
        
        # 微信消息处理模式
        self.wechat_message_mode = os.getenv('WECHAT_MESSAGE_MODE', 'compatible').lower()
        if self.wechat_message_mode not in ['plaintext', 'compatible', 'secure']:
            self.wechat_message_mode = 'compatible'
        
        # Vertex Flow API配置
        self.vertex_flow_api_url = os.getenv('VERTEX_FLOW_API_URL', 'http://localhost:8000')
        self.default_workflow = os.getenv('DEFAULT_WORKFLOW', 'default_chat')
        
        # 服务器配置
        self.server_host = os.getenv('SERVER_HOST', '0.0.0.0')
        self.server_port = int(os.getenv('SERVER_PORT', '8001'))
        
        # 功能开关
        self.enable_mcp = os.getenv('ENABLE_MCP', 'true').lower() == 'true'
        self.enable_search = os.getenv('ENABLE_SEARCH', 'true').lower() == 'true'
        self.enable_multimodal = os.getenv('ENABLE_MULTIMODAL', 'true').lower() == 'true'
        self.enable_reasoning = os.getenv('ENABLE_REASONING', 'false').lower() == 'true'
        
        # 消息处理配置
        self.max_message_length = int(os.getenv('MAX_MESSAGE_LENGTH', '2000'))
        self.session_timeout = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1小时
        
        # 日志配置
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # 部署相关配置
        self.domain = os.getenv('DOMAIN', '')
        self.ssl_cert_path = os.getenv('SSL_CERT_PATH', '')
        self.ssl_key_path = os.getenv('SSL_KEY_PATH', '')
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """验证配置是否完整"""
        if not self.wechat_token:
            return False, "WECHAT_TOKEN 未设置"
        
        if not self.vertex_flow_api_url:
            return False, "VERTEX_FLOW_API_URL 未设置"
        
        # 验证安全模式配置
        if self.wechat_message_mode == 'secure':
            if not self.wechat_encoding_aes_key:
                return False, "安全模式需要设置 WECHAT_ENCODING_AES_KEY"
            if not self.wechat_app_id:
                return False, "安全模式需要设置 WECHAT_APP_ID"
        
        return True, None
    
    def get_webhook_url(self) -> str:
        """获取微信webhook URL"""
        if self.domain:
            protocol = 'https' if self.ssl_cert_path else 'http'
            return f"{protocol}://{self.domain}/wechat"
        else:
            return f"http://{self.server_host}:{self.server_port}/wechat"
    
    def __str__(self) -> str:
        """配置信息字符串表示（隐藏敏感信息）"""
        return f"""
WeChatConfig:
  - WECHAT_TOKEN: {'已设置' if self.wechat_token else '未设置'}
  - WECHAT_APP_ID: {'已设置' if self.wechat_app_id else '未设置'}
  - WECHAT_MESSAGE_MODE: {self.wechat_message_mode}
  - WECHAT_ENCODING_AES_KEY: {'已设置' if self.wechat_encoding_aes_key else '未设置'}
  - VERTEX_FLOW_API_URL: {self.vertex_flow_api_url}
  - DEFAULT_WORKFLOW: {self.default_workflow}
  - SERVER: {self.server_host}:{self.server_port}
  - ENABLE_MCP: {self.enable_mcp}
  - ENABLE_SEARCH: {self.enable_search}
  - ENABLE_MULTIMODAL: {self.enable_multimodal}
  - WEBHOOK_URL: {self.get_webhook_url()}
"""


# 全局配置实例
config = WeChatConfig()