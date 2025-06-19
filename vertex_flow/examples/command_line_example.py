#!/usr/bin/env python3
"""
Command Line Tool 使用示例

展示如何在 Vertex Flow 中使用命令行工具
"""

import json
import logging

from vertex_flow.workflow.constants import ENABLE_STREAM, SYSTEM, USER
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.tools.command_line import create_command_line_tool
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex


def setup_logging():
    """设置日志"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def test_command_line_tool_standalone():
    """独立测试命令行工具"""
    print("=== 独立命令行工具测试 ===")

    # 创建工具
    cmd_tool = create_command_line_tool()

    # 测试基本命令
    commands = [
        {"command": "pwd"},
        {"command": "ls -la | head -10"},
        {"command": "echo 'Hello from command line tool!'"},
        {"command": "python --version"},
        {"command": "date"},
    ]

    for cmd_input in commands:
        print(f"\n执行命令: {cmd_input['command']}")
        result = cmd_tool.execute(cmd_input)

        if result["success"]:
            print(f"✅ 成功 (退出码: {result['exit_code']})")
            if result["stdout"]:
                print(f"输出: {result['stdout'].strip()}")
        else:
            print(f"❌ 失败 (退出码: {result['exit_code']})")
            if result["stderr"]:
                print(f"错误: {result['stderr'].strip()}")


def test_command_line_with_llm():
    """结合LLM使用命令行工具"""
    print("\n=== LLM + 命令行工具集成测试 ===")

    try:
        # 初始化服务
        service = VertexFlowService()
        llm_model = service.get_chatmodel()

        if not llm_model:
            print("❌ 无法获取LLM模型，请检查配置")
            return

        # 创建工具
        cmd_tool = service.get_command_line_tool()

        # 创建LLM顶点并传入工具
        llm_vertex = LLMVertex(
            id="test_llm",
            name="测试LLM",
            model=llm_model,
            params={
                SYSTEM: "你是一个系统管理助手，可以帮助用户执行命令行操作。当用户请求执行命令时，请使用execute_command工具。",
                USER: [],
                ENABLE_STREAM: False,
            },
            tools=[cmd_tool],  # 传入工具
        )

        # 模拟用户请求
        test_messages = ["请帮我查看当前目录", "请检查Python版本", "请显示当前时间", "请列出当前目录下的前5个文件"]

        for message in test_messages:
            print(f"\n用户请求: {message}")

            # 准备输入
            inputs = {"conversation_history": [], "current_message": message}

            # 发送消息并获取响应
            try:
                response = llm_vertex.execute(inputs, {})
                print(f"AI回复: {response.get('response', '无回复')}")
            except Exception as e:
                print(f"❌ 处理失败: {e}")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")


def demo_security_features():
    """演示安全特性"""
    print("\n=== 安全特性演示 ===")

    cmd_tool = create_command_line_tool()

    # 测试被阻止的危险命令
    dangerous_commands = [
        "rm -rf /",
        "sudo rm -rf /tmp/*",
        "del /s /q C:\\",
        "format C:",
    ]

    print("测试危险命令拦截:")
    for cmd in dangerous_commands:
        print(f"\n尝试执行: {cmd}")
        result = cmd_tool.execute({"command": cmd})
        if not result["success"] and "blocked" in result["stderr"]:
            print("✅ 危险命令已被阻止")
        else:
            print("❌ 危险命令未被正确拦截")


def demo_advanced_features():
    """演示高级特性"""
    print("\n=== 高级特性演示 ===")

    cmd_tool = create_command_line_tool()

    # 演示工作目录参数
    print("1. 指定工作目录:")
    result = cmd_tool.execute({"command": "pwd", "working_dir": "/tmp"})
    print(f"结果: {result['stdout'].strip()}")

    # 演示超时设置
    print("\n2. 超时设置 (快速命令):")
    result = cmd_tool.execute({"command": "echo 'Quick command'", "timeout": 5})
    print(f"结果: {result['stdout'].strip()}")

    # 演示复合命令
    print("\n3. 复合命令:")
    result = cmd_tool.execute({"command": "echo 'Line 1' && echo 'Line 2' && echo 'Line 3'"})
    print(f"结果:\n{result['stdout']}")


def main():
    """主函数"""
    setup_logging()

    print("🛠️ Vertex Flow 命令行工具使用示例")
    print("=" * 50)

    # 独立工具测试
    test_command_line_tool_standalone()

    # 安全特性演示
    demo_security_features()

    # 高级特性演示
    demo_advanced_features()

    # LLM集成测试 (需要配置)
    try:
        test_command_line_with_llm()
    except Exception as e:
        print(f"\n⚠️ LLM集成测试跳过: {e}")
        print("请确保已正确配置 LLM 服务")

    print("\n🎉 示例演示完成!")
    print("\n💡 使用提示:")
    print("- 在 workflow_app.py 中启用 Function Tools 来使用工具")
    print("- 可以通过系统提示告诉AI何时使用命令行工具")
    print("- 工具会自动阻止一些危险命令以确保安全")


if __name__ == "__main__":
    main()
