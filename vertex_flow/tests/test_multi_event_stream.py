import asyncio

import pytest

from vertex_flow.workflow.event_channel import EventChannel, EventType


class TestMultiEventStream:
    """测试 EventChannel 的多事件类型订阅功能"""

    @pytest.mark.asyncio
    async def test_single_event_type_subscription(self):
        """测试单个事件类型订阅（向后兼容性）"""
        channel = EventChannel()

        # 发送一个消息事件
        channel.emit_event(EventType.MESSAGES, {"content": "test message", "status": "processing"})
        channel.emit_event(EventType.MESSAGES, {"content": "complete", "status": "workflow_complete"})

        # 订阅单个事件类型
        events = []
        async for event in channel.astream(EventType.MESSAGES):
            events.append(event)
            if event.get("status") == "workflow_complete":
                break

        assert len(events) == 2
        assert events[0]["content"] == "test message"
        assert events[1]["content"] == "complete"

    @pytest.mark.asyncio
    async def test_multiple_event_types_subscription(self):
        """测试多个事件类型订阅"""
        channel = EventChannel()

        # 异步发送不同类型的事件
        async def send_events():
            await asyncio.sleep(0.1)
            channel.emit_event(EventType.MESSAGES, {"type": "message", "content": "hello"})
            await asyncio.sleep(0.1)
            channel.emit_event(EventType.VALUES, {"type": "value", "data": 42})
            await asyncio.sleep(0.1)
            channel.emit_event(EventType.UPDATES, {"type": "update", "progress": 50})
            await asyncio.sleep(0.1)
            channel.emit_event(EventType.MESSAGES, {"type": "message", "status": "workflow_complete"})

        # 启动发送事件的任务
        send_task = asyncio.create_task(send_events())

        # 订阅多个事件类型
        events = []
        async for event in channel.astream([EventType.MESSAGES, EventType.VALUES, EventType.UPDATES]):
            events.append(event)
            if event.get("status") == "workflow_complete":
                break

        await send_task

        # 验证收到了所有类型的事件
        assert len(events) == 4
        event_types = [event.get("type") for event in events]
        assert "message" in event_types
        assert "value" in event_types
        assert "update" in event_types

    @pytest.mark.asyncio
    async def test_mixed_subscription_format(self):
        """测试混合订阅格式（字符串和列表）"""
        channel = EventChannel()

        # 发送事件
        channel.emit_event(EventType.UPDATES, {"progress": 100, "status": "workflow_complete"})

        # 使用字符串格式订阅（应该被转换为列表）
        events = []
        async for event in channel.astream(EventType.UPDATES):
            events.append(event)
            if event.get("status") == "workflow_complete":
                break

        assert len(events) == 1
        assert events[0]["progress"] == 100

    @pytest.mark.asyncio
    async def test_concurrent_event_handling(self):
        """测试并发事件处理"""
        channel = EventChannel()

        # 快速发送多个不同类型的事件
        async def rapid_send():
            for i in range(5):
                channel.emit_event(EventType.MESSAGES, {"id": i, "type": "message"})
                channel.emit_event(EventType.VALUES, {"id": i, "type": "value"})
                await asyncio.sleep(0.01)  # 很短的间隔

            channel.emit_event(EventType.UPDATES, {"status": "workflow_complete"})

        # 启动快速发送任务
        send_task = asyncio.create_task(rapid_send())

        # 订阅所有事件类型
        events = []
        async for event in channel.astream([EventType.MESSAGES, EventType.VALUES, EventType.UPDATES]):
            events.append(event)
            if event.get("status") == "workflow_complete":
                break

        await send_task

        # 验证收到了预期数量的事件
        assert len(events) == 11  # 5个message + 5个value + 1个complete

        # 验证事件类型分布
        message_events = [e for e in events if e.get("type") == "message"]
        value_events = [e for e in events if e.get("type") == "value"]
        complete_events = [e for e in events if e.get("status") == "workflow_complete"]

        assert len(message_events) == 5
        assert len(value_events) == 5
        assert len(complete_events) == 1


if __name__ == "__main__":
    # 运行测试
    asyncio.run(TestMultiEventStream().test_multiple_event_types_subscription())
    print("多事件类型订阅测试通过！")
