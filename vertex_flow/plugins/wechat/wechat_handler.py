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
from wechat_crypto import WeChatCrypto


class WeChatHandler:
    """微信公众号消息处理器"""
    
    def __init__(self, token: str, encoding_aes_key: str = None, app_id: str = None, message_mode: str = 'compatible'):
        self.token = token
        self.app_id = app_id
        self.encoding_aes_key = encoding_aes_key
        self.message_mode = message_mode.lower()
        
        # 根据消息模式决定是否启用加密功能
        if self.message_mode == 'plaintext':
            # 明文模式：不使用加密
            self.crypto = None
        elif self.message_mode in ['compatible', 'secure']:
            # 兼容模式或安全模式：如果有密钥则初始化加密工具
            if encoding_aes_key and app_id:
                self.crypto = WeChatCrypto(token, encoding_aes_key, app_id)
            else:
                self.crypto = None
        else:
            self.crypto = None
        
        # 向后兼容的secure_mode属性
        self.secure_mode = (self.message_mode == 'secure')
    
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
        """解析XML消息"""
        try:
            root = ET.fromstring(xml_data)
            
            # 检查是否为加密消息
            encrypt_element = root.find('Encrypt')
            
            if encrypt_element is not None:
                # 消息是加密的
                if self.message_mode == 'plaintext':
                    # 明文模式不支持加密消息
                    raise ValueError("明文模式不支持加密消息")
                elif self.message_mode == 'secure':
                    # 安全模式必须解密
                    if not self.crypto:
                        raise ValueError("安全模式需要配置加密密钥")
                    encrypted_msg = encrypt_element.text
                    decrypted_xml = self.crypto.decrypt_message(encrypted_msg)
                    root = ET.fromstring(decrypted_xml)
                elif self.message_mode == 'compatible':
                    # 兼容模式：如果有加密工具则解密，否则报错
                    if self.crypto:
                        encrypted_msg = encrypt_element.text
                        decrypted_xml = self.crypto.decrypt_message(encrypted_msg)
                        root = ET.fromstring(decrypted_xml)
                    else:
                        raise ValueError("接收到加密消息但未配置解密密钥")
            else:
                # 消息是明文的
                if self.message_mode == 'secure':
                    # 安全模式不允许明文消息
                    raise ValueError("安全模式不允许明文消息")
            
            # 提取消息信息
            message_info = {}
            for child in root:
                message_info[child.tag] = child.text or ''
            
            return message_info
        except Exception as e:
            raise ValueError(f"XML消息解析失败: {str(e)}")
    
    def create_text_reply(self, to_user: str, from_user: str, content: str, timestamp: str = None, nonce: str = None) -> str:
        """创建文本回复消息"""
        if timestamp is None:
            timestamp = str(int(time.time()))
        
        # 创建明文回复XML
        reply_xml = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{timestamp}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
        
        # 根据消息模式决定是否加密
        if self.message_mode == 'plaintext':
            # 明文模式：直接返回明文
            return reply_xml
        elif self.message_mode == 'secure':
            # 安全模式：必须加密
            if not self.crypto:
                raise ValueError("安全模式需要配置加密密钥")
            if not (timestamp and nonce):
                raise ValueError("安全模式需要timestamp和nonce参数")
            try:
                success, encrypt_msg, signature, error = self.crypto.encrypt_message(reply_xml, timestamp, nonce)
                if success:
                    # 创建加密回复XML
                    encrypted_xml = f'''<xml>
<Encrypt><![CDATA[{encrypt_msg}]]></Encrypt>
<MsgSignature><![CDATA[{signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>'''
                    return encrypted_xml
                else:
                    raise ValueError(f"消息加密失败: {error}")
            except Exception as e:
                raise ValueError(f"消息加密失败: {str(e)}")
        elif self.message_mode == 'compatible':
            # 兼容模式：如果有加密工具且有必要参数则加密，否则返回明文
            if self.crypto and timestamp and nonce:
                try:
                    success, encrypt_msg, signature, error = self.crypto.encrypt_message(reply_xml, timestamp, nonce)
                    if success:
                        # 创建加密回复XML
                        encrypted_xml = f'''<xml>
<Encrypt><![CDATA[{encrypt_msg}]]></Encrypt>
<MsgSignature><![CDATA[{signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>'''
                        return encrypted_xml
                    else:
                        # 加密失败，返回明文
                        return reply_xml
                except Exception:
                    # 加密失败，返回明文
                    return reply_xml
            else:
                return reply_xml
        
        return reply_xml
    
    def create_image_reply(self, to_user: str, from_user: str, media_id: str, timestamp: str = None, nonce: str = None) -> str:
        """创建图片回复消息"""
        if timestamp is None:
            timestamp = str(int(time.time()))
        
        # 创建明文回复XML
        reply_xml = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{timestamp}</CreateTime>
<MsgType><![CDATA[image]]></MsgType>
<Image>
<MediaId><![CDATA[{media_id}]]></MediaId>
</Image>
</xml>"""
        
        # 根据消息模式决定是否加密
        if self.message_mode == 'plaintext':
            # 明文模式：直接返回明文
            return reply_xml
        elif self.message_mode == 'secure':
            # 安全模式：必须加密
            if not self.crypto:
                raise ValueError("安全模式需要配置加密密钥")
            if not (timestamp and nonce):
                raise ValueError("安全模式需要timestamp和nonce参数")
            try:
                encrypted_reply = self.crypto.encrypt_message(reply_xml, timestamp, nonce)
                return encrypted_reply
            except Exception as e:
                raise ValueError(f"图片回复加密失败: {str(e)}")
        elif self.message_mode == 'compatible':
            # 兼容模式：如果有加密工具且有必要参数则加密，否则返回明文
            if self.crypto and timestamp and nonce:
                try:
                    encrypted_reply = self.crypto.encrypt_message(reply_xml, timestamp, nonce)
                    return encrypted_reply
                except Exception:
                    # 加密失败，返回明文
                    return reply_xml
            else:
                return reply_xml
        
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