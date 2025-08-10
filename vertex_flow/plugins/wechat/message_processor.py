#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息处理器
负责与Vertex Flow Chat API的集成，处理用户消息并获取AI回复
"""

import asyncio
import json
import logging
from typing import Dict, Optional

import aiohttp


class MessageProcessor:
    """消息处理器，与Vertex Flow Chat API集成"""

    def __init__(self, api_base_url: str, default_workflow: str = "default_chat", config=None):
        self.api_base_url = api_base_url.rstrip("/")
        self.default_workflow = default_workflow
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 用户会话管理
        self.user_sessions = {}

    async def process_message(
        self, user_id: str, content: str, image_url: Optional[str] = None, workflow_name: Optional[str] = None
    ) -> str:
        """处理用户消息，调用Vertex Flow API获取回复"""
        try:
            # 准备请求数据
            request_data = {
                "workflow_name": workflow_name or self.default_workflow,
                "content": content,
                "stream": False,
                "enable_mcp": self.config.enable_mcp if self.config else True,
                "enable_search": self.config.enable_search if self.config else True,
                "enable_reasoning": self.config.enable_reasoning if self.config else False,
                "show_reasoning": False,
                "enable_tools": self.config.enable_tools if self.config else True,
            }

            # 如果有图片URL，添加多模态支持
            if image_url:
                request_data["image_url"] = image_url

            # 调用Vertex Flow API
            response = await self._call_vertex_flow_api(request_data)

            if response and response.get("status"):
                output = response.get("output", "")
                if isinstance(output, dict):
                    # 如果输出是字典，尝试提取文本内容
                    # 优先提取llm字段，然后是content字段
                    if "llm" in output:
                        return str(output["llm"])
                    elif "content" in output:
                        return str(output["content"])
                    else:
                        return str(output)
                return str(output)
            else:
                error_msg = response.get("message", "处理失败") if response else "服务暂时不可用"
                self.logger.error(f"API调用失败: {error_msg}")
                return f"抱歉，{error_msg}，请稍后再试。"

        except Exception as e:
            self.logger.error(f"处理消息时发生错误: {str(e)}")
            return "抱歉，处理您的消息时遇到了问题，请稍后再试。"

    async def _call_vertex_flow_api(self, request_data: Dict) -> Optional[Dict]:
        """调用Vertex Flow API"""
        url = f"{self.api_base_url}/workflow"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"API请求失败，状态码: {response.status}")
                        error_text = await response.text()
                        self.logger.error(f"错误详情: {error_text}")
                        return None
        except asyncio.TimeoutError:
            self.logger.error("API请求超时")
            return None
        except Exception as e:
            self.logger.error(f"API请求异常: {str(e)}")
            return None

    def get_user_session(self, user_id: str) -> Dict:
        """获取用户会话信息"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {"messages": [], "last_activity": None}
        return self.user_sessions[user_id]

    def update_user_session(self, user_id: str, user_message: str, ai_response: str):
        """更新用户会话"""
        session = self.get_user_session(user_id)
        session["messages"].append(
            {"user": user_message, "assistant": ai_response, "timestamp": asyncio.get_event_loop().time()}
        )
        session["last_activity"] = asyncio.get_event_loop().time()

        # 保持最近10条对话记录
        if len(session["messages"]) > 10:
            session["messages"] = session["messages"][-10:]

    def clear_expired_sessions(self, expire_time: int = 3600):
        """清理过期会话（默认1小时）"""
        current_time = asyncio.get_event_loop().time()
        expired_users = []

        for user_id, session in self.user_sessions.items():
            if session.get("last_activity") and current_time - session["last_activity"] > expire_time:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self.user_sessions[user_id]
            self.logger.info(f"清理过期会话: {user_id}")
