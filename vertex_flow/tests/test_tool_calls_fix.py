#!/usr/bin/env python3
"""
测试工具调用修复后的功能
"""

import json
import time

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.tools.functions import FunctionTool, today_func
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex

logger = LoggerUtil.get_logger(__name__)


def test_tool_calls_in_streaming():
    """测试流式模式下的工具调用"""

    # 创建today工具
    today_tool = FunctionTool(
        name="today",
        description="获取当前时间，支持多种格式和时区。",
        func=today_func,
        schema={
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": [
                        "timestamp",
                        "timestamp_ms",
                        "iso",
                        "iso_utc",
                        "date",
                        "time",
                        "datetime",
                        "rfc2822",
                        "custom",
                    ],
                    "description": "输出格式",
                },
                "timezone": {"type": "string", "description": "时区（如UTC, Asia/Shanghai）"},
                "custom_format": {"type": "string", "description": "自定义格式字符串"},
            },
            "required": [],
        },
    )

    # 创建模拟的ChatModel（用于测试）
    class MockChatModel(ChatModel):
        def __init__(self):
            super().__init__(name="mock-model", sk="mock-key", base_url="mock-url", provider="mock")
            self.call_count = 0
            self.max_calls = 3  # 限制最大调用次数，防止无限循环

        def chat_stream(self, messages, option=None, tools=None):
            """模拟流式输出，包含工具调用"""
            self.call_count += 1

            # 防止无限循环
            if self.call_count > self.max_calls:
                logger.warning(f"MockChatModel达到最大调用次数限制: {self.max_calls}")
                return

            # 检查消息中是否已有工具调用结果
            has_tool_result = any(msg.get("role") == "tool" for msg in messages)

            # 如果已有工具结果，返回最终响应
            if has_tool_result:
                final_chunks = [
                    type(
                        "MockChunk",
                        (),
                        {
                            "choices": [
                                type(
                                    "MockChoice",
                                    (),
                                    {"delta": type("MockDelta", (), {"content": "我已经获取了当前时间："})()},
                                )()
                            ]
                        },
                    )(),
                    type(
                        "MockChunk",
                        (),
                        {
                            "choices": [
                                type(
                                    "MockChoice",
                                    (),
                                    {"delta": type("MockDelta", (), {"content": "2024-01-15T10:30:00"})()},
                                )()
                            ]
                        },
                    )(),
                ]
                for chunk in final_chunks:
                    yield chunk
                return

            # 第一次调用：返回工具调用
            tool_call_chunks = [
                # 工具调用开始
                type(
                    "MockChunk",
                    (),
                    {
                        "choices": [
                            type(
                                "MockChoice",
                                (),
                                {
                                    "delta": type(
                                        "MockDelta",
                                        (),
                                        {
                                            "tool_calls": [
                                                type(
                                                    "MockToolCall",
                                                    (),
                                                    {
                                                        "id": "call_123",
                                                        "function": type(
                                                            "MockFunction",
                                                            (),
                                                            {"name": "today", "arguments": '{"format": "iso"}'},
                                                        )(),
                                                        "type": "function",
                                                    },
                                                )()
                                            ]
                                        },
                                    )()
                                },
                            )()
                        ]
                    },
                )(),
            ]

            for chunk in tool_call_chunks:
                yield chunk

    # 创建LLMVertex
    llm_vertex = LLMVertex(
        id="test_llm",
        name="测试LLM",
        model=MockChatModel(),
        params={
            "system": "你是一个有用的助手，可以调用today工具来获取时间信息。",
            "user": [],
            "enable_stream": True,
            "enable_reasoning": False,
            "show_reasoning": False,
        },
        tools=[today_tool],
    )

    # 设置消息
    llm_vertex.messages = [
        {"role": "system", "content": "你是一个有用的助手，可以调用today工具来获取时间信息。"},
        {"role": "user", "content": "请告诉我现在的时间"},
    ]

    # 创建上下文
    context = WorkflowContext()

    print("🧪 开始测试流式工具调用...")
    print("=" * 50)

    try:
        # 使用流式生成器
        print("📤 流式输出:")
        chunk_count = 0
        for chunk in llm_vertex.chat_stream_generator({}, context):
            chunk_count += 1
            print(f"  Chunk {chunk_count}: {chunk}")

        print(f"\n✅ 流式输出完成，共收到 {chunk_count} 个chunk")

        # 检查messages中是否有工具调用
        print("\n📋 检查messages:")
        for i, msg in enumerate(llm_vertex.messages):
            print(f"  Message {i}: {msg}")

        # 检查是否有工具调用结果
        tool_messages = [msg for msg in llm_vertex.messages if msg.get("role") == "tool"]
        if tool_messages:
            print(f"\n🛠️ 发现 {len(tool_messages)} 个工具调用结果:")
            for msg in tool_messages:
                print(f"  Tool: {msg}")
        else:
            print("\n⚠️ 未发现工具调用结果")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


def test_tool_calls_in_non_streaming():
    """测试非流式模式下的工具调用"""

    # 创建today工具
    today_tool = FunctionTool(
        name="today",
        description="获取当前时间，支持多种格式和时区。",
        func=today_func,
        schema={
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": [
                        "timestamp",
                        "timestamp_ms",
                        "iso",
                        "iso_utc",
                        "date",
                        "time",
                        "datetime",
                        "rfc2822",
                        "custom",
                    ],
                    "description": "输出格式",
                },
                "timezone": {"type": "string", "description": "时区（如UTC, Asia/Shanghai）"},
                "custom_format": {"type": "string", "description": "自定义格式字符串"},
            },
            "required": [],
        },
    )

    # 创建模拟的ChatModel（用于测试）
    class MockChatModel(ChatModel):
        def __init__(self):
            super().__init__(name="mock-model", sk="mock-key", base_url="mock-url", provider="mock")
            self.call_count = 0
            self.max_calls = 3  # 限制最大调用次数，防止无限循环

        def chat(self, messages, option=None, tools=None):
            """模拟非流式输出，包含工具调用"""
            self.call_count += 1

            # 防止无限循环
            if self.call_count > self.max_calls:
                logger.warning(f"MockChatModel达到最大调用次数限制: {self.max_calls}")
                return type(
                    "MockChoice",
                    (),
                    {
                        "finish_reason": "stop",
                        "message": type(
                            "MockMessage",
                            (),
                            {
                                "role": "assistant",
                                "content": "达到最大调用次数限制",
                            },
                        )(),
                    },
                )()

            # 检查消息中是否已有工具调用结果
            has_tool_result = any(msg.get("role") == "tool" for msg in messages)

            # 如果已有工具结果，返回最终响应
            if has_tool_result:
                return type(
                    "MockChoice",
                    (),
                    {
                        "finish_reason": "stop",
                        "message": type(
                            "MockMessage",
                            (),
                            {
                                "role": "assistant",
                                "content": "我已经获取了当前时间：2024-01-15T10:30:00",
                            },
                        )(),
                    },
                )()

            # 第一次调用：返回工具调用
            mock_choice = type(
                "MockChoice",
                (),
                {
                    "finish_reason": "tool_calls",
                    "message": type(
                        "MockMessage",
                        (),
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                type(
                                    "MockToolCall",
                                    (),
                                    {
                                        "id": "call_123",
                                        "function": type(
                                            "MockFunction", (), {"name": "today", "arguments": '{"format": "iso"}'}
                                        )(),
                                        "type": "function",
                                    },
                                )
                            ],
                        },
                    )(),
                },
            )()
            return mock_choice

    # 创建LLMVertex
    llm_vertex = LLMVertex(
        id="test_llm",
        name="测试LLM",
        model=MockChatModel(),
        params={
            "system": "你是一个有用的助手，可以调用today工具来获取时间信息。",
            "user": [],
            "enable_stream": False,  # 禁用流式
            "enable_reasoning": False,
            "show_reasoning": False,
        },
        tools=[today_tool],
    )

    # 设置消息
    llm_vertex.messages = [
        {"role": "system", "content": "你是一个有用的助手，可以调用today工具来获取时间信息。"},
        {"role": "user", "content": "请告诉我现在的时间"},
    ]

    # 创建上下文
    context = WorkflowContext()

    print("🧪 开始测试非流式工具调用...")
    print("=" * 50)

    try:
        # 使用非流式模式
        result = llm_vertex.chat({}, context)
        print(f"📤 非流式输出: {result}")

        # 检查messages中是否有工具调用
        print("\n📋 检查messages:")
        for i, msg in enumerate(llm_vertex.messages):
            print(f"  Message {i}: {msg}")

        # 检查是否有工具调用结果
        tool_messages = [msg for msg in llm_vertex.messages if msg.get("role") == "tool"]
        if tool_messages:
            print(f"\n🛠️ 发现 {len(tool_messages)} 个工具调用结果:")
            for msg in tool_messages:
                print(f"  Tool: {msg}")
        else:
            print("\n⚠️ 未发现工具调用结果")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🔧 测试工具调用修复")
    print("=" * 60)

    print("\n1️⃣ 测试流式模式下的工具调用:")
    test_tool_calls_in_streaming()

    print("\n" + "=" * 60)

    print("\n2️⃣ 测试非流式模式下的工具调用:")
    test_tool_calls_in_non_streaming()

    print("\n" + "=" * 60)
    print("🎉 测试完成!")
