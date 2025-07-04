#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度研究工作流综合测试
包含流式输出、索引修复、循环增强等功能测试
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import ENABLE_STREAM, SYSTEM, USER
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.while_vertex import WhileVertex
from vertex_flow.workflow.vertex.while_vertex_group import WhileVertexGroup
from vertex_flow.workflow.workflow import Workflow

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


class MockResponse:
    """模拟响应对象"""

    def __init__(self, content):
        self.choices = [MockChoice(content)]


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


def create_mock_deep_research_workflow():
    """创建模拟的深度研究工作流"""
    # 创建模拟模型
    mock_model = MockChatModel()

    # 创建工作流
    workflow = Workflow(id="deep_research_workflow", name="深度研究工作流")

    # 创建LLM顶点
    llm_vertex = LLMVertex(
        id="research_llm",
        params={
            "model": mock_model,
            SYSTEM: "你是一个深度研究助手",
            USER: ["请进行深度研究"],
            ENABLE_STREAM: True,
        },
    )

    # 添加到工作流
    workflow.add_vertex(llm_vertex)

    return workflow


def test_deep_research_streaming():
    """测试深度研究工作流的流式输出功能"""
    print("=== 测试深度研究工作流流式输出 ===")

    try:
        # 创建工作流
        workflow = create_mock_deep_research_workflow()

        # 收集流式事件
        streaming_events = []

        def on_streaming_event(event):
            """处理流式事件"""
            streaming_events.append(event)
            print(f"收到流式事件: {event}")

        # 订阅流式事件
        from vertex_flow.workflow.event_channel import EventType
        workflow.subscribe(EventType.MESSAGES, on_streaming_event)

        # 执行工作流
        context = WorkflowContext()
        result = workflow.execute({"query": "测试查询"}, context)

        print(f"工作流执行结果: {result}")
        print(f"收到的流式事件数量: {len(streaming_events)}")

        # 验证流式事件
        assert len(streaming_events) > 0, "应该收到流式事件"
        print("✅ 深度研究工作流流式输出测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_deep_research_workflow_index_fix():
    """测试深度研究工作流循环索引超出范围问题的修复"""
    print("\n=== 测试深度研究工作流索引修复 ===")

    try:
        # 模拟步骤数据
        steps = [
            {"step_name": "数据收集", "description": "收集相关数据"},
            {"step_name": "数据分析", "description": "分析收集的数据"},
            {"step_name": "结论生成", "description": "生成研究结论"},
        ]

        def mock_step_prepare_task(inputs, context=None):
            """模拟步骤准备任务"""
            steps = inputs.get("steps", [])
            iteration_index = inputs.get("iteration_index", 0)

            print(f"准备步骤: iteration_index={iteration_index}, total_steps={len(steps)}")

            # 检查索引是否超出范围
            if iteration_index >= len(steps):
                print(f"⚠️ 索引超出范围: {iteration_index} >= {len(steps)}，停止执行")
                return {"current_step": None, "completed": True}

            current_step = steps[iteration_index]
            print(f"执行步骤 {iteration_index + 1}/{len(steps)}: {current_step['step_name']}")

            return {
                "current_step": current_step,
                "step_index": iteration_index,
                "steps": steps,
                "completed": False,
            }

        def mock_step_condition_task(inputs, context=None):
            """模拟步骤条件检查"""
            completed = inputs.get("completed", False)
            steps = inputs.get("steps", [])
            iteration_index = inputs.get("iteration_index", 0)

            # 如果已完成或索引超出范围，则停止循环
            should_continue = not completed and iteration_index < len(steps)
            print(
                f"条件检查: completed={completed}, iteration_index={iteration_index}, should_continue={should_continue}"
            )

            return should_continue

        # 创建While顶点
        while_vertex = WhileVertex(
            id="research_steps",
            name="研究步骤循环",
            execute_task=mock_step_prepare_task,
            condition_task=mock_step_condition_task,
        )

        # 执行循环
        initial_inputs = {"steps": steps}
        result = while_vertex.while_loop(initial_inputs)

        print(f"循环执行结果: {result}")

        # 验证结果
        assert result["iteration_count"] == len(steps), f"期望迭代{len(steps)}次，实际迭代{result['iteration_count']}次"
        assert result.get("completed") == True, "循环应该正常完成"

        print("✅ 深度研究工作流索引修复测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_deep_research_workflow_index_enhancement():
    """测试深度研究工作流的循环索引增强功能"""
    print("\n=== 测试深度研究工作流索引增强 ===")

    try:
        # 记录每次迭代的索引信息
        iteration_logs = []

        def mock_step_prepare_task(inputs, context=None):
            """模拟步骤准备任务，验证iteration_index自动注入"""
            iteration_index = inputs.get("iteration_index")
            steps = inputs.get("steps", [])

            print(f"步骤准备: iteration_index={iteration_index}, total_steps={len(steps)}")

            # 验证iteration_index存在
            assert iteration_index is not None, "iteration_index应该被自动注入"

            # 记录迭代信息
            iteration_logs.append({"iteration": iteration_index, "step_count": len(steps)})

            # 检查是否完成
            if iteration_index >= len(steps):
                return {"completed": True}

            current_step = steps[iteration_index]
            return {
                "current_step": current_step,
                "steps": steps,
                "completed": False,
            }

        def mock_step_condition_task(inputs, context=None):
            """模拟步骤条件检查"""
            completed = inputs.get("completed", False)
            iteration_index = inputs.get("iteration_index", 0)
            steps = inputs.get("steps", [])

            should_continue = not completed and iteration_index < len(steps)
            print(f"条件检查: iteration_index={iteration_index}, should_continue={should_continue}")

            return should_continue

        # 创建测试步骤
        steps = [
            {"step_name": "初始化研究", "description": "设置研究参数"},
            {"step_name": "执行研究", "description": "进行深度研究"},
            {"step_name": "总结结果", "description": "整理研究结果"},
        ]

        # 创建While顶点
        while_vertex = WhileVertex(
            id="enhanced_research",
            name="增强研究循环",
            execute_task=mock_step_prepare_task,
            condition_task=mock_step_condition_task,
        )

        # 执行循环
        initial_inputs = {"steps": steps}
        result = while_vertex.while_loop(initial_inputs)

        print(f"循环执行结果: {result}")
        print(f"迭代日志: {iteration_logs}")

        # 验证结果
        expected_iterations = len(steps)
        assert result["iteration_count"] == expected_iterations, f"期望迭代{expected_iterations}次"
        assert len(iteration_logs) == expected_iterations, f"期望记录{expected_iterations}次迭代"

        # 验证每次迭代的索引递增
        for i, log in enumerate(iteration_logs):
            assert log["iteration"] == i, f"第{i}次迭代的索引应该是{i}"

        print("✅ 深度研究工作流索引增强测试通过")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始深度研究工作流综合测试...\n")

    tests = [
        test_deep_research_streaming,
        test_deep_research_workflow_index_fix,
        test_deep_research_workflow_index_enhancement,
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
        print("\n🎉 所有深度研究工作流测试通过！")
        return True
    else:
        print(f"\n💥 有 {failed} 个测试失败！")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
