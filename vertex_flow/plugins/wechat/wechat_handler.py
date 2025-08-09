#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号消息处理器
处理微信公众号的消息接收、验证和回复
"""

import hashlib
import time
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple


class WeChatHandler:
    """微信公众号消息处理器"""
    
    def __init__(self, token: str):
        self.token = token
    
    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """验证微信服务器签名"""
        try:
            # 将token、timestamp、nonce三个参数进行字典序排序
            tmp_arr = [self.token, timestamp, nonce]
            tmp_arr.sort()
            tmp_str = ''.join(tmp_arr)
            
            # sha1加密
            sha1 = hashlib.sha1()
            sha1.update(tmp_str.encode('utf-8'))
            hashcode = sha1.hexdigest()
            
            # 验证签名
            return hashcode == signature
        except Exception:
            return False
    
    def parse_xml_message(self, xml_data: str) -> Dict[str, str]:
        """解析微信XML消息"""
        try:
            root = ET.fromstring(xml_data)
            message = {}
            
            for child in root:
                message[child.tag] = child.text
            
            return message
        except Exception:
            return {}
    
    def create_text_reply(self, to_user: str, from_user: str, content: str) -> str:
        """创建文本回复消息"""
        timestamp = int(time.time())
        
        reply_xml = f"""
        <xml>
        <ToUserName><![CDATA[{to_user}]]></ToUserName>
        <FromUserName><![CDATA[{from_user}]]></FromUserName>
        <CreateTime>{timestamp}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{content}]]></Content>
        </xml>
        """.strip()
        
        return reply_xml
    
    def create_image_reply(self, to_user: str, from_user: str, media_id: str) -> str:
        """创建图片回复消息"""
        timestamp = int(time.time())
        
        reply_xml = f"""
        <xml>
        <ToUserName><![CDATA[{to_user}]]></ToUserName>
        <FromUserName><![CDATA[{from_user}]]></FromUserName>
        <CreateTime>{timestamp}</CreateTime>
        <MsgType><![CDATA[image]]></MsgType>
        <Image>
        <MediaId><![CDATA[{media_id}]]></MediaId>
        </Image>
        </xml>
        """.strip()
        
        return reply_xml
    
    def extract_message_info(self, message: Dict[str, str]) -> Tuple[str, str, str, str]:
        """提取消息信息"""
        to_user = message.get('ToUserName', '')
        from_user = message.get('FromUserName', '')
        msg_type = message.get('MsgType', '')
        content = message.get('Content', '')
        
        return to_user, from_user, msg_type, content
    
    def is_supported_message_type(self, msg_type: str) -> bool:
        """检查是否支持的消息类型"""
        supported_types = ['text', 'image', 'voice']
        return msg_type in supported_types