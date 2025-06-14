#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的流式输出测试
"""

import asyncio
import time

import pytest

from vertex_flow.workflow.event_channel import EventChannel, EventType


@pytest.mark.asyncio
async def test_simple_stream():
    """简单的流式输出测试"""
    print("=== 简单流式输出测试 ===")

    channel = EventChannel()

    # 发送事件
    async def send_events():
        for i in range(1, 4):
            await asyncio.sleep(0.3)
            event = {"id": i, "message": f"事件 {i}"}
            print(f"发送: {event}")
            channel.emit_event(EventType.MESSAGES, event)

        # 发送完成事件
        await asyncio.sleep(0.3)
        complete_event = {"id": 4, "status": "workflow_complete", "message": "完成"}
        print(f"发送: {complete_event}")
        channel.emit_event(EventType.MESSAGES, complete_event)

    # 启动发送任务
    send_task = asyncio.create_task(send_events())

    # 接收事件
    print("开始接收事件...")
    count = 0

    async for event in channel.astream([EventType.MESSAGES]):
        count += 1
        print(f"接收: {event}")

        if event.get("status") == "workflow_complete":
            print("流结束")
            break

    await send_task
    print(f"总共接收 {count} 个事件")


if __name__ == "__main__":
    asyncio.run(test_simple_stream())
