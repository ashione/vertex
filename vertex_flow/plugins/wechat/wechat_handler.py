#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号消息处理器
处理微信公众号的消息接收、验证和回复
支持明文模式和安全模式（加解密）
"""

import hashlib
import time
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple
from .wechat_crypto import WeChatCrypto


class WeChatHandler:
    """微信公众号消息处理器"""
    
    def __init__(self, token: str, encoding_aes_key: str = None, app_id: str = None):
        self.token = token
        self.app_id = app_id
        self.encoding_aes_key = encoding_aes_key
        
        # 如果提供了加密密钥，则启用安全模式
        self.secure_mode = bool(encoding_aes_key and app_id)
        if self.secure_mode:
            self.crypto = WeChatCrypto(token, encoding_aes_key, app_id)
        else:
            self.crypto = None
    
    def verify_signature(self, signature: str, timestamp: str, nonce: str, encrypt_msg: str = None) -> bool:
        """验证微信服务器签名"""
        try:
            if self.secure_mode and self.crypto:
                # 安全模式：使用加解密工具验证
                return self.crypto.verify_signature(signature, timestamp, nonce, encrypt_msg)
            else:
                # 明文模式：原有验证逻辑
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
            
            # 检查是否为加密消息
            encrypt_elem = root.find('Encrypt')
            if encrypt_elem is not None and self.secure_mode and self.crypto:
                # 安全模式：解密消息
                success, decrypted_xml, error = self.crypto.parse_encrypted_xml(xml_data)
                if success:
                    # 解析解密后的XML
                    decrypted_root = ET.fromstring(decrypted_xml)
                    for child in decrypted_root:
                        message[child.tag] = child.text
                else:
                    # 解密失败，记录错误
                    message['Error'] = error
            else:
                # 明文模式：直接解析
                for child in root:
                    message[child.tag] = child.text
            
            return message
        except Exception as e:
            return {'Error': f'解析XML失败: {str(e)}'}
    
    def create_text_reply(self, to_user: str, from_user: str, content: str, timestamp: str = None, nonce: str = None) -> str:
        """创建文本回复消息"""
        if timestamp is None:
            timestamp = str(int(time.time()))
        
        reply_xml = f"""
        <xml>
        <ToUserName><![CDATA[{to_user}]]></ToUserName>
        <FromUserName><![CDATA[{from_user}]]></FromUserName>
        <CreateTime>{timestamp}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{content}]]></Content>
        </xml>
        """.strip()
        
        # 如果是安全模式，需要加密回复
        if self.secure_mode and self.crypto and nonce:
            success, encrypted_xml, error = self.crypto.create_encrypted_response_xml(reply_xml, timestamp, nonce)
            if success:
                return encrypted_xml
            else:
                # 加密失败，返回错误信息（明文）
                error_xml = f"""
                <xml>
                <ToUserName><![CDATA[{to_user}]]></ToUserName>
                <FromUserName><![CDATA[{from_user}]]></FromUserName>
                <CreateTime>{timestamp}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[加密回复失败: {error}]]></Content>
                </xml>
                """.strip()
                return error_xml
        
        return reply_xml
    
    def create_image_reply(self, to_user: str, from_user: str, media_id: str, timestamp: str = None, nonce: str = None) -> str:
        """创建图片回复消息"""
        if timestamp is None:
            timestamp = str(int(time.time()))
        
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
        
        # 如果是安全模式，需要加密回复
        if self.secure_mode and self.crypto and nonce:
            success, encrypted_xml, error = self.crypto.create_encrypted_response_xml(reply_xml, timestamp, nonce)
            if success:
                return encrypted_xml
            else:
                # 加密失败，返回错误信息（明文）
                error_xml = f"""
                <xml>
                <ToUserName><![CDATA[{to_user}]]></ToUserName>
                <FromUserName><![CDATA[{from_user}]]></FromUserName>
                <CreateTime>{timestamp}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[加密回复失败: {error}]]></Content>
                </xml>
                """.strip()
                return error_xml
        
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