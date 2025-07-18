#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 tool_caller 和 RuntimeToolCall 合并后的功能

验证点：
1. RuntimeToolCall 现在从 tool_caller 模块导入
2. 所有原有功能保持正常
3. 不再有重复的类定义
"""


def test_merged_functionality():
    """测试合并后的功能"""
    print("=== 测试 tool_caller 和 RuntimeToolCall 合并 ===")

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


def main():
    """主测试函数"""
    print("🔧 tool_caller 和 RuntimeToolCall 合并验证测试")
    print("=" * 50)

    tests = [
        ("合并功能测试", test_merged_functionality),
        ("导入一致性测试", test_import_consistency),
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
        print("🎉 所有测试通过！tool_caller 和 RuntimeToolCall 合并成功")
        print("✅ 代码结构更加清晰，避免了重复定义")
        print("✅ 所有功能保持正常工作")
    else:
        print("❌ 部分测试失败，需要检查合并过程")

    return passed == total


if __name__ == "__main__":
    main()
