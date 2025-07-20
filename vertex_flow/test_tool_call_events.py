#!/usr/bin/env python3
"""
测试工具调用事件发送的简单脚本
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.constants import (
    CONTENT_KEY,
    SYSTEM,
    TYPE_KEY,
    USER,
    VERTEX_ID_KEY,
)
from vertex_flow.workflow.events import EventType
from vertex_flow.workflow.stream_data import StreamData, StreamDataType
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.workflow import Workflow


class MockChatModelWithToolCalls:
    """模拟带工具调用的ChatModel"""

    def __init__(self):
        self.call_count = 0

    def chat_stream(self, messages, option=None, tools=None):
        """模拟返回工具调用的流式数据"""
        self.call_count += 1

        # 模拟工具调用
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "test_function", "arguments": '{"param1": "value1", "param2": "value2"}'},
            }
        ]

        # 先返回工具调用
        yield StreamData.create_tool_calls(tool_calls)

        # 然后返回内容
        yield StreamData.create_content("工具调用完成")


def test_tool_call_events():
    """测试工具调用事件是否正确发送"""
    print("=== 测试工具调用事件发送 ===")

    # 创建工作流
    workflow = Workflow()

    # 创建LLM vertex
    llm_vertex = LLMVertex(
        id="test_llm", model=MockChatModelWithToolCalls(), params={SYSTEM: "你是一个测试助手", USER: ["请调用测试函数"]}
    )

    # 添加到工作流
    workflow.add_vertex(llm_vertex)

    # 收集事件
    events = []

    def event_handler(event_type, event_data):
        events.append((event_type, event_data))
        print(f"收到事件: {event_type}, 数据: {event_data}")

    # 注册事件处理器
    workflow.event_channel.add_listener(EventType.MESSAGES, event_handler)

    # 执行流式处理
    print("\n开始流式处理...")
    result = ""
    for chunk in llm_vertex._unified_stream_core({}, None, emit_events=True):
        result += chunk
        print(f"流式输出: {chunk}")

    print(f"\n最终结果: {result}")
    print(f"\n总共收到 {len(events)} 个事件")

    # 检查是否有工具调用事件
    tool_call_events = [e for e in events if e[1].get(TYPE_KEY) == "tool_call"]
    content_events = [e for e in events if e[1].get(TYPE_KEY) in ["regular", "reasoning"]]

    print(f"\n工具调用事件数量: {len(tool_call_events)}")
    print(f"内容事件数量: {len(content_events)}")

    if tool_call_events:
        print("\n✅ 工具调用事件发送成功!")
        for i, (event_type, event_data) in enumerate(tool_call_events):
            tool_call = event_data.get("tool_call", {})
            print(
                f"  事件 {i+1}: 函数={tool_call.get('function', {}).get('name')}, 参数={tool_call.get('function', {}).get('arguments')}"
            )
    else:
        print("\n❌ 没有收到工具调用事件")

    return len(tool_call_events) > 0


if __name__ == "__main__":
    success = test_tool_call_events()
    sys.exit(0 if success else 1)
