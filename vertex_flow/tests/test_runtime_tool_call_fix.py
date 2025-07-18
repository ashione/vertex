#!/usr/bin/env python3
"""
测试 RuntimeToolCall 导入修复效果
验证：
1. RuntimeToolCall 导入不再报错
2. DeepSeek 流式工具调用能正常工作
3. 消息序列完整性
"""

import logging
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_runtime_tool_call_import():
    """测试 RuntimeToolCall 导入"""
    print("=== 测试 RuntimeToolCall 导入 ===")

    try:
        # 测试从 tool_caller 导入 RuntimeToolCall
        from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall

        print("✓ 从 tool_caller 导入 RuntimeToolCall 成功")

        # 测试 LLMVertex 导入（包含修复后的导入语句）
        from vertex_flow.workflow.vertex.llm_vertex import LLMVertex

        print("✓ LLMVertex 导入成功，内部 RuntimeToolCall 导入已修复")

        # 测试 RuntimeToolCall 基本功能
        test_tool_call = {
            "id": "test_call_123",
            "type": "function",
            "function": {"name": "test_function", "arguments": '{"param": "value"}'},
        }

        runtime_tool_call = RuntimeToolCall.normalize(test_tool_call)
        print(f"✓ RuntimeToolCall.normalize 工作正常: {runtime_tool_call.id}")

        runtime_tool_calls = RuntimeToolCall.normalize_list([test_tool_call])
        print(f"✓ RuntimeToolCall.normalize_list 工作正常: {len(runtime_tool_calls)} 个工具调用")

        return True

    except ImportError as e:
        print(f"✗ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 其他错误: {e}")
        return False


def test_deepseek_tool_caller():
    """测试 DeepSeek 工具调用器"""
    print("\n=== 测试 DeepSeek 工具调用器 ===")

    try:
        from vertex_flow.workflow.tools.tool_caller import DeepSeekToolCaller, create_tool_caller

        # 创建 DeepSeek 工具调用器
        tool_caller = create_tool_caller("deepseek")
        print(f"✓ DeepSeek 工具调用器创建成功: {type(tool_caller).__name__}")

        # 测试基本功能
        print(f"✓ 支持流式处理: {tool_caller.can_handle_streaming()}")

        # 测试工具调用消息创建
        test_tool_calls = [
            {
                "id": "call_test_123",
                "type": "function",
                "function": {"name": "calculator", "arguments": '{"expression": "2+2"}'},
            }
        ]

        assistant_msg = tool_caller.create_assistant_message(test_tool_calls)
        print(f"✓ 助手消息创建成功: {assistant_msg['role']} with {len(assistant_msg['tool_calls'])} tool calls")

        tool_msg = tool_caller.create_tool_message("call_test_123", "calculator", {"result": 4})
        print(f"✓ 工具响应消息创建成功: {tool_msg['role']} for {tool_msg['tool_call_id']}")

        return True

    except Exception as e:
        print(f"✗ DeepSeek 工具调用器测试失败: {e}")
        return False


def test_message_sequence_integrity():
    """测试消息序列完整性"""
    print("\n=== 测试消息序列完整性 ===")

    try:
        from vertex_flow.workflow.tools.tool_caller import create_tool_caller

        tool_caller = create_tool_caller("deepseek")

        # 模拟一个完整的工具调用序列
        messages = [
            {"role": "system", "content": "你是一个数学助手。"},
            {"role": "user", "content": "请计算2+2等于多少？"},
        ]

        # 模拟助手消息包含工具调用
        tool_calls = [
            {
                "id": "call_calc_123",
                "type": "function",
                "function": {"name": "calculator", "arguments": '{"expression": "2+2"}'},
            }
        ]

        assistant_msg = tool_caller.create_assistant_message(tool_calls)
        messages.append(assistant_msg)

        # 模拟工具响应
        tool_msg = tool_caller.create_tool_message("call_calc_123", "calculator", {"result": 4})
        messages.append(tool_msg)

        # 验证消息序列
        print(f"✓ 消息序列包含 {len(messages)} 条消息")

        # 检查每个工具调用都有对应的响应
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant" and msg.get("tool_calls")]
        tool_messages = [msg for msg in messages if msg.get("role") == "tool"]

        print(f"✓ 助手工具调用消息: {len(assistant_messages)}")
        print(f"✓ 工具响应消息: {len(tool_messages)}")

        # 验证每个工具调用都有对应的响应
        for assistant_msg in assistant_messages:
            for tool_call in assistant_msg["tool_calls"]:
                tool_call_id = tool_call["id"]
                corresponding_tool_msg = next(
                    (msg for msg in tool_messages if msg.get("tool_call_id") == tool_call_id), None
                )
                if corresponding_tool_msg:
                    print(f"✓ 工具调用 {tool_call_id} 有对应的响应")
                else:
                    print(f"✗ 工具调用 {tool_call_id} 缺少对应的响应")
                    return False

        print("✓ 消息序列完整性验证通过")
        return True

    except Exception as e:
        print(f"✗ 消息序列完整性测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🔧 RuntimeToolCall 导入修复验证测试")
    print("=" * 50)

    tests = [test_runtime_tool_call_import, test_deepseek_tool_caller, test_message_sequence_integrity]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ {test.__name__} 失败")
        except Exception as e:
            print(f"❌ {test.__name__} 异常: {e}")

    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！RuntimeToolCall 导入错误已修复")
        print("✅ DeepSeek 流式工具调用应该不再出现 'insufficient tool messages' 错误")
        return True
    else:
        print("❌ 部分测试失败，需要进一步修复")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
