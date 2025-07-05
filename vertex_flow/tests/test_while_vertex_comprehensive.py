#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
While顶点综合功能测试
包含执行顺序、索引增强、流式输出修复等功能测试
"""

import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import ENABLE_STREAM, ITERATION_INDEX_KEY, SYSTEM, USER
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex.function_vertex import FunctionVertex
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.while_vertex import WhileVertex
from vertex_flow.workflow.vertex.while_vertex_group import WhileVertexGroup
from vertex_flow.workflow.workflow import Workflow

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = LoggerUtil.get_logger()


class MockMessage:
    """模拟消息对象"""

    def __init__(self, content):
        self.content = content


class MockChoice:
    """模拟选择对象"""

    def __init__(self, content, finish_reason="stop"):
        self.message = MockMessage(content)
        self.finish_reason = finish_reason


class MockChatModel:
    """模拟聊天模型"""

    def __init__(self):
        self.responses = ["这是一个测试响应"]
        self.response_index = 0

    def chat(self, messages, **kwargs):
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        return MockChoice(response)

    def chat_stream(self, messages, **kwargs):
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        # 模拟流式输出
        for char in response:
            yield MockChoice(char)

    def model_name(self):
        return "MockModel"


def test_while_vertex_execution_order():
    """测试WhileVertex的执行顺序问题，验证循环索引超出范围的情况"""
    print("=== 测试WhileVertex执行顺序问题 ===")

    try:
        # 使用简单的计数器测试，避免复杂的步骤逻辑
        execution_log = []

        def execute_task(inputs, context=None):
            """简单的计数执行任务"""
            count = inputs.get("count", 0)
            iteration_index = inputs.get(ITERATION_INDEX_KEY, 0)

            log_entry = {
                "iteration_index": iteration_index,
                "count": count,
                "index_in_range": iteration_index < 3,  # 预期执行3次
            }
            execution_log.append(log_entry)

            print(f"✅ 执行任务: iteration_index={iteration_index}, count={count}")

            # 简单地增加计数
            new_count = count + 1
            return {"count": new_count}

        def condition_task(inputs, context=None):
            """简单的循环条件检查"""
            count = inputs.get("count", 0)
            should_continue = count < 3  # 执行3次

            print(f"🔍 条件检查: count={count}, should_continue={should_continue}")
            return should_continue

        # 创建WhileVertex
        while_vertex = WhileVertex(
            id="execution_order_test",
            name="执行顺序测试",
            execute_task=execute_task,
            condition_task=condition_task,
        )

        # 执行循环
        result = while_vertex.while_loop({"count": 0})

        print(f"\n执行结果: {result}")
        print(f"总迭代次数: {result['iteration_count']}")
        print(f"预期迭代次数: 3")
        print(f"最终计数: {result.get('final_inputs', {}).get('count', 0)}")

        # 验证结果
        expected_iterations = 3
        actual_iterations = result["iteration_count"]
        final_count = result.get("final_inputs", {}).get("count", 0)

        if actual_iterations == expected_iterations and final_count == expected_iterations:
            print("\n✅ 执行顺序测试通过")
            return True
        else:
            print(f"\n❌ 执行顺序测试失败: 期望{expected_iterations}次迭代，实际{actual_iterations}次")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_while_vertex_index_enhancement():
    """测试WhileVertex的循环索引自动注入功能"""
    print("\n=== 测试WhileVertex索引自动注入功能 ===")

    try:
        # 记录每次迭代的索引信息
        iteration_logs = []

        def execute_task_with_index(inputs, context=None):
            """测试execute_task，验证索引信息是否正确注入"""
            print(f"执行任务，输入keys: {list(inputs.keys())}")

            # 验证索引键存在
            iteration_index = inputs.get(ITERATION_INDEX_KEY)
            print(f"  - {ITERATION_INDEX_KEY}: {iteration_index}")

            # 验证索引信息存在
            assert iteration_index is not None, f"{ITERATION_INDEX_KEY} 应该存在"

            # 记录迭代信息
            iteration_logs.append({"iteration": iteration_index, "input_count": inputs.get("count", 0)})

            # 返回更新的计数
            new_count = inputs.get("count", 0) + 1
            print(f"  - 返回新计数: {new_count}")
            return {"count": new_count}

        def condition_task(inputs, context=None):
            """循环条件：执行3次"""
            count = inputs.get("count", 0)
            should_continue = count < 3
            print(f"检查循环条件: count={count}, should_continue={should_continue}")
            return should_continue

        # 创建WhileVertex
        while_vertex = WhileVertex(
            id="index_enhancement_test",
            name="索引增强测试",
            execute_task=execute_task_with_index,
            condition_task=condition_task,
        )

        # 执行循环
        print("开始执行循环...")
        result = while_vertex.while_loop({"count": 0})

        print(f"\n循环执行结果: {result}")
        print(f"迭代日志: {iteration_logs}")

        # 验证结果
        expected_iterations = 3
        assert (
            result["iteration_count"] == expected_iterations
        ), f"期望迭代{expected_iterations}次，实际迭代{result['iteration_count']}次"
        assert (
            len(iteration_logs) == expected_iterations
        ), f"期望记录{expected_iterations}次迭代，实际记录{len(iteration_logs)}次"

        # 验证每次迭代的索引递增
        for i, log in enumerate(iteration_logs):
            assert log["iteration"] == i, f"第{i}次迭代的索引应该是{i}，实际是{log['iteration']}"

        print("✅ WhileVertex索引自动注入功能测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_while_vertex_api_methods():
    """测试WhileVertex的索引获取API方法"""
    print("\n=== 测试WhileVertex索引获取API方法 ===")

    try:

        def simple_task(inputs, context=None):
            return {"result": "ok"}

        def simple_condition(inputs, context=None):
            return inputs.get("count", 0) < 3

        while_vertex = WhileVertex(
            id="api_test",
            name="API测试",
            execute_task=simple_task,
            condition_task=simple_condition,
        )

        # 测试初始状态
        assert while_vertex.get_iteration_index() == 0
        print("✅ 初始索引为0")

        # 手动设置索引并测试
        while_vertex.set_iteration_index(5)
        assert while_vertex.get_iteration_index() == 5
        print("✅ 手动设置索引为5")

        # 测试增量方法
        while_vertex.increment_iteration_index()
        assert while_vertex.get_iteration_index() == 6
        print("✅ 索引增量方法正常")

        print("✅ WhileVertex索引获取API方法测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_while_streaming_fix():
    """测试while循环内部的流式输出功能修复"""
    print("\n=== 测试while循环流式输出修复 ===")

    try:
        # 创建模拟模型
        mock_model = MockChatModel()

        # 收集流式事件
        streaming_events = []

        def on_streaming_event(event):
            """处理流式事件"""
            streaming_events.append(event)
            print(f"收到流式事件: {event}")

        # 创建包含LLM的工作流
        workflow = Workflow()

        # 创建LLM顶点
        llm_vertex = LLMVertex(
            id="streaming_llm",
            params={
                "model": mock_model,
                SYSTEM: "你是一个测试助手",
                USER: ["请回答问题"],
                ENABLE_STREAM: True,
            },
        )

        # 创建While顶点组
        def while_execute_task(inputs, context=None):
            """While循环执行任务"""
            iteration_index = inputs.get(ITERATION_INDEX_KEY, 0)
            print(f"While循环执行，迭代: {iteration_index}")

            # 执行LLM顶点
            llm_result = llm_vertex.execute(inputs, context)

            return {"llm_result": llm_result, "count": inputs.get("count", 0) + 1}

        def while_condition_task(inputs, context=None):
            """While循环条件"""
            count = inputs.get("count", 0)
            return count < 2  # 执行2次

        while_vertex = WhileVertex(
            id="streaming_while",
            name="流式While循环",
            execute_task=while_execute_task,
            condition_task=while_condition_task,
        )

        # 添加到工作流
        workflow.add_vertex(while_vertex)

        # 订阅流式事件
        workflow.subscribe_streaming_event(on_streaming_event)

        # 执行工作流
        context = WorkflowContext()
        result = workflow.execute({"query": "测试查询", "count": 0}, context)

        print(f"工作流执行结果: {result}")
        print(f"收到的流式事件数量: {len(streaming_events)}")

        # 验证流式事件
        if len(streaming_events) > 0:
            print("✅ while循环流式输出修复测试通过")
            return True
        else:
            print("❌ 未收到流式事件")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_constants_import():
    """测试常量导入是否正确"""
    print("\n=== 测试常量导入 ===")

    try:
        # 验证常量值
        assert ITERATION_INDEX_KEY == "iteration_index"
        print(f"常量值验证: {ITERATION_INDEX_KEY}")
        print("✅ 常量导入测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始While顶点综合功能测试...\n")

    tests = [
        test_constants_import,
        test_while_vertex_api_methods,
        test_while_vertex_execution_order,
        test_while_vertex_index_enhancement,
        test_while_streaming_fix,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 异常: {e}")
            failed += 1

    print(f"\n=== 测试结果汇总 ===")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有While顶点功能测试通过！")
        return True
    else:
        print(f"\n💥 有 {failed} 个测试失败！")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
