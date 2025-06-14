import asyncio
import time

from vertex_flow.workflow.event_channel import EventChannel, EventType


async def test_workflow_complete_handling():
    """测试workflow_complete事件处理是否会卡住"""
    print("开始测试workflow_complete事件处理...")

    channel = EventChannel()

    # 异步发送事件的任务
    async def send_events():
        await asyncio.sleep(0.1)
        print("发送消息事件...")
        channel.emit_event(EventType.MESSAGES, {"content": "test message", "id": 1})

        await asyncio.sleep(0.1)
        print("发送值事件...")
        channel.emit_event(EventType.VALUES, {"data": 42, "id": 2})

        await asyncio.sleep(0.1)
        print("发送更新事件...")
        channel.emit_event(EventType.UPDATES, {"progress": 50, "id": 3})

        await asyncio.sleep(0.1)
        print("发送workflow_complete事件...")
        channel.emit_event(EventType.UPDATES, {"status": "workflow_complete", "message": "工作流执行完成"})

        print("所有事件发送完毕")

    # 启动发送事件的任务
    send_task = asyncio.create_task(send_events())

    # 记录开始时间
    start_time = time.time()

    # 订阅多个事件类型
    events_received = []
    print("开始监听事件...")

    try:
        async for event in channel.astream([EventType.MESSAGES, EventType.VALUES, EventType.UPDATES]):
            events_received.append(event)
            print(f"收到事件: {event}")

            # 如果超过5秒还没结束，说明可能卡住了
            if time.time() - start_time > 5:
                print("❌ 测试超时，可能卡住了")
                break

    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        # 确保在异常情况下也返回结果
        elapsed_time = time.time() - start_time
        return len(events_received), elapsed_time

    # 等待发送任务完成
    await send_task

    # 计算耗时
    elapsed_time = time.time() - start_time
    print(f"测试耗时: {elapsed_time:.2f}秒")

    # 验证结果
    print(f"\n收到的事件数量: {len(events_received)}")

    # 检查是否收到了workflow_complete事件
    complete_events = [e for e in events_received if e.get("status") == "workflow_complete"]
    if complete_events:
        print("✅ 成功收到workflow_complete事件")
        print("✅ astream正确退出，没有卡住")
    else:
        print("❌ 没有收到workflow_complete事件")

    # 检查是否在合理时间内完成
    if elapsed_time < 2:
        print("✅ 测试在合理时间内完成")
    else:
        print("❌ 测试耗时过长，可能存在性能问题")

    print("\n测试完成")
    return len(events_received), elapsed_time


if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(test_workflow_complete_handling())
    print(f"\n最终结果: 收到 {result[0]} 个事件，耗时 {result[1]:.2f} 秒")
