#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号消息加解密工具
实现微信公众号安全模式的AES加解密功能
"""

import base64
import hashlib
import random
import string
import struct
import xml.etree.ElementTree as ET
from typing import Optional, Tuple

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class WeChatCrypto:
    """微信公众号消息加解密类"""

    def __init__(self, token: str, encoding_aes_key: str, app_id: str):
        """
        初始化加解密工具

        Args:
            token: 微信公众号Token
            encoding_aes_key: 43位字符的AES密钥
            app_id: 微信公众号AppID
        """
        self.token = token
        self.app_id = app_id

        # 将43位密钥转换为32位AES密钥
        if len(encoding_aes_key) == 43:
            self.aes_key = base64.b64decode(encoding_aes_key + "=")
        else:
            raise ValueError("EncodingAESKey必须是43位字符")

    def verify_signature(self, signature: str, timestamp: str, nonce: str, encrypt_msg: str = None) -> bool:
        """
        验证微信服务器签名（安全模式）

        Args:
            signature: 微信签名
            timestamp: 时间戳
            nonce: 随机数
            encrypt_msg: 加密消息（安全模式下需要）

        Returns:
            bool: 验证结果
        """
        try:
            # 安全模式下需要包含encrypt_msg
            if encrypt_msg:
                tmp_arr = [self.token, timestamp, nonce, encrypt_msg]
            else:
                tmp_arr = [self.token, timestamp, nonce]

            tmp_arr.sort()
            tmp_str = "".join(tmp_arr)

            # sha1加密
            sha1 = hashlib.sha1()
            sha1.update(tmp_str.encode("utf-8"))
            hashcode = sha1.hexdigest()

            return hashcode == signature
        except Exception:
            return False

    def decrypt_message(self, encrypt_msg: str) -> Tuple[bool, str, str]:
        """
        解密微信消息

        Args:
            encrypt_msg: 加密的消息内容

        Returns:
            Tuple[bool, str, str]: (是否成功, 解密后的消息, 错误信息)
        """
        try:
            # Base64解码
            cipher_data = base64.b64decode(encrypt_msg)

            # AES解密
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            decrypted = cipher.decrypt(cipher_data)

            # 去除PKCS7填充
            try:
                decrypted = unpad(decrypted, AES.block_size)
            except ValueError:
                # 如果unpad失败，尝试手动去除填充
                pad_len = decrypted[-1]
                if isinstance(pad_len, str):
                    pad_len = ord(pad_len)
                decrypted = decrypted[:-pad_len]

            # 解析消息结构：random(16) + msg_len(4) + msg + app_id
            random_bytes = decrypted[:16]
            msg_len = struct.unpack("!I", decrypted[16:20])[0]
            msg = decrypted[20 : 20 + msg_len].decode("utf-8")
            app_id = decrypted[20 + msg_len :].decode("utf-8")

            # 验证AppID
            if app_id != self.app_id:
                return False, "", f"AppID不匹配: 期望{self.app_id}, 实际{app_id}"

            return True, msg, ""

        except Exception as e:
            return False, "", f"解密失败: {str(e)}"

    def encrypt_message(self, msg: str, timestamp: str, nonce: str) -> Tuple[bool, str, str, str]:
        """
        加密微信消息

        Args:
            msg: 要加密的消息内容
            timestamp: 时间戳
            nonce: 随机数

        Returns:
            Tuple[bool, str, str, str]: (是否成功, 加密消息, 签名, 错误信息)
        """
        try:
            # 生成16位随机字符串
            random_str = "".join(random.choices(string.ascii_letters + string.digits, k=16))

            # 构造消息结构：random(16) + msg_len(4) + msg + app_id
            msg_bytes = msg.encode("utf-8")
            app_id_bytes = self.app_id.encode("utf-8")
            msg_len = struct.pack("!I", len(msg_bytes))

            plain_text = random_str.encode("utf-8") + msg_len + msg_bytes + app_id_bytes

            # PKCS7填充
            padded_text = pad(plain_text, AES.block_size)

            # AES加密
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            encrypted = cipher.encrypt(padded_text)

            # Base64编码
            encrypt_msg = base64.b64encode(encrypted).decode("utf-8")

            # 生成签名
            tmp_arr = [self.token, timestamp, nonce, encrypt_msg]
            tmp_arr.sort()
            tmp_str = "".join(tmp_arr)

            sha1 = hashlib.sha1()
            sha1.update(tmp_str.encode("utf-8"))
            signature = sha1.hexdigest()

            return True, encrypt_msg, signature, ""

        except Exception as e:
            return False, "", "", f"加密失败: {str(e)}"

    def parse_encrypted_xml(self, xml_data: str) -> Tuple[bool, str, str]:
        """
        解析加密的XML消息

        Args:
            xml_data: 加密的XML数据

        Returns:
            Tuple[bool, str, str]: (是否成功, 解密后的消息XML, 错误信息)
        """
        try:
            root = ET.fromstring(xml_data)
            encrypt_elem = root.find("Encrypt")

            if encrypt_elem is None:
                return False, "", "未找到Encrypt元素"

            encrypt_msg = encrypt_elem.text
            if not encrypt_msg:
                return False, "", "Encrypt元素为空"

            # 解密消息
            success, decrypted_msg, error = self.decrypt_message(encrypt_msg)
            if not success:
                return False, "", error

            return True, decrypted_msg, ""

        except Exception as e:
            return False, "", f"解析XML失败: {str(e)}"

    def create_encrypted_response_xml(self, msg: str, timestamp: str, nonce: str) -> Tuple[bool, str, str]:
        """
        创建加密的响应XML

        Args:
            msg: 响应消息内容
            timestamp: 时间戳
            nonce: 随机数

        Returns:
            Tuple[bool, str, str]: (是否成功, 加密的XML响应, 错误信息)
        """
        try:
            # 加密消息
            success, encrypt_msg, signature, error = self.encrypt_message(msg, timestamp, nonce)
            if not success:
                return False, "", error

            # 构造XML响应
            xml_response = f"""<xml>
<Encrypt><![CDATA[{encrypt_msg}]]></Encrypt>
<MsgSignature><![CDATA[{signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""

            return True, xml_response, ""

        except Exception as e:
            return False, "", f"创建加密响应失败: {str(e)}"


def generate_aes_key() -> str:
    """
    生成43位的AES密钥

    Returns:
        str: 43位的AES密钥
    """
    # 生成32字节的随机数据
    random_bytes = bytes([random.randint(0, 255) for _ in range(32)])
    # Base64编码并去掉末尾的'='
    return base64.b64encode(random_bytes).decode("utf-8")[:-1]


if __name__ == "__main__":
    # 测试用例
    print("生成AES密钥示例:")
    print(generate_aes_key())
