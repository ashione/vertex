#!/usr/bin/env python3
"""
测试MCP工具调用集成和异常处理
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.utils.logger import LoggerUtil

logger = LoggerUtil.get_logger(__name__)

class MockChatModel:
    """模拟聊天模型，用于测试MCP工具调用"""
    
    def __init__(self):
        self.call_count = 0
        self.max_calls = 3  # 限制最大调用次数，防止无限循环
    
    def chat_stream(self, messages, **kwargs):
        """模拟流式聊天，包含工具调用"""
        self.call_count += 1
        
        # 防止无限循环
        if self.call_count > self.max_calls:
            logger.warning(f"MockChatModel达到最大调用次数限制: {self.max_calls}")
            return
        
        # 创建模拟的chunk对象
        class MockChoice:
            def __init__(self, delta, finish_reason=None):
                self.delta = delta
                self.finish_reason = finish_reason
        
        class MockDelta:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls
        
        class MockChunk:
            def __init__(self, choices):
                self.choices = choices
        
        # 检查消息中是否已有工具调用结果
        has_tool_result = any(msg.get("role") == "tool" for msg in messages)
        
        # 第一次调用且没有工具结果：返回工具调用
        if self.call_count == 1 and not has_tool_result:
            tool_calls = [{
                "id": "call_test_123",
                "type": "function",
                "function": {
                    "name": "everything_echo",  # 修正工具名称
                    "arguments": json.dumps({"message": "Test MCP call"})
                }
            }]
            delta = MockDelta(tool_calls=tool_calls)
            choice = MockChoice(delta, "tool_calls")
            yield MockChunk([choice])
        
        # 有工具结果或后续调用：返回最终响应
        else:
            delta = MockDelta(content="工具调用完成，结果已处理。")
            choice = MockChoice(delta, "stop")
            yield MockChunk([choice])
    
    def chat(self, messages, **kwargs):
        """模拟非流式聊天"""
        self.call_count += 1
        
        # 防止无限循环
        if self.call_count > self.max_calls:
            logger.warning(f"MockChatModel达到最大调用次数限制: {self.max_calls}")
            # 创建模拟的choice对象
            class MockChoice:
                def __init__(self):
                    self.finish_reason = "stop"
                    self.message = type('MockMessage', (), {
                        'content': "达到最大调用次数限制",
                        'role': 'assistant'
                    })()
            return MockChoice()
        
        # 检查消息中是否已有工具调用结果
        has_tool_result = any(msg.get("role") == "tool" for msg in messages)
        
        # 如果已有工具结果，返回最终响应
        if has_tool_result:
            class MockChoice:
                def __init__(self):
                    self.finish_reason = "stop"
                    self.message = type('MockMessage', (), {
                        'content': "工具调用完成，结果已处理。",
                        'role': 'assistant'
                    })()
            return MockChoice()
        
        # 第一次调用：返回工具调用
        class MockChoice:
            def __init__(self):
                self.finish_reason = "tool_calls"
                self.message = type('MockMessage', (), {
                    'content': "",
                    'role': 'assistant',
                    'tool_calls': [{
                        "id": "call_test_123",
                        "type": "function",
                        "function": {
                            "name": "everything_echo",
                            "arguments": json.dumps({"message": "Test MCP call"})
                        }
                    }]
                })()
        return MockChoice()

def test_mcp_tool_calls_streaming():
    """测试流式模式下的MCP工具调用"""
    logger.info("=== 测试流式MCP工具调用 ===")
    
    try:
        # 创建上下文和LLM实例
        context = WorkflowContext()
        llm_vertex = MCPLLMVertex(
            id="test-mcp-llm",
            name="test-mcp-llm",
            model=MockChatModel(),
            params={"system": "You are a helpful assistant.", "user": []}
        )
        
        # 初始化MCP配置
        mcp_config = {
            "enabled": True,
            "clients": {
                "everything": {
                    "enabled": True,
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-everything"]
                }
            }
        }
        
        # 初始化MCP
        from vertex_flow.workflow.mcp_manager import get_mcp_manager
        mcp_manager = get_mcp_manager()
        mcp_manager.initialize(mcp_config)
        
        # 测试流式调用
        messages = [{"role": "user", "content": "请使用echo工具测试一下"}]
        
        logger.info("开始流式调用...")
        response_content = ""
        
        for chunk in llm_vertex.chat_stream_generator(messages):
            if chunk.get("content"):
                response_content += chunk["content"]
                logger.info(f"收到内容: {chunk['content']}")
            
            if chunk.get("finish_reason") == "stop":
                logger.info("流式调用完成")
                break
        
        # 检查token统计
        token_usage = llm_vertex.get_token_usage()
        logger.info(f"Token使用情况: {token_usage}")
        
        # 检查消息历史
        logger.info(f"消息数量: {len(llm_vertex.messages)}")
        for i, msg in enumerate(llm_vertex.messages):
            logger.info(f"消息 {i}: {msg.get('role')} - {msg.get('content', 'N/A')[:50]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"流式MCP工具调用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mcp_tool_calls_non_streaming():
    """测试非流式模式下的MCP工具调用"""
    logger.info("=== 测试非流式MCP工具调用 ===")
    
    try:
        # 创建上下文和LLM实例
        context = WorkflowContext()
        llm_vertex = MCPLLMVertex(
            id="test-mcp-llm-non-stream",
            name="test-mcp-llm-non-stream",
            model=MockChatModel(),
            params={"system": "You are a helpful assistant.", "user": []}
        )
        
        # 测试非流式调用
        messages = [{"role": "user", "content": "请回答一个简单问题"}]
        
        logger.info("开始非流式调用...")
        response = llm_vertex.chat(messages)
        
        logger.info(f"响应: {response}")
        
        # 检查token统计
        token_usage = llm_vertex.get_token_usage()
        logger.info(f"Token使用情况: {token_usage}")
        
        return True
        
    except Exception as e:
        logger.error(f"非流式MCP工具调用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    logger.info("开始MCP集成测试...")
    
    # 测试流式调用
    streaming_success = test_mcp_tool_calls_streaming()
    
    # 测试非流式调用
    non_streaming_success = test_mcp_tool_calls_non_streaming()
    
    # 总结结果
    logger.info("=== 测试结果总结 ===")
    logger.info(f"流式调用测试: {'成功' if streaming_success else '失败'}")
    logger.info(f"非流式调用测试: {'成功' if non_streaming_success else '失败'}")
    
    if streaming_success and non_streaming_success:
        logger.info("所有测试通过！")
        return 0
    else:
        logger.error("部分测试失败！")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)