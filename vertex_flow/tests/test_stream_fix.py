#!/usr/bin/env python3
import asyncio
import sys
import threading
import time

from vertex_flow.src.model_client import ModelClient
from vertex_flow.workflow.edge import Always, Edge
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.vertex import SinkVertex, SourceVertex
from vertex_flow.workflow.workflow import Workflow


class MockModel:
    """模拟LLM模型用于测试"""

    def __init__(self, vertex_id):
        self.vertex_id = vertex_id

    def chat_stream(self, messages):
        """模拟流式聊天"""
        response = f"Response from {self.vertex_id}: "
        for i, char in enumerate(response):
            time.sleep(0.1)  # 模拟流式输出延迟
            yield char

        # 模拟更多内容
        for i in range(3):
            time.sleep(0.2)
            yield f"chunk_{i} "


async def test_stream_fix():
    """测试流式处理修复 - 使用简化的事件通道测试"""
    print("Testing stream fix with EventChannel...")

    from vertex_flow.workflow.event_channel import EventChannel, EventType

    # 创建事件通道
    channel = EventChannel()

    # 异步发送模拟的LLM顶点事件
    async def send_llm_events():
        await asyncio.sleep(0.1)

        # 模拟第一个LLM顶点的事件
        print("发送 LLM Vertex 1 事件...")
        channel.emit_event(
            EventType.MESSAGES,
            {
                "vertex_id": "llm_vertex_1",
                "status": "processing",
                "message": "Response from vertex_1: chunk_0 chunk_1 chunk_2 ",
            },
        )

        await asyncio.sleep(0.2)

        # 模拟第二个LLM顶点的事件
        print("发送 LLM Vertex 2 事件...")
        channel.emit_event(
            EventType.MESSAGES,
            {
                "vertex_id": "llm_vertex_2",
                "status": "processing",
                "message": "Response from vertex_2: chunk_0 chunk_1 chunk_2 ",
            },
        )

        await asyncio.sleep(0.2)

        # 模拟第三个LLM顶点的事件
        print("发送 LLM Vertex 3 事件...")
        channel.emit_event(
            EventType.MESSAGES,
            {
                "vertex_id": "llm_vertex_3",
                "status": "processing",
                "message": "Response from vertex_3: chunk_0 chunk_1 chunk_2 ",
            },
        )

        await asyncio.sleep(0.2)

        # 发送工作流完成事件
        print("发送工作流完成事件...")
        channel.emit_event(
            EventType.MESSAGES,
            {"vertex_id": "workflow", "status": "workflow_complete", "message": "所有LLM顶点处理完成"},
        )

        print("所有事件发送完毕")

    # 启动发送事件的任务
    send_task = asyncio.create_task(send_llm_events())

    print("开始监听事件...")
    event_count = 0
    vertex_events = {}

    try:
        async for event in channel.astream(EventType.MESSAGES):
            event_count += 1
            vertex_id = event.get("vertex_id", "unknown")
            status = event.get("status", "unknown")
            message = event.get("message", "")

            if vertex_id not in vertex_events:
                vertex_events[vertex_id] = []
            vertex_events[vertex_id].append(status)

            print(f"Event {event_count}: Vertex={vertex_id}, Status={status}, Message='{message}'")

            if status == "workflow_complete":
                print("Workflow completed!")
                break

    except Exception as e:
        print(f"Error during streaming: {e}")
        import traceback

        traceback.print_exc()

    # 等待发送任务完成
    await send_task

    print(f"\nSummary:")
    print(f"Total events received: {event_count}")
    print(f"Vertices that sent events: {list(vertex_events.keys())}")
    for vertex_id, statuses in vertex_events.items():
        print(f"  {vertex_id}: {statuses}")

    # 验证修复效果
    llm_vertices = [vid for vid in vertex_events.keys() if vid.startswith("llm_vertex")]
    if len(llm_vertices) >= 3:  # 应该有3个LLM vertex发送事件
        print("\n✅ 修复成功：所有LLM vertex都发送了事件")
    else:
        print(f"\n❌ 修复失败：只有 {len(llm_vertices)} 个LLM vertex发送了事件，期望3个")

    if "workflow_complete" in [status for statuses in vertex_events.values() for status in statuses]:
        print("✅ 工作流正确完成")
    else:
        print("❌ 工作流未正确完成")


if __name__ == "__main__":
    asyncio.run(test_stream_fix())
