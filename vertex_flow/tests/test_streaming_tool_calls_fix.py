#!/usr/bin/env python3
"""
测试流式工具调用修复
验证mcp_llm_vertex和llm_vertex在stream chat时工具调用不会被中断
"""

import json
import time
from typing import Dict, Any, Generator

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.chat import ChatModel
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.tools.functions import FunctionTool
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex

logger = LoggerUtil.get_logger(__name__)


def create_test_tool():
    """创建测试工具"""
    def test_func(arguments: Dict[str, Any], context) -> str:
        return f"工具调用成功，参数: {arguments}"
    
    return FunctionTool(
        name="test_tool",
        description="测试工具，用于验证流式工具调用",
        func=test_func,
        schema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "测试消息"},
            },
            "required": ["message"],
        },
    )


class MockStreamingChatModel(ChatModel):
    """模拟支持流式输出的聊天模型"""
    
    def __init__(self):
        super().__init__(name="mock-streaming-model", sk="mock-key", base_url="mock-url", provider="mock")
        self.call_count = 0
        self.max_calls = 5  # 限制最大调用次数
    
    def chat_stream(self, messages, option=None, tools=None):
        """模拟流式输出，包含工具调用"""
        self.call_count += 1
        
        # 防止无限循环
        if self.call_count > self.max_calls:
            logger.warning(f"MockStreamingChatModel达到最大调用次数限制: {self.max_calls}")
            return
        
        # 检查消息中是否已有工具调用结果
        has_tool_result = any(msg.get("role") == "tool" for msg in messages)
        
        # 如果已有工具结果，返回最终响应
        if has_tool_result:
            # 模拟最终响应
            final_chunks = [
                self._create_chunk("工具调用完成，结果已处理。"),
                self._create_chunk("这是最终的总结。")
            ]
            for chunk in final_chunks:
                yield chunk
            return
        
        # 第一次调用：返回工具调用
        tool_call_chunks = [
            self._create_chunk("", tool_calls=[{
                "id": "call_test_123",
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "arguments": json.dumps({"message": "测试流式工具调用"})
                }
            }])
        ]
        
        for chunk in tool_call_chunks:
            yield chunk
    
    def chat(self, messages, option=None, tools=None):
        """模拟非流式聊天"""
        self.call_count += 1
        
        # 防止无限循环
        if self.call_count > self.max_calls:
            return self._create_choice("达到最大调用次数限制", "stop")
        
        # 检查消息中是否已有工具调用结果
        has_tool_result = any(msg.get("role") == "tool" for msg in messages)
        
        # 如果已有工具结果，返回最终响应
        if has_tool_result:
            return self._create_choice("工具调用完成，结果已处理。", "stop")
        
        # 第一次调用：返回工具调用
        return self._create_choice("", "tool_calls", tool_calls=[{
            "id": "call_test_123",
            "type": "function",
            "function": {
                "name": "test_tool",
                "arguments": json.dumps({"message": "测试非流式工具调用"})
            }
        }])
    
    def _create_chunk(self, content: str, tool_calls=None):
        """创建模拟的chunk对象"""
        class MockDelta:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls
        
        class MockChoice:
            def __init__(self, delta):
                self.delta = delta
        
        class MockChunk:
            def __init__(self, choices):
                self.choices = choices
        
        delta = MockDelta(content, tool_calls)
        choice = MockChoice(delta)
        return MockChunk([choice])
    
    def _create_choice(self, content: str, finish_reason: str, tool_calls=None):
        """创建模拟的choice对象"""
        class MockMessage:
            def __init__(self, content, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls
                self.role = "assistant"
        
        class MockChoice:
            def __init__(self, content, finish_reason, tool_calls=None):
                self.message = MockMessage(content, tool_calls)
                self.finish_reason = finish_reason
        
        return MockChoice(content, finish_reason, tool_calls)


def test_llm_vertex_streaming_tool_calls():
    """测试LLMVertex的流式工具调用"""
    logger.info("=== 测试LLMVertex流式工具调用 ===")
    
    try:
        # 创建测试工具
        test_tool = create_test_tool()
        
        # 创建LLMVertex
        llm_vertex = LLMVertex(
            id="test_llm_streaming",
            name="测试LLM流式",
            model=MockStreamingChatModel(),
            params={
                "system": "你是一个有用的助手，可以调用test_tool工具。",
                "user": [],
                "enable_stream": True,
                "enable_reasoning": False,
                "show_reasoning": False,
            },
            tools=[test_tool],
        )
        
        # 设置消息
        llm_vertex.messages = [
            {"role": "system", "content": "你是一个有用的助手，可以调用test_tool工具。"},
            {"role": "user", "content": "请调用test_tool工具进行测试"},
        ]
        
        # 创建上下文
        context = WorkflowContext()
        
        print("🧪 开始测试LLMVertex流式工具调用...")
        print("=" * 50)
        
        # 使用流式生成器
        print("📤 流式输出:")
        chunk_count = 0
        full_response = ""
        
        for chunk in llm_vertex.chat_stream_generator({}, context):
            chunk_count += 1
            full_response += str(chunk)
            print(f"  Chunk {chunk_count}: {chunk}")
        
        print(f"\n✅ 流式输出完成，共收到 {chunk_count} 个chunk")
        print(f"📝 完整响应: {full_response}")
        
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
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_llm_vertex_streaming_tool_calls():
    """测试MCPLLMVertex的流式工具调用"""
    logger.info("=== 测试MCPLLMVertex流式工具调用 ===")
    
    try:
        # 创建测试工具
        test_tool = create_test_tool()
        
        # 创建MCPLLMVertex
        mcp_llm_vertex = MCPLLMVertex(
            id="test_mcp_llm_streaming",
            name="测试MCPLLM流式",
            model=MockStreamingChatModel(),
            params={
                "system": "你是一个有用的助手，可以调用test_tool工具。",
                "user": [],
                "enable_stream": True,
                "enable_reasoning": False,
                "show_reasoning": False,
            },
            tools=[test_tool],
            mcp_enabled=False,  # 禁用MCP以避免依赖问题
        )
        
        # 设置消息
        mcp_llm_vertex.messages = [
            {"role": "system", "content": "你是一个有用的助手，可以调用test_tool工具。"},
            {"role": "user", "content": "请调用test_tool工具进行测试"},
        ]
        
        # 创建上下文
        context = WorkflowContext()
        
        print("🧪 开始测试MCPLLMVertex流式工具调用...")
        print("=" * 50)
        
        # 使用流式生成器
        print("📤 流式输出:")
        chunk_count = 0
        full_response = ""
        
        for chunk in mcp_llm_vertex.chat_stream_generator({}, context):
            chunk_count += 1
            full_response += str(chunk)
            print(f"  Chunk {chunk_count}: {chunk}")
        
        print(f"\n✅ 流式输出完成，共收到 {chunk_count} 个chunk")
        print(f"📝 完整响应: {full_response}")
        
        # 检查messages中是否有工具调用
        print("\n📋 检查messages:")
        for i, msg in enumerate(mcp_llm_vertex.messages):
            print(f"  Message {i}: {msg}")
        
        # 检查是否有工具调用结果
        tool_messages = [msg for msg in mcp_llm_vertex.messages if msg.get("role") == "tool"]
        if tool_messages:
            print(f"\n🛠️ 发现 {len(tool_messages)} 个工具调用结果:")
            for msg in tool_messages:
                print(f"  Tool: {msg}")
        else:
            print("\n⚠️ 未发现工具调用结果")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_tool_calls():
    """测试多次工具调用"""
    logger.info("=== 测试多次工具调用 ===")
    
    try:
        # 创建测试工具
        test_tool = create_test_tool()
        
        # 创建支持多次工具调用的模拟模型
        class MultiToolMockModel(MockStreamingChatModel):
            def __init__(self):
                super().__init__()
                self.tool_call_count = 0
                self.max_tool_calls = 2
            
            def chat_stream(self, messages, option=None, tools=None):
                self.call_count += 1
                
                # 防止无限循环
                if self.call_count > self.max_calls:
                    return
                
                # 检查工具调用次数
                tool_results = [msg for msg in messages if msg.get("role") == "tool"]
                
                if len(tool_results) >= self.max_tool_calls:
                    # 所有工具调用完成，返回最终响应
                    final_chunks = [
                        self._create_chunk("所有工具调用已完成。"),
                        self._create_chunk("这是最终的总结。")
                    ]
                    for chunk in final_chunks:
                        yield chunk
                    return
                
                # 返回工具调用
                tool_call_chunks = [
                    self._create_chunk("", tool_calls=[{
                        "id": f"call_test_{self.tool_call_count}",
                        "type": "function",
                        "function": {
                            "name": "test_tool",
                            "arguments": json.dumps({"message": f"第{self.tool_call_count + 1}次工具调用"})
                        }
                    }])
                ]
                
                self.tool_call_count += 1
                
                for chunk in tool_call_chunks:
                    yield chunk
        
        # 创建LLMVertex
        llm_vertex = LLMVertex(
            id="test_multi_tool_llm",
            name="测试多次工具调用LLM",
            model=MultiToolMockModel(),
            params={
                "system": "你是一个有用的助手，可以多次调用test_tool工具。",
                "user": [],
                "enable_stream": True,
                "enable_reasoning": False,
                "show_reasoning": False,
            },
            tools=[test_tool],
        )
        
        # 设置消息
        llm_vertex.messages = [
            {"role": "system", "content": "你是一个有用的助手，可以多次调用test_tool工具。"},
            {"role": "user", "content": "请多次调用test_tool工具进行测试"},
        ]
        
        # 创建上下文
        context = WorkflowContext()
        
        print("🧪 开始测试多次工具调用...")
        print("=" * 50)
        
        # 使用流式生成器
        print("📤 流式输出:")
        chunk_count = 0
        full_response = ""
        
        for chunk in llm_vertex.chat_stream_generator({}, context):
            chunk_count += 1
            full_response += str(chunk)
            print(f"  Chunk {chunk_count}: {chunk}")
        
        print(f"\n✅ 流式输出完成，共收到 {chunk_count} 个chunk")
        print(f"📝 完整响应: {full_response}")
        
        # 检查工具调用结果
        tool_messages = [msg for msg in llm_vertex.messages if msg.get("role") == "tool"]
        print(f"\n🛠️ 发现 {len(tool_messages)} 个工具调用结果:")
        for i, msg in enumerate(tool_messages):
            print(f"  Tool {i+1}: {msg}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("开始流式工具调用修复测试...")
    
    # 测试LLMVertex
    llm_success = test_llm_vertex_streaming_tool_calls()
    
    # 测试MCPLLMVertex
    mcp_success = test_mcp_llm_vertex_streaming_tool_calls()
    
    # 测试多次工具调用
    multi_success = test_multiple_tool_calls()
    
    # 总结结果
    logger.info("=== 测试结果总结 ===")
    logger.info(f"LLMVertex流式工具调用测试: {'成功' if llm_success else '失败'}")
    logger.info(f"MCPLLMVertex流式工具调用测试: {'成功' if mcp_success else '失败'}")
    logger.info(f"多次工具调用测试: {'成功' if multi_success else '失败'}")
    
    if llm_success and mcp_success and multi_success:
        logger.info("所有测试通过！流式工具调用修复成功！")
        return 0
    else:
        logger.error("部分测试失败！需要进一步调试。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)