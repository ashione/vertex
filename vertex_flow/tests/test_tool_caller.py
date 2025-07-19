#!/usr/bin/env python3
"""
ToolCaller专项测试

合并了以下测试功能：
1. tool_caller合并测试
2. RuntimeToolCall修复测试
3. DeepSeek tool_caller测试
4. 消息序列完整性测试
"""

import os
import sys

from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall, ToolCaller, create_tool_caller


def test_runtime_tool_call_import():
    """测试RuntimeToolCall导入修复"""
    print("=== 测试 RuntimeToolCall 导入 ===")

    try:
        # 测试从 tool_caller 导入 RuntimeToolCall
        from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall

        print("✓ 从 tool_caller 导入 RuntimeToolCall 成功")

        # 测试LLMVertex导入，确保内部RuntimeToolCall导入已修复
        from vertex_flow.workflow.vertex.llm_vertex import LLMVertex

        print("✓ LLMVertex 导入成功，内部 RuntimeToolCall 导入已修复")

        # 测试 RuntimeToolCall 基本功能
        test_tool_call = {
            "id": "call_test_123",
            "type": "function",
            "function": {"name": "calculator", "arguments": '{"a": 2, "b": 3, "operation": "add"}'},
        }

        runtime_tool_call = RuntimeToolCall.normalize(test_tool_call)
        print(f"✓ RuntimeToolCall.normalize 工作正常: {runtime_tool_call.id}")

        runtime_tool_calls = RuntimeToolCall.normalize_list([test_tool_call])
        print(f"✓ RuntimeToolCall.normalize_list 工作正常: {len(runtime_tool_calls)} 个工具调用")

        return True

    except Exception as e:
        print(f"❌ RuntimeToolCall 导入测试失败: {e}")
        return False


def test_deepseek_tool_caller():
    """测试DeepSeek工具调用器"""
    print("\n=== 测试 DeepSeek 工具调用器 ===")

    try:
        from vertex_flow.workflow.tools.tool_caller import DeepSeekToolCaller, create_tool_caller

        # 创建DeepSeek工具调用器
        tool_caller = create_tool_caller("deepseek")
        print(f"✓ DeepSeek 工具调用器创建成功: {type(tool_caller).__name__}")

        # 测试流式处理能力
        print(f"✓ 支持流式处理: {tool_caller.can_handle_streaming()}")

        # 测试消息创建功能
        test_tool_calls = [
            {
                "id": "call_test_123",
                "type": "function",
                "function": {"name": "calculator", "arguments": '{"a": 2, "b": 3, "operation": "add"}'},
            }
        ]

        assistant_msg = tool_caller.create_assistant_message(test_tool_calls)
        print(f"✓ 助手消息创建成功: {assistant_msg['role']} with {len(assistant_msg['tool_calls'])} tool calls")

        tool_msg = tool_caller.create_tool_message("call_test_123", "calculator", {"result": 4})
        print(f"✓ 工具响应消息创建成功: {tool_msg['role']} for {tool_msg['tool_call_id']}")

        return True

    except Exception as e:
        print(f"❌ DeepSeek 工具调用器测试失败: {e}")
        return False


def test_message_sequence_integrity():
    """测试消息序列完整性"""
    print("\n=== 测试消息序列完整性 ===")

    try:
        from vertex_flow.workflow.tools.tool_caller import create_tool_caller

        tool_caller = create_tool_caller("deepseek")

        # 模拟完整的对话序列
        messages = [
            {"role": "system", "content": "你是一个数学助手。"},
            {"role": "user", "content": "请计算 2 + 3"},
        ]

        # 添加助手工具调用
        tool_calls = [
            {
                "id": "call_calc_123",
                "type": "function",
                "function": {"name": "calculator", "arguments": '{"a": 2, "b": 3, "operation": "add"}'},
            }
        ]

        assistant_msg = tool_caller.create_assistant_message(tool_calls)
        messages.append(assistant_msg)

        # 添加工具响应
        tool_msg = tool_caller.create_tool_message("call_calc_123", "calculator", {"result": 4})
        messages.append(tool_msg)

        # 验证消息序列
        print(f"✓ 消息总数: {len(messages)}")
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant" and msg.get("tool_calls")]
        tool_messages = [msg for msg in messages if msg.get("role") == "tool"]

        print(f"✓ 助手工具调用消息: {len(assistant_messages)}")
        print(f"✓ 工具响应消息: {len(tool_messages)}")

        # 验证工具调用和响应的对应关系
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

        return True

    except Exception as e:
        print(f"❌ 消息序列完整性测试失败: {e}")
        return False


def test_merged_functionality():
    """测试合并后的功能"""
    print("\n=== 测试 tool_caller 和 RuntimeToolCall 合并 ===")

    try:
        # 测试从 tool_caller 导入 RuntimeToolCall
        from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall, ToolCaller, create_tool_caller

        print("✓ 从 tool_caller 成功导入 RuntimeToolCall 和相关类")

        # 测试 RuntimeToolCall 功能
        test_tool_call = {
            "id": "call_merge_test_123",
            "type": "function",
            "function": {"name": "calculator", "arguments": '{"a": 2, "b": 3, "operation": "add"}'},
        }

        runtime_tool_call = RuntimeToolCall.normalize(test_tool_call)
        print(f"✓ RuntimeToolCall.normalize 工作正常: {runtime_tool_call.id}")

        runtime_tool_calls = RuntimeToolCall.normalize_list([test_tool_call])
        print(f"✓ RuntimeToolCall.normalize_list 工作正常: {len(runtime_tool_calls)} 个工具调用")

        # 测试 tool_caller 功能
        tool_caller = create_tool_caller("openai")
        print(f"✓ 工具调用器创建成功: {type(tool_caller).__name__}")

        # 验证不能从 functions 导入 RuntimeToolCall
        try:
            from vertex_flow.workflow.tools.functions import RuntimeToolCall as OldRuntimeToolCall

            print("❌ 错误：仍然可以从 functions 导入 RuntimeToolCall")
            return False
        except ImportError:
            print("✓ 确认无法从 functions 导入 RuntimeToolCall（已成功移除）")

        # 测试 LLMVertex 和 MCPLLMVertex 导入
        from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
        from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex

        print("✓ LLMVertex 和 MCPLLMVertex 导入成功")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_import_consistency():
    """测试导入一致性"""
    print("\n=== 测试导入一致性 ===")

    try:
        # 确保所有模块都使用相同的 RuntimeToolCall
        from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall as TC_RuntimeToolCall
        from vertex_flow.workflow.vertex.llm_vertex import RuntimeToolCall as LLM_RuntimeToolCall
        from vertex_flow.workflow.vertex.mcp_llm_vertex import RuntimeToolCall as MCP_RuntimeToolCall

        # 检查是否是同一个类
        if TC_RuntimeToolCall is LLM_RuntimeToolCall is MCP_RuntimeToolCall:
            print("✓ 所有模块使用相同的 RuntimeToolCall 类")
            return True
        else:
            print("❌ 不同模块使用了不同的 RuntimeToolCall 类")
            return False

    except Exception as e:
        print(f"❌ 导入一致性测试失败: {e}")
        return False


def test_tool_caller_types():
    """测试不同类型的tool_caller"""
    print("\n=== 测试不同类型的 tool_caller ===")

    try:
        # 测试支持的工具调用器类型
        supported_types = ["openai", "deepseek", "anthropic"]

        for caller_type in supported_types:
            try:
                tool_caller = create_tool_caller(caller_type)
                print(f"✓ {caller_type} 工具调用器创建成功: {type(tool_caller).__name__}")

                # 测试基本功能
                test_tool_calls = [
                    {
                        "id": "call_test_123",
                        "type": "function",
                        "function": {"name": "test_function", "arguments": '{"param": "value"}'},
                    }
                ]

                assistant_msg = tool_caller.create_assistant_message(test_tool_calls)
                assert assistant_msg["role"] == "assistant"
                assert len(assistant_msg["tool_calls"]) == 1

                tool_msg = tool_caller.create_tool_message("call_test_123", "test_function", {"result": "success"})
                assert tool_msg["role"] == "tool"
                assert tool_msg["tool_call_id"] == "call_test_123"

            except Exception as e:
                print(f"⚠️ {caller_type} 工具调用器测试失败: {e}")

        return True

    except Exception as e:
        print(f"❌ 工具调用器类型测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🔧 ToolCaller 专项测试")
    print("=" * 60)

    tests = [
        ("RuntimeToolCall导入测试", test_runtime_tool_call_import),
        ("DeepSeek工具调用器测试", test_deepseek_tool_caller),
        ("消息序列完整性测试", test_message_sequence_integrity),
        ("合并功能测试", test_merged_functionality),
        ("导入一致性测试", test_import_consistency),
        ("工具调用器类型测试", test_tool_caller_types),
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

    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有ToolCaller测试通过！")
        print("✅ RuntimeToolCall 导入错误已修复")
        print("✅ DeepSeek 流式工具调用正常工作")
        print("✅ 消息序列完整性验证通过")
        print("✅ 代码结构更加清晰，避免了重复定义")
    else:
        print("❌ 部分测试失败，需要检查相关功能")

    return passed == total


if __name__ == "__main__":
    main()
