#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步消息处理器
处理后台消息处理任务和客服消息发送
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Set

try:
    from .config import config
    from .message_processor import MessageProcessor
    from .wechat_api import get_wechat_api
except ImportError:
    from config import config
    from message_processor import MessageProcessor
    from wechat_api import get_wechat_api


@dataclass
class AsyncTask:
    """异步任务数据类"""

    task_id: str
    user_openid: str
    message_content: str
    workflow_name: Optional[str] = None
    image_url: Optional[str] = None
    created_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class AsyncMessageProcessor:
    """异步消息处理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.message_processor = MessageProcessor(
            api_base_url=config.vertex_flow_api_url, default_workflow=config.default_workflow, config=config
        )
        self.wechat_api = get_wechat_api()

        # 任务管理
        self.pending_tasks: Dict[str, AsyncTask] = {}
        self.processing_tasks: Set[str] = set()
        self.completed_tasks: Dict[str, Dict] = {}  # 存储已完成任务的结果
        self.task_queue = None  # 延迟初始化

        # 启动后台处理器
        self._background_task = None
        self._shutdown = False

    async def start(self):
        """启动异步处理器"""
        if self._background_task is None:
            # 在当前事件循环中初始化队列
            self.task_queue = asyncio.Queue()
            self._background_task = asyncio.create_task(self._background_processor())
            self.logger.info("异步消息处理器已启动")

    async def stop(self):
        """停止异步处理器"""
        self._shutdown = True
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
        self.logger.info("异步消息处理器已停止")

    async def submit_task(
        self,
        user_openid: str,
        message_content: str,
        workflow_name: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """提交异步处理任务

        Args:
            user_openid: 用户openid
            message_content: 消息内容
            workflow_name: 工作流名称
            image_url: 图片URL

        Returns:
            任务ID
        """
        task_id = f"{user_openid}_{int(time.time() * 1000)}"

        task = AsyncTask(
            task_id=task_id,
            user_openid=user_openid,
            message_content=message_content,
            workflow_name=workflow_name,
            image_url=image_url,
        )

        self.pending_tasks[task_id] = task

        # 确保队列已初始化
        if self.task_queue is None:
            await self.start()

        await self.task_queue.put(task_id)

        self.logger.info(f"提交异步任务: {task_id}, 用户: {user_openid}")

        # 发送正在输入状态（如果API可用）
        if self.wechat_api:
            try:
                await self._send_typing_indicator(user_openid)
            except Exception as e:
                self.logger.warning(f"发送输入状态失败: {str(e)}")

        return task_id

    async def _send_typing_indicator(self, user_openid: str):
        """发送正在输入状态"""
        try:
            await self.wechat_api.send_typing_indicator(user_openid)
        except Exception as e:
            self.logger.warning(f"发送输入状态失败: {str(e)}")

    async def _background_processor(self):
        """后台任务处理器"""
        self.logger.info("后台任务处理器开始运行")

        while not self._shutdown:
            try:
                # 等待任务，设置超时避免阻塞
                task_id = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)

                if task_id in self.pending_tasks:
                    task = self.pending_tasks.pop(task_id)
                    self.processing_tasks.add(task_id)

                    # 处理任务
                    await self._process_task(task)

            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                self.logger.error(f"后台处理器异常: {str(e)}")
                await asyncio.sleep(1)

        self.logger.info("后台任务处理器已停止")

    async def _process_task(self, task: AsyncTask):
        """处理单个任务"""
        start_time = time.time()

        try:
            self.logger.info(f"开始处理任务: {task.task_id}")

            # 调用消息处理器
            response = await self.message_processor.process_message(
                user_id=task.user_openid,
                content=task.message_content,
                image_url=task.image_url,
                workflow_name=task.workflow_name,
            )

            # 发送客服消息
            if self.wechat_api and response:
                success = await self.wechat_api.send_customer_service_message(openid=task.user_openid, message=response)

                processing_time = time.time() - start_time

                # 存储任务结果（无论客服消息是否发送成功）
                self.completed_tasks[task.task_id] = {
                    "status": "completed",
                    "result": response,
                    "processing_time": processing_time,
                    "completed_at": time.time(),
                }

                if success:
                    self.logger.info(f"任务处理完成: {task.task_id}, 耗时: {processing_time:.2f}秒")

                    # 更新用户会话
                    self.message_processor.update_user_session(task.user_openid, task.message_content, response)
                else:
                    self.logger.error(f"客服消息发送失败: {task.task_id}")
                    # 可以考虑重试机制
            else:
                self.logger.error(f"任务处理失败或API不可用: {task.task_id}")

        except Exception as e:
            self.logger.error(f"处理任务异常: {task.task_id}, 错误: {str(e)}")

            # 存储失败状态
            self.completed_tasks[task.task_id] = {
                "status": "failed",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "completed_at": time.time(),
            }

            # 发送错误消息给用户
            if self.wechat_api:
                try:
                    await self.wechat_api.send_customer_service_message(
                        openid=task.user_openid, message="抱歉，处理您的消息时遇到了问题，请稍后再试。"
                    )
                except Exception as send_error:
                    self.logger.error(f"发送错误消息失败: {str(send_error)}")

        finally:
            # 清理任务
            self.processing_tasks.discard(task.task_id)

            # 定期清理过期的已完成任务（保留10分钟）
            current_time = time.time()
            expired_tasks = [
                tid
                for tid, task_info in self.completed_tasks.items()
                if current_time - task_info.get("completed_at", 0) > 600  # 10分钟
            ]
            for tid in expired_tasks:
                self.completed_tasks.pop(tid, None)
                self.logger.debug(f"清理过期任务: {tid}")

    def get_task_status(self, task_id: str) -> Dict[str, any]:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        if task_id in self.completed_tasks:
            # 任务已完成
            return self.completed_tasks[task_id]
        elif task_id in self.pending_tasks:
            task = self.pending_tasks[task_id]
            return {"status": "pending", "created_at": task.created_at, "wait_time": time.time() - task.created_at}
        elif task_id in self.processing_tasks:
            return {"status": "processing", "message": "正在处理中..."}
        else:
            return {"status": "unknown", "message": "任务不存在或已完成"}

    def get_queue_status(self) -> Dict[str, any]:
        """获取队列状态"""
        return {
            "pending_count": len(self.pending_tasks),
            "processing_count": len(self.processing_tasks),
            "queue_size": self.task_queue.qsize(),
            "is_running": self._background_task is not None and not self._background_task.done(),
        }


# 全局异步处理器实例
async_processor = AsyncMessageProcessor()


async def get_async_processor() -> AsyncMessageProcessor:
    """获取异步处理器实例"""
    if async_processor._background_task is None:
        await async_processor.start()
    return async_processor
