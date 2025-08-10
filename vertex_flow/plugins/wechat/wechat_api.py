#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号API客户端
处理access_token获取和客服消息发送
"""

import asyncio
import logging
import time
from typing import Dict, Optional

import aiohttp

try:
    from .config import config
except ImportError:
    from config import config


class WeChatAPI:
    """微信公众号API客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self.token_expires_at = 0
        self.logger = logging.getLogger(__name__)

        # 微信API基础URL
        self.base_url = "https://api.weixin.qq.com/cgi-bin"

    async def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """获取access_token

        Args:
            force_refresh: 是否强制刷新token

        Returns:
            access_token字符串，失败返回None
        """
        current_time = time.time()

        # 如果token还有效且不强制刷新，直接返回
        if not force_refresh and self.access_token and current_time < self.token_expires_at - 300:  # 提前5分钟刷新
            return self.access_token

        try:
            url = f"{self.base_url}/token"
            params = {"grant_type": "client_credential", "appid": self.app_id, "secret": self.app_secret}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()

                        if "access_token" in data:
                            self.access_token = data["access_token"]
                            expires_in = data.get("expires_in", 7200)  # 默认2小时
                            self.token_expires_at = current_time + expires_in

                            self.logger.info(f"获取access_token成功，APPID: {self.app_id}，有效期: {expires_in}秒")
                            return self.access_token
                        else:
                            error_code = data.get("errcode", "unknown")
                            error_msg = data.get("errmsg", "unknown error")
                            self.logger.error(f"获取access_token失败: {error_code} - {error_msg}")
                            return None
                    else:
                        self.logger.error(f"获取access_token请求失败，状态码: {response.status}")
                        return None

        except Exception as e:
            self.logger.error(f"获取access_token异常: {str(e)}")
            return None

    async def send_customer_service_message(self, openid: str, message: str, msg_type: str = "text") -> bool:
        """发送客服消息

        Args:
            openid: 用户的openid
            message: 消息内容
            msg_type: 消息类型，默认为text

        Returns:
            发送成功返回True，失败返回False
        """
        access_token = await self.get_access_token()
        if not access_token:
            self.logger.error("无法获取access_token，客服消息发送失败")
            return False

        try:
            url = f"{self.base_url}/message/custom/send"
            params = {"access_token": access_token}

            # 构造消息数据
            if msg_type == "text":
                data = {"touser": openid, "msgtype": "text", "text": {"content": message}}
            else:
                self.logger.error(f"不支持的消息类型: {msg_type}")
                return False

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, params=params, json=data, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        if result.get("errcode") == 0:
                            self.logger.info(f"客服消息发送成功: {openid}")
                            return True
                        else:
                            error_code = result.get("errcode", "unknown")
                            error_msg = result.get("errmsg", "unknown error")
                            rid = result.get("rid", "no-rid")

                            # 48001错误的详细排查信息
                            if error_code == 48001:
                                self.logger.error(f"客服消息发送失败 - 48001权限错误:")
                                self.logger.error(f"  错误信息: {error_msg}")
                                self.logger.error(f"  请求ID: {rid}")
                                self.logger.error(f"  使用的APPID: {self.app_id}")
                                self.logger.error(f"  排查建议:")
                                self.logger.error(f"    1. 检查公众号后台 → 开发 → 接口权限 → 客服消息是否已获得")
                                self.logger.error(f"    2. 确认APPID/APPSECRET是否匹配当前公众号")
                                self.logger.error(f"    3. 如果是测试号，确认用户已加为体验者")
                                self.logger.error(f"    4. 未认证订阅号通常无客服消息权限")
                            else:
                                self.logger.error(f"客服消息发送失败: {error_code} - {error_msg} (rid: {rid})")
                            return False
                    else:
                        self.logger.error(f"客服消息发送请求失败，状态码: {response.status}")
                        return False

        except Exception as e:
            self.logger.error(f"客服消息发送异常: {str(e)}")
            return False

    async def send_typing_indicator(self, openid: str) -> bool:
        """发送正在输入状态

        Args:
            openid: 用户的openid

        Returns:
            发送成功返回True，失败返回False
        """
        access_token = await self.get_access_token()
        if not access_token:
            return False

        try:
            url = f"{self.base_url}/message/custom/typing"
            params = {"access_token": access_token}

            data = {"touser": openid, "command": "Typing"}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, params=params, json=data, timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("errcode") == 0
                    return False

        except Exception as e:
            self.logger.error(f"发送输入状态异常: {str(e)}")
            return False


# 全局API实例
wechat_api = None


def get_wechat_api() -> Optional[WeChatAPI]:
    """获取微信API实例"""
    global wechat_api

    if not wechat_api and config.wechat_app_id and config.wechat_app_secret:
        wechat_api = WeChatAPI(config.wechat_app_id, config.wechat_app_secret)

    return wechat_api
