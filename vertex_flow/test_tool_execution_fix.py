#!/usr/bin/env python3
"""
测试工具调用执行修复
"""

import logging
import os
import sys
from typing import Any, Dict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow.app.workflow_app import WorkflowChatApp
from workflow.tools.tool_manager import FunctionTool
from workflow.vertex.llm_vertex import LLMVertex
from workflow.vertex.mcp_llm_vertex import MCPLLMVertex
from workflow.workflow import WorkflowContext

# 设置日志级别
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_test_tool():
    """创建一个简单的测试工具"""

    def test_function(text: str) -> str:
        """测试函数，返回处理后的文本"""
        return f"工具处理结果: {text}"

    return FunctionTool(
        name="test_function",
        description="一个测试工具函数",
        func=test_function,
        schema={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "要处理的文本"}},
            "required": ["text"],
        },
    )


def test_tool_execution():
    """测试工具执行是否正常工作"""
    print("\n=== 测试工具调用执行修复 ===")

    try:
        # 创建应用实例
        app = WorkflowChatApp()

        # 创建测试工具
        test_tool = create_test_tool()

        # 设置消息，明确要求使用工具
        messages = [{"role": "user", "content": "请使用test_function工具处理文本'hello world'"}]

        print(f"发送消息: {messages[0]['content']}")

        # 使用流式聊天
        chunk_count = 0
        response_content = ""

        for chunk in app.chat_with_vertex(
            messages=messages,
            system_prompt="你是一个智能助手，可以调用工具来帮助用户",
            tools=[test_tool],
            enable_stream=True,
        ):
            chunk_count += 1
            if chunk:
                response_content += str(chunk)
                print(f"收到chunk {chunk_count}: {chunk}")

        print(f"\n总共收到 {chunk_count} 个响应块")
        print(f"最终回复长度: {len(response_content)} 字符")
        print(f"最终回复内容: {response_content}")

        # 检查是否有工具调用和执行
        if chunk_count > 0 and response_content:
            print("\n✅ 流式输出功能正常工作")
            if "工具处理结果" in response_content:
                print("✅ 工具调用执行成功")
                return True
            else:
                print("❌ 工具调用可能没有被执行")
                return False
        else:
            print("❌ 流式输出失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_tool_execution()
    sys.exit(0 if success else 1)
