#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试事件流的真正流式输出
"""

import asyncio
import time

import pytest

from vertex_flow.workflow.constants import CONTENT_KEY, MESSAGE_KEY
from vertex_flow.workflow.event_channel import EventChannel, EventType


@pytest.mark.asyncio
async def test_streaming_output():
    """测试流式输出是否真正按顺序进行"""
    print("=== 测试流式输出 ===")

    # 创建事件通道
    channel = EventChannel()

    # 发送事件的任务
    async def send_events_with_delay():
        events = [
            {"id": 1, "message": "第一个事件", "timestamp": time.time()},
            {"id": 2, "message": "第二个事件", "timestamp": time.time()},
            {"id": 3, "message": "第三个事件", "timestamp": time.time()},
            {"id": 4, "message": "第四个事件", "timestamp": time.time()},
            {"id": 5, "status": "workflow_complete", "message": "完成事件", "timestamp": time.time()},
        ]

        for i, event in enumerate(events):
            await asyncio.sleep(0.5)  # 每0.5秒发送一个事件
            event["timestamp"] = time.time()
            print(
                f"[发送] 事件 {
                    event['id']}: {
                    event['message']} (时间: {
                    event['timestamp']:.3f})"
            )
            channel.emit_event(EventType.MESSAGES, event)

    # 启动发送任务
    send_task = asyncio.create_task(send_events_with_delay())

    print("开始监听事件流...")
    start_time = time.time()

    try:
        async for event in channel.astream([EventType.MESSAGES]):
            receive_time = time.time()
            event_id = event.get("id", "unknown")
            message = event.get(CONTENT_KEY) or event.get(MESSAGE_KEY) or ""
            send_time = event.get("timestamp", 0)

            delay = receive_time - send_time if send_time > 0 else 0
            elapsed = receive_time - start_time

            print(
                f"[接收] 事件 {event_id}: {message} (延迟: {
                    delay:.3f}s, 总时间: {
                    elapsed:.3f}s)"
            )

            # 检查是否为完成事件
            if event.get("status") == "workflow_complete":
                print("收到完成事件，流式输出结束")
                break

    except Exception as e:
        print(f"流式输出错误: {e}")
        import traceback

        traceback.print_exc()

    # 等待发送任务完成
    await send_task

    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.3f}秒")

    if total_time >= 2.0:  # 应该至少需要2.5秒（5个事件 * 0.5秒间隔）
        print("✅ 流式输出正常：事件按时间顺序逐个接收")
    else:
        print("❌ 流式输出异常：事件可能被批量处理")


@pytest.mark.asyncio
async def test_concurrent_events():
    """测试并发事件的处理"""
    print("\n=== 测试并发事件处理 ===")

    channel = EventChannel()

    async def send_concurrent_events():
        # 同时发送多个事件
        events = [
            {"source": "A", "message": "来自A的事件"},
            {"source": "B", "message": "来自B的事件"},
            {"source": "C", "message": "来自C的事件"},
            {"source": "D", "status": "workflow_complete", "message": "完成事件"},
        ]

        # 几乎同时发送所有事件
        for event in events:
            channel.emit_event(EventType.MESSAGES, event)
            await asyncio.sleep(0.01)  # 很短的间隔

    send_task = asyncio.create_task(send_concurrent_events())

    print("开始接收并发事件...")
    event_count = 0

    try:
        async for event in channel.astream([EventType.MESSAGES]):
            event_count += 1
            source = event.get("source", "unknown")
            message = event.get(CONTENT_KEY) or event.get(MESSAGE_KEY) or ""

            print(f"[接收] 事件 {event_count}: 来源={source}, 消息={message}")

            if event.get("status") == "workflow_complete":
                print("并发事件处理完成")
                break

    except Exception as e:
        print(f"并发事件处理错误: {e}")

    await send_task

    if event_count == 4:
        print("✅ 并发事件处理正常：所有事件都被正确接收")
    else:
        print(f"❌ 并发事件处理异常：期望4个事件，实际接收{event_count}个")


async def main():
    """主测试函数"""
    print("开始测试事件流的流式输出特性...\n")

    try:
        await test_streaming_output()
        await test_concurrent_events()

        print("\n🎉 所有测试完成！")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
