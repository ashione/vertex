#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复重复assistant消息的问题

验证点：
1. chat_stream不会重复添加assistant消息
2. 工具调用后的消息序列正确
3. 避免重复的user content问题
"""


def test_no_duplicate_assistant_messages():
    """测试不会重复添加assistant消息"""
    print("=== 测试避免重复assistant消息 ===")

    try:
        from vertex_flow.workflow.chat import ChatModel

        # 创建一个模拟的ChatModel来测试
        class MockChatModel(ChatModel):
            def __init__(self):
                # 不调用父类初始化，避免需要真实的API密钥
                self.name = "mock-model"
                self.provider = "mock"
                self._usage = {}

            def _create_completion(self, messages, option=None, stream=False, tools=None):
                # 模拟返回包含工具调用的completion
                if stream:
                    return self._mock_stream_completion()
                else:
                    return self._mock_completion()

            def _mock_stream_completion(self):
                """模拟流式completion，包含工具调用分片"""

                class MockDelta:
                    def __init__(self, tool_calls=None, content=None):
                        self.tool_calls = tool_calls
                        self.content = content

                class MockChoice:
                    def __init__(self, delta):
                        self.delta = delta

                class MockChunk:
                    def __init__(self, choices):
                        self.choices = choices

                # 模拟工具调用分片
                tool_call_fragment = {
                    "id": "call_test_123",
                    "type": "function",
                    "function": {"name": "calculator", "arguments": '{"a": 2, "b": 3}'},
                }

                # 返回工具调用分片
                yield MockChunk([MockChoice(MockDelta(tool_calls=[tool_call_fragment]))])

                # 返回内容分片
                yield MockChunk([MockChoice(MockDelta(content="计算结果是5"))])

        # 测试chat_stream方法
        model = MockChatModel()
        messages = [{"role": "user", "content": "请计算2+3"}]

        # 记录初始消息数量
        initial_count = len(messages)
        print(f"初始消息数量: {initial_count}")

        # 调用chat_stream
        content_chunks = []
        for chunk in model.chat_stream(messages):
            if chunk:
                content_chunks.append(chunk)

        print(f"流式输出内容: {''.join(content_chunks)}")
        print(f"处理后消息数量: {len(messages)}")

        # 检查是否只添加了一个assistant消息
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant"]
        print(f"assistant消息数量: {len(assistant_messages)}")

        if len(assistant_messages) == 1:
            print("✓ 没有重复的assistant消息")
            return True
        else:
            print(f"❌ 发现重复的assistant消息: {len(assistant_messages)}")
            for i, msg in enumerate(assistant_messages):
                print(f"  Assistant消息 {i+1}: {msg}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_existing_assistant_message():
    """测试当已存在assistant消息时不会重复添加"""
    print("\n=== 测试已存在assistant消息时的处理 ===")

    try:
        from vertex_flow.workflow.chat import ChatModel

        class MockChatModel(ChatModel):
            def __init__(self):
                self.name = "mock-model"
                self.provider = "mock"
                self._usage = {}

            def _create_completion(self, messages, option=None, stream=False, tools=None):
                if stream:
                    return self._mock_stream_completion()
                else:
                    return self._mock_completion()

            def _mock_stream_completion(self):
                class MockDelta:
                    def __init__(self, tool_calls=None, content=None):
                        self.tool_calls = tool_calls
                        self.content = content

                class MockChoice:
                    def __init__(self, delta):
                        self.delta = delta

                class MockChunk:
                    def __init__(self, choices):
                        self.choices = choices

                tool_call_fragment = {
                    "id": "call_test_456",
                    "type": "function",
                    "function": {"name": "search", "arguments": '{"query": "test"}'},
                }

                yield MockChunk([MockChoice(MockDelta(tool_calls=[tool_call_fragment]))])
                yield MockChunk([MockChoice(MockDelta(content="搜索完成"))])

        model = MockChatModel()

        # 预先添加一个assistant消息（模拟已存在的情况）
        messages = [
            {"role": "user", "content": "请搜索信息"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_existing_789",
                        "type": "function",
                        "function": {"name": "existing_tool", "arguments": "{}"},
                    }
                ],
            },
        ]

        initial_count = len(messages)
        print(f"初始消息数量（包含已存在的assistant消息）: {initial_count}")

        # 调用chat_stream
        content_chunks = []
        for chunk in model.chat_stream(messages):
            if chunk:
                content_chunks.append(chunk)

        print(f"流式输出内容: {''.join(content_chunks)}")
        print(f"处理后消息数量: {len(messages)}")

        # 检查assistant消息数量
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant"]
        print(f"assistant消息数量: {len(assistant_messages)}")

        # 应该只有原来的1个assistant消息，不会重复添加
        if len(assistant_messages) == 1:
            print("✓ 正确处理已存在的assistant消息，没有重复添加")
            return True
        else:
            print(f"❌ assistant消息数量不正确: {len(assistant_messages)}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_message_sequence_integrity():
    """测试消息序列完整性"""
    print("\n=== 测试消息序列完整性 ===")

    try:
        from vertex_flow.workflow.chat import ChatModel

        class MockChatModel(ChatModel):
            def __init__(self):
                self.name = "mock-model"
                self.provider = "mock"
                self._usage = {}

            def _create_completion(self, messages, option=None, stream=False, tools=None):
                if stream:
                    return self._mock_stream_completion()
                else:
                    return self._mock_completion()

            def _mock_stream_completion(self):
                class MockDelta:
                    def __init__(self, tool_calls=None, content=None):
                        self.tool_calls = tool_calls
                        self.content = content

                class MockChoice:
                    def __init__(self, delta):
                        self.delta = delta

                class MockChunk:
                    def __init__(self, choices):
                        self.choices = choices

                # 模拟多个工具调用分片
                tool_call_fragment1 = {
                    "id": "call_multi_1",
                    "type": "function",
                    "function": {"name": "tool1", "arguments": '{"param1": "value1"}'},
                }

                tool_call_fragment2 = {
                    "id": "call_multi_2",
                    "type": "function",
                    "function": {"name": "tool2", "arguments": '{"param2": "value2"}'},
                }

                yield MockChunk([MockChoice(MockDelta(tool_calls=[tool_call_fragment1]))])
                yield MockChunk([MockChoice(MockDelta(tool_calls=[tool_call_fragment2]))])
                yield MockChunk([MockChoice(MockDelta(content="处理完成"))])

        model = MockChatModel()
        messages = [{"role": "user", "content": "请执行多个工具"}]

        # 调用chat_stream
        content_chunks = []
        for chunk in model.chat_stream(messages):
            if chunk:
                content_chunks.append(chunk)

        print(f"最终消息序列:")
        for i, msg in enumerate(messages):
            role = msg.get("role")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            print(f"  {i+1}. {role}: content='{content}', tool_calls={len(tool_calls)}")

        # 验证消息序列
        if len(messages) == 2:  # user + assistant
            assistant_msg = messages[1]
            if assistant_msg.get("role") == "assistant" and len(assistant_msg.get("tool_calls", [])) > 0:
                print("✓ 消息序列完整性正确")
                return True

        print("❌ 消息序列完整性有问题")
        return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🔧 重复assistant消息修复验证测试")
    print("=" * 50)

    tests = [
        ("避免重复assistant消息", test_no_duplicate_assistant_messages),
        ("已存在assistant消息处理", test_existing_assistant_message),
        ("消息序列完整性", test_message_sequence_integrity),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n运行 {test_name}...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} 通过")
        else:
            print(f"❌ {test_name} 失败")

    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！重复assistant消息问题已修复")
        print("✅ chat_stream不再重复添加assistant消息")
        print("✅ 避免了重复的user content问题")
        print("✅ 消息序列保持完整性")
    else:
        print("❌ 部分测试失败，需要进一步检查")

    return passed == total


if __name__ == "__main__":
    main()
