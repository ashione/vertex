import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from vertex_flow.workflow.context import WorkflowContext


class RuntimeToolCall:
    """统一处理tool_call的格式转换，将dict格式转换为对象格式"""

    def __init__(self, data):
        """
        初始化RuntimeToolCall

        Args:
            data: dict格式的tool_call数据，包含id、type、function等信息
        """
        self.id = data.get("id", "")
        self.type = data.get("type", "function")
        self.function = type(
            "RuntimeFunction", (), {"name": data["function"]["name"], "arguments": data["function"]["arguments"]}
        )()

    @staticmethod
    def normalize(tool_call):
        """
        将tool_call统一转换为RuntimeToolCall对象格式

        Args:
            tool_call: 可能是dict或对象格式的tool_call

        Returns:
            RuntimeToolCall: 统一的对象格式
        """
        if isinstance(tool_call, dict):
            return RuntimeToolCall(tool_call)
        else:
            # 已经是对象格式，直接返回
            return tool_call

    @staticmethod
    def normalize_list(tool_calls):
        """
        将tool_calls列表统一转换为RuntimeToolCall对象格式

        Args:
            tool_calls: tool_call列表

        Returns:
            list: RuntimeToolCall对象列表
        """
        return [RuntimeToolCall.normalize(tc) for tc in tool_calls]


class ToolCaller(ABC):
    """抽象的工具调用器基类，用于适配不同模型的工具调用处理"""

    def __init__(self, tools: List[Any] = None):
        self.tools = tools or []

    @abstractmethod
    def can_handle_streaming(self) -> bool:
        """检查是否支持流式工具调用"""
        pass

    @abstractmethod
    def extract_tool_calls_from_stream(self, chunk: Any) -> List[Dict[str, Any]]:
        """从流式响应中提取工具调用"""
        pass

    @abstractmethod
    def extract_tool_calls_from_choice(self, choice: Any) -> List[Dict[str, Any]]:
        """从非流式响应中提取工具调用"""
        pass

    @abstractmethod
    def is_tool_call_chunk(self, chunk: Any) -> bool:
        """检查是否为工具调用分片"""
        pass

    @abstractmethod
    def merge_tool_call_fragments(self, fragments: List[Any]) -> List[Dict[str, Any]]:
        """合并工具调用分片"""
        pass

    @abstractmethod
    def create_assistant_message(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建助手消息"""
        pass

    @abstractmethod
    def create_tool_message(self, tool_call_id: str, tool_name: str, content: Any) -> Dict[str, Any]:
        """创建工具响应消息"""
        pass

    async def execute_tool_calls(
        self, tool_calls: List[Dict[str, Any]], context: Optional[WorkflowContext] = None
    ) -> List[Dict[str, Any]]:
        """执行工具调用并返回工具响应消息列表"""
        tool_messages = []

        async def call_tool(tool_call: Dict[str, Any], context: Optional[WorkflowContext] = None):
            tool_call_id = tool_call.get("id", "")
            tool_name = tool_call.get("function", {}).get("name", "")
            arguments_str = tool_call.get("function", {}).get("arguments", "{}")

            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}

            # 查找对应的工具
            tool = None
            for t in self.tools:
                if hasattr(t, "name") and t.name == tool_name:
                    tool = t
                    break

            if tool:
                try:
                    # 执行工具
                    if asyncio.iscoroutinefunction(tool.execute):
                        result = await tool.execute(arguments, context)
                    else:
                        result = await asyncio.to_thread(tool.execute, arguments, context)

                    return self.create_tool_message(tool_call_id, tool_name, result)
                except Exception as e:
                    error_msg = f"Error executing tool '{tool_name}': {str(e)}"
                    logging.error(error_msg)
                    return self.create_tool_message(tool_call_id, tool_name, {"error": error_msg})
            else:
                error_msg = f"Tool '{tool_name}' not found"
                logging.error(error_msg)
                return self.create_tool_message(tool_call_id, tool_name, {"error": error_msg})

        # 并发执行所有工具调用
        tasks = [call_tool(tool_call, context) for tool_call in tool_calls]
        results = await asyncio.gather(*tasks) if tasks else []

        return results

    def execute_tool_calls_sync(
        self, tool_calls: List[Dict[str, Any]], context: Optional[WorkflowContext] = None
    ) -> List[Dict[str, Any]]:
        """同步执行工具调用"""
        try:
            loop = asyncio.get_running_loop()
            # 已在事件循环中
            coro = self.execute_tool_calls(tool_calls, context)
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()
            return loop.run_until_complete(coro)
        except RuntimeError:
            # 不在事件循环中
            return asyncio.run(self.execute_tool_calls(tool_calls, context))


class OpenAIToolCaller(ToolCaller):
    """OpenAI兼容的工具调用器"""

    def can_handle_streaming(self) -> bool:
        return True

    def extract_tool_calls_from_stream(self, chunk: Any) -> List[Dict[str, Any]]:
        """从流式响应中提取工具调用"""
        if hasattr(chunk, "choices") and chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                return delta.tool_calls
        return []

    def extract_tool_calls_from_choice(self, choice: Any) -> List[Dict[str, Any]]:
        """从非流式响应中提取工具调用"""
        if hasattr(choice, "message") and hasattr(choice.message, "tool_calls"):
            return choice.message.tool_calls or []
        return []

    def is_tool_call_chunk(self, chunk: Any) -> bool:
        """检查是否为工具调用分片"""
        return bool(self.extract_tool_calls_from_stream(chunk))

    def merge_tool_call_fragments(self, fragments: List[Any]) -> List[Dict[str, Any]]:
        """合并工具调用分片"""
        if not fragments:
            return []

        # 按ID分组
        tool_calls_by_id = {}
        for frag in fragments:
            frag_dict = frag if isinstance(frag, dict) else getattr(frag, "__dict__", {})
            tool_call_id = frag_dict.get("id", "")

            if tool_call_id not in tool_calls_by_id:
                tool_calls_by_id[tool_call_id] = {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                }

            # 更新函数信息
            if frag_dict.get("function"):
                func = frag_dict["function"]
                func_dict = func if isinstance(func, dict) else getattr(func, "__dict__", func)

                if func_dict.get("name"):
                    tool_calls_by_id[tool_call_id]["function"]["name"] = func_dict["name"]
                if func_dict.get("arguments"):
                    tool_calls_by_id[tool_call_id]["function"]["arguments"] += func_dict["arguments"]

        return list(tool_calls_by_id.values())

    def create_assistant_message(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建助手消息"""
        return {"role": "assistant", "content": "", "tool_calls": tool_calls}

    def create_tool_message(self, tool_call_id: str, tool_name: str, content: Any) -> Dict[str, Any]:
        """创建工具响应消息"""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": json.dumps(content) if not isinstance(content, str) else content,
        }


class TongyiToolCaller(OpenAIToolCaller):
    """通义千问工具调用器"""

    def can_handle_streaming(self) -> bool:
        return True

    def extract_tool_calls_from_stream(self, chunk: Any) -> List[Dict[str, Any]]:
        """通义千问的流式工具调用提取"""
        # 通义千问的流式工具调用格式与OpenAI兼容
        return super().extract_tool_calls_from_stream(chunk)


class DeepSeekToolCaller(OpenAIToolCaller):
    """DeepSeek工具调用器"""

    def can_handle_streaming(self) -> bool:
        return True

    def extract_tool_calls_from_stream(self, chunk: Any) -> List[Dict[str, Any]]:
        """DeepSeek的流式工具调用提取"""
        # DeepSeek的流式工具调用格式与OpenAI兼容
        return super().extract_tool_calls_from_stream(chunk)


class OllamaToolCaller(OpenAIToolCaller):
    """Ollama工具调用器"""

    def can_handle_streaming(self) -> bool:
        return False  # Ollama可能不支持流式工具调用

    def extract_tool_calls_from_stream(self, chunk: Any) -> List[Dict[str, Any]]:
        """Ollama的流式工具调用提取"""
        # Ollama可能不支持流式工具调用，返回空列表
        return []


def create_tool_caller(provider: str, tools: List[Any] = None) -> ToolCaller:
    """工厂函数，根据提供商创建对应的工具调用器"""
    tool_caller_map = {
        "openai": OpenAIToolCaller,
        "tongyi": TongyiToolCaller,
        "deepseek": DeepSeekToolCaller,
        "ollama": OllamaToolCaller,
        "openrouter": OpenAIToolCaller,
        "doubao": OpenAIToolCaller,
        "other": OpenAIToolCaller,
    }

    caller_class = tool_caller_map.get(provider.lower(), OpenAIToolCaller)
    return caller_class(tools)
