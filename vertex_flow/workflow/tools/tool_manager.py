"""统一工具管理器

这个模块提供了一个统一的工具管理和调用接口，包含：
1. FunctionTool的注册和管理
2. 统一的工具调用执行
3. 不同类型工具的协调处理
"""

import datetime
import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

try:
    import pytz

    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.tools.tool_caller import RuntimeToolCall, ToolCaller

logger = LoggerUtil.get_logger(__name__)


class FunctionTool:
    """函数工具类"""

    def __init__(self, name: str, description: str, func: Callable, schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.func = func
        self.schema = schema

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.schema},
        }

    def execute(self, inputs: Dict[str, Any], context=None) -> Any:
        """执行函数"""
        return self.func(inputs, context)


class ToolCallResult:
    """工具调用结果封装"""

    def __init__(self, tool_call_id: str, content: str, success: bool = True, error: Optional[str] = None):
        self.tool_call_id = tool_call_id
        self.content = content
        self.success = success
        self.error = error

    def to_message(self) -> Dict[str, Any]:
        """转换为消息格式"""
        # 确保content永远不为None
        if self.success:
            content = self.content if self.content is not None else ""
        else:
            error_content = self.error or self.content or "Unknown error"
            content = f"Error: {error_content}"

        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": content,
        }


class ToolExecutor(ABC):
    """工具执行器抽象基类"""

    @abstractmethod
    def execute_tool_call(self, tool_call: RuntimeToolCall, context: WorkflowContext) -> ToolCallResult:
        """执行单个工具调用"""
        pass

    @abstractmethod
    def can_handle(self, tool_name: str) -> bool:
        """判断是否能处理指定的工具"""
        pass


class MCPToolExecutor(ToolExecutor):
    """MCP工具执行器"""

    def __init__(self):
        self._executor = None
        try:
            from concurrent.futures import ThreadPoolExecutor

            self._executor = ThreadPoolExecutor(max_workers=4)
        except ImportError:
            logger.warning("ThreadPoolExecutor not available")

    def can_handle(self, tool_name: str) -> bool:
        """判断是否为MCP工具"""
        return tool_name is not None and tool_name.startswith("mcp_")

    def execute_tool_call(self, tool_call: RuntimeToolCall, context: WorkflowContext) -> ToolCallResult:
        """执行MCP工具调用"""
        try:
            if self._executor:
                future = self._executor.submit(self._call_mcp_tool_async, tool_call)
                result_info = future.result(timeout=30.0)
            else:
                result_info = self._call_mcp_tool_sync(tool_call)

            # result_info 现在是一个 (content, is_success) 元组
            if isinstance(result_info, tuple):
                content, is_success = result_info
                return ToolCallResult(tool_call.id, content, success=is_success, error=None if is_success else content)
            else:
                # 向后兼容，如果返回的是字符串
                return ToolCallResult(tool_call.id, result_info, success=True)
        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_call.function.name}: {e}")
            return ToolCallResult(tool_call.id, str(e), success=False, error=str(e))

    def _call_mcp_tool_sync(self, tool_call: RuntimeToolCall) -> str:
        """同步调用MCP工具"""
        try:
            from vertex_flow.workflow.mcp_manager import get_mcp_manager

            # 解析工具调用
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

            # 移除mcp_前缀获取原始工具名
            if tool_name.startswith("mcp_"):
                original_tool_name = tool_name[4:]
            else:
                original_tool_name = tool_name

            logger.info(f"🔧 [MCPToolExecutor] Executing MCP tool: {original_tool_name} with arguments: {arguments}")
            logger.info(f"🔧 [MCPToolExecutor] Tool Call ID: {tool_call.id}")
            logger.info(f"🔧 [MCPToolExecutor] Original Tool Name: {original_tool_name}")
            logger.info(
                f"🔧 [MCPToolExecutor] Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}"
            )

            # 调用MCP工具
            mcp_manager = get_mcp_manager()
            result = mcp_manager.call_tool(original_tool_name, arguments, tool_call_id=tool_call.id)

            logger.info(f"🔧 [MCPToolExecutor] Result for Tool Call ID {tool_call.id} - Tool Name: {original_tool_name}")
            logger.info(f"MCP Tool Manager Result Debug - Result Type: {type(result)}")
            if result:
                logger.info(f"MCP Tool Manager Result Debug - Content Type: {type(result.content)}")
                logger.info(f"MCP Tool Manager Result Debug - Content: {result.content}")
                if hasattr(result, "__dict__"):
                    logger.info(f"MCP Tool Manager Result Debug - Attributes: {result.__dict__}")
            else:
                logger.info(f"MCP Tool Manager Result Debug - Result: None")

            if result:
                # 检查是否是错误结果
                if hasattr(result, "isError") and result.isError:
                    # 错误结果，提取错误信息
                    error_msg = "MCP tool execution failed"
                    if result.content:
                        if isinstance(result.content, list):
                            error_parts = []
                            for item in result.content:
                                if hasattr(item, "text"):
                                    error_parts.append(item.text)
                                elif isinstance(item, dict) and "text" in item:
                                    error_parts.append(item["text"])
                                else:
                                    error_parts.append(str(item))
                            error_msg = "\n".join(error_parts)
                        else:
                            error_msg = str(result.content)
                    logger.warning(f"MCP tool {original_tool_name} failed: {error_msg}")
                    return error_msg, False  # 返回 (content, is_success) 元组

                # 成功结果，提取内容
                if result.content:
                    if isinstance(result.content, list):
                        content_parts = []
                        for item in result.content:
                            if hasattr(item, "text"):
                                content_parts.append(item.text)
                            elif isinstance(item, dict) and "text" in item:
                                content_parts.append(item["text"])
                            else:
                                content_parts.append(str(item))
                        return "\n".join(content_parts), True  # 返回 (content, is_success) 元组
                    else:
                        return str(result.content), True  # 返回 (content, is_success) 元组
                else:
                    return "Tool executed successfully but returned no content", True  # 返回 (content, is_success) 元组
            else:
                return "MCP tool execution returned no result", False  # 返回 (content, is_success) 元组

        except Exception as e:
            logger.error(f"Error in MCP tool execution: {e}")
            raise

    def _call_mcp_tool_async(self, tool_call: RuntimeToolCall) -> tuple:
        """异步调用MCP工具"""
        import asyncio

        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self._execute_mcp_tool_async(tool_call))
        finally:
            loop.close()

    async def _execute_mcp_tool_async(self, tool_call: RuntimeToolCall) -> tuple:
        """异步执行MCP工具"""
        # 这里可以实现真正的异步MCP调用
        # 目前先使用同步版本
        return self._call_mcp_tool_sync(tool_call)


class FunctionToolExecutor(ToolExecutor):
    """函数工具执行器"""

    def __init__(self, function_tools: Dict[str, FunctionTool]):
        self.function_tools = function_tools

    def can_handle(self, tool_name: str) -> bool:
        """判断是否为函数工具"""
        return tool_name is not None and tool_name in self.function_tools

    def execute_tool_call(self, tool_call: RuntimeToolCall, context: WorkflowContext) -> ToolCallResult:
        """执行函数工具调用"""
        try:
            tool_name = tool_call.function.name
            function_tool = self.function_tools.get(tool_name)

            if not function_tool:
                return ToolCallResult(tool_call.id, f"Function tool '{tool_name}' not found", success=False)

            # 解析参数
            if isinstance(tool_call.function.arguments, str):
                import json

                arguments = json.loads(tool_call.function.arguments)
            else:
                arguments = tool_call.function.arguments

            # 执行函数
            result = function_tool.execute(arguments, context)

            # 处理结果
            if isinstance(result, dict) or isinstance(result, list):
                import json

                content = json.dumps(result, ensure_ascii=False)
            else:
                content = str(result)

            return ToolCallResult(tool_call.id, content, success=True)

        except Exception as e:
            logger.error(f"Error executing function tool {tool_call.function.name}: {e}")
            return ToolCallResult(tool_call.id, str(e), success=False, error=str(e))


class RegularToolExecutor(ToolExecutor):
    """常规工具执行器"""

    def __init__(self, tool_caller: Optional[ToolCaller] = None, tools: Optional[List[Dict[str, Any]]] = None):
        self.tool_caller = tool_caller
        self.tools = tools or []

    def can_handle(self, tool_name: str) -> bool:
        """判断是否为常规工具"""
        return tool_name is not None and not tool_name.startswith("mcp_")

    def execute_tool_call(self, tool_call: RuntimeToolCall, context: WorkflowContext) -> ToolCallResult:
        """执行常规工具调用"""
        try:
            if self.tool_caller:
                # 使用tool_caller执行
                tool_results = self.tool_caller.execute_tool_calls_sync([tool_call], self.tools)
                if tool_results:
                    # 假设返回的是消息格式
                    result_message = tool_results[0]
                    return ToolCallResult(tool_call.id, result_message.get("content", ""), success=True)
                else:
                    return ToolCallResult(tool_call.id, "No result returned", success=False)
            else:
                # 回退到基础实现
                return ToolCallResult(tool_call.id, f"Tool {tool_call.function.name} executed (fallback)", success=True)
        except Exception as e:
            logger.error(f"Error executing regular tool {tool_call.function.name}: {e}")
            return ToolCallResult(tool_call.id, str(e), success=False, error=str(e))


class ToolManager:
    """统一工具管理器

    这个类统一管理所有类型的工具，包括：
    1. FunctionTool的注册和管理
    2. 统一的工具调用执行
    3. 不同类型工具的协调处理
    """

    def __init__(self, tool_caller: Optional[ToolCaller] = None, tools: Optional[List[Dict[str, Any]]] = None):
        self.tool_caller = tool_caller
        self.tools = tools or []
        self.function_tools: Dict[str, FunctionTool] = {}

        # 初始化工具执行器
        self.function_tool_executor = FunctionToolExecutor(self.function_tools)
        self.executors: List[ToolExecutor] = [
            MCPToolExecutor(),
            self.function_tool_executor,
            RegularToolExecutor(tool_caller, tools),
        ]

        # 注册默认工具
        self._register_default_tools()

    def create_assistant_message(self, choice_or_tool_calls: Union[Any, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """创建assistant消息

        Args:
            choice_or_tool_calls: choice对象或工具调用列表

        Returns:
            assistant消息字典
        """
        if self.tool_caller and hasattr(choice_or_tool_calls, "message"):
            # 使用tool_caller创建消息
            return self.tool_caller.create_assistant_message(choice_or_tool_calls)
        else:
            # 手动创建消息
            if isinstance(choice_or_tool_calls, list):
                # 直接传入的工具调用列表
                tool_calls = choice_or_tool_calls
                content = None
            else:
                # choice对象
                choice = choice_or_tool_calls
                content = getattr(choice.message, "content", None) if hasattr(choice, "message") else None
                tool_calls = getattr(choice.message, "tool_calls", []) if hasattr(choice, "message") else []

            # 标准化工具调用格式
            normalized_tool_calls = RuntimeToolCall.normalize_list(tool_calls)

            return {
                "role": "assistant",
                "content": content if content is not None else "",  # 确保content不为null
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                    }
                    for tool_call in normalized_tool_calls
                ],
            }

    def execute_tool_calls(
        self, tool_calls: List[Union[Dict[str, Any], RuntimeToolCall]], context: WorkflowContext
    ) -> List[Dict[str, Any]]:
        """执行工具调用并返回工具消息列表

        Args:
            tool_calls: 工具调用列表
            context: 工作流上下文

        Returns:
            工具消息列表
        """
        # 标准化工具调用
        normalized_tool_calls = RuntimeToolCall.normalize_list(tool_calls)

        tool_messages = []

        for tool_call in normalized_tool_calls:
            # 确保有tool_call_id，处理None和空字符串
            if not tool_call.id or tool_call.id is None:
                import uuid
                old_id = tool_call.id
                tool_call.id = f"call_{uuid.uuid4().hex[:8]}"
                logger.info(f"🔧 [execute_tool_calls] Generated new tool call ID: {old_id} → {tool_call.id} for tool: {tool_call.function.name if tool_call.function else 'unknown'}")
            else:
                logger.debug(f"🔧 [execute_tool_calls] Using existing tool call ID: {tool_call.id} for tool: {tool_call.function.name if tool_call.function else 'unknown'}")

            # 检查工具名称是否有效
            tool_name = tool_call.function.name if tool_call.function else None
            if not tool_name:
                # 尝试从arguments中恢复工具名称
                arguments_str = tool_call.function.arguments if tool_call.function else ""
                if arguments_str:
                    import re

                    # 尝试匹配常见的工具名称模式
                    patterns = [
                        r'"name":\s*"([^"]+)"',  # JSON中的name字段
                        r"(mcp_[a-zA-Z_]+)",  # mcp_开头的工具名
                        r"([a-zA-Z_]+_v\d+)",  # 版本化的工具名
                        r"([a-zA-Z_]+_[a-zA-Z_]+)",  # 下划线分隔的工具名
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, arguments_str)
                        if match:
                            recovered_name = match.group(1)
                            # 更新工具调用的名称
                            if tool_call.function:
                                tool_call.function.name = recovered_name
                            tool_name = recovered_name
                            logger.info(
                                f"Recovered tool name '{recovered_name}' from arguments for tool call {tool_call.id}"
                            )
                            break

                # 如果仍然没有工具名称，才跳过
                if not tool_name:
                    logger.warning(f"Tool call {tool_call.id} has no function name, skipping {tool_call.function}")
                    error_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "Error: Tool call has no function name",
                    }
                    tool_messages.append(error_msg)
                    continue

            # 找到合适的执行器
            executor = self._find_executor(tool_name)

            if executor:
                # 执行工具调用
                result = executor.execute_tool_call(tool_call, context)
                tool_messages.append(result.to_message())
            else:
                # 没有找到合适的执行器
                logger.warning(f"No executor found for tool: {tool_call.function.name}")
                error_result = ToolCallResult(
                    tool_call.id,
                    f"No executor available for tool: {tool_call.function.name}",
                    success=False,
                    error="No executor found",
                )
                tool_messages.append(error_result.to_message())

        return tool_messages

    def handle_tool_calls_complete(
        self,
        choice_or_tool_calls: Union[Any, List[Dict[str, Any]]],
        context: WorkflowContext,
        messages: List[Dict[str, Any]],
        completion_func: Optional[Callable] = None,
        max_rounds: int = 10,
    ) -> Union[bool, Any]:
        """完整处理工具调用，包括多轮调用和循环检测"""
        import traceback
        # 获取调用栈信息
        call_stack = traceback.extract_stack()
        caller_info = call_stack[-2] if len(call_stack) >= 2 else call_stack[-1]
        logger.info(f"🔧 [handle_tool_calls_complete] Called from: {caller_info.filename}:{caller_info.lineno} in {caller_info.name}")
        
        try:
            # 提取工具调用
            if hasattr(choice_or_tool_calls, "message") and hasattr(choice_or_tool_calls.message, "tool_calls"):
                tool_calls = choice_or_tool_calls.message.tool_calls
                logger.info(f"🔧 [handle_tool_calls_complete] Extracted {len(tool_calls)} tool calls from choice.message")
            elif isinstance(choice_or_tool_calls, list):
                tool_calls = choice_or_tool_calls
                logger.info(f"🔧 [handle_tool_calls_complete] Received {len(tool_calls)} tool calls as list")
            else:
                logger.warning(f"🔧 [handle_tool_calls_complete] No tool calls found in input: {type(choice_or_tool_calls)}")
                return False

            if not tool_calls:
                logger.info(f"🔧 [handle_tool_calls_complete] No tool calls to process")
                return False
            
            # 记录所有输入的工具调用详情
            for i, tc in enumerate(tool_calls):
                if isinstance(tc, dict):
                    tc_id = tc.get('id')
                    tc_name = tc.get('function', {}).get('name')
                    tc_args = tc.get('function', {}).get('arguments')
                else:
                    tc_id = getattr(tc, 'id', None)
                    tc_name = getattr(tc.function, 'name', None) if hasattr(tc, 'function') else None
                    tc_args = getattr(tc.function, 'arguments', None) if hasattr(tc, 'function') else None
                logger.info(f"🔧 [handle_tool_calls_complete]   Input[{i}] ID: {tc_id}, Name: {tc_name}, Args: {tc_args}")

            # 检查是否已经存在相同的assistant消息（避免重复）
            normalized_tool_calls = RuntimeToolCall.normalize_list(tool_calls)
            existing_assistant_msg = None

            # 查找最后一个assistant消息
            for msg in reversed(messages):
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    existing_assistant_msg = msg
                    break

            # 检查是否是相同的工具调用
            should_add_assistant = True
            if existing_assistant_msg:
                existing_tool_calls = existing_assistant_msg.get("tool_calls", [])
                if len(existing_tool_calls) == len(normalized_tool_calls):
                    # 比较工具调用是否相同
                    same_calls = True
                    for i, (existing, new) in enumerate(zip(existing_tool_calls, normalized_tool_calls)):
                        if (
                            existing.get("function", {}).get("name") != new.function.name
                            or existing.get("function", {}).get("arguments") != new.function.arguments
                        ):
                            same_calls = False
                            break

                    if same_calls:
                        should_add_assistant = False
                        logger.debug("Skipping duplicate assistant message with same tool calls")

            # 添加assistant消息（如果需要），在执行工具之前
            if should_add_assistant:
                # 预处理工具调用，确保有ID
                for tool_call in normalized_tool_calls:
                    if not tool_call.id or tool_call.id is None:
                        import uuid
                        old_id = tool_call.id
                        tool_call.id = f"call_{uuid.uuid4().hex[:8]}"
                        logger.info(f"🔧 [handle_tool_calls_complete] Generated new tool call ID: {old_id} → {tool_call.id} for tool: {tool_call.function.name if tool_call.function else 'unknown'}")
                    else:
                        logger.debug(f"🔧 [handle_tool_calls_complete] Using existing tool call ID: {tool_call.id} for tool: {tool_call.function.name if tool_call.function else 'unknown'}")
                
                assistant_message = self.create_assistant_message(normalized_tool_calls)
                messages.append(assistant_message)

            # 检查是否已经存在相同的tool消息（避免重复执行）
            existing_tool_call_ids = set()
            for msg in messages:
                if msg.get("role") == "tool" and msg.get("tool_call_id"):
                    existing_tool_call_ids.add(msg.get("tool_call_id"))

            # 过滤掉已经执行过的工具调用
            tools_to_execute = []
            for tool_call in normalized_tool_calls:
                if tool_call.id not in existing_tool_call_ids:
                    tools_to_execute.append(tool_call)
                else:
                    logger.debug(f"Skipping already executed tool call: {tool_call.id}")

            # 执行工具调用
            if tools_to_execute:
                tool_messages = self.execute_tool_calls(tools_to_execute, context)
                messages.extend(tool_messages)

            return True

        except Exception as e:
            logger.error(f"Error in handle_tool_calls_complete: {e}")
            return False

    def _find_executor(self, tool_name: str) -> Optional[ToolExecutor]:
        """找到合适的工具执行器"""
        for executor in self.executors:
            if executor.can_handle(tool_name):
                return executor
        return None

    def add_executor(self, executor: ToolExecutor):
        """添加自定义工具执行器"""
        self.executors.insert(0, executor)  # 插入到前面，优先级更高

    def update_tools(self, tools: List[Dict[str, Any]]):
        """更新工具列表"""
        self.tools = tools
        # 更新常规工具执行器的工具列表
        for executor in self.executors:
            if isinstance(executor, RegularToolExecutor):
                executor.tools = tools

    # FunctionTool管理方法
    def register_tool(self, tool: FunctionTool):
        """注册函数工具"""
        self.function_tools[tool.name] = tool
        logger.info(f"Registered function tool: {tool.name}")

    def unregister_tool(self, tool_name: str):
        """注销函数工具"""
        if tool_name in self.function_tools:
            del self.function_tools[tool_name]
            logger.info(f"Unregistered function tool: {tool_name}")

    def get_tool(self, tool_name: str) -> Optional[FunctionTool]:
        """获取函数工具"""
        return self.function_tools.get(tool_name)

    def list_function_tools(self) -> List[FunctionTool]:
        """列出所有函数工具"""
        return list(self.function_tools.values())

    def get_function_tools_as_dict(self) -> List[Dict[str, Any]]:
        """获取函数工具的字典格式列表"""
        return [tool.to_dict() for tool in self.function_tools.values()]

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称列表"""
        names = []
        # 添加函数工具名称
        names.extend(self.function_tools.keys())
        # 添加MCP工具名称（如果有的话）
        for executor in self.executors:
            if hasattr(executor, "get_tool_names"):
                names.extend(executor.get_tool_names())
        return names

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any], context=None) -> Any:
        """执行单个工具"""
        # 查找函数工具
        if tool_name in self.function_tools:
            tool = self.function_tools[tool_name]
            return tool.execute(arguments, context)

        # 查找其他类型的工具
        for executor in self.executors:
            if executor.can_handle(tool_name):
                # 创建模拟的RuntimeToolCall对象
                mock_tool_call = type(
                    "MockRuntimeToolCall",
                    (),
                    {
                        "id": "mock_call_id",
                        "function": type(
                            "MockFunction",
                            (),
                            {
                                "name": tool_name,
                                "arguments": json.dumps(arguments) if isinstance(arguments, dict) else str(arguments),
                            },
                        )(),
                    },
                )()

                # 创建WorkflowContext
                from vertex_flow.workflow.context import WorkflowContext

                if context is None:
                    context = WorkflowContext()

                result = executor.execute_tool_call(mock_tool_call, context)
                return result.content

        raise ValueError(f"Tool '{tool_name}' not found")

    def _register_default_tools(self):
        """注册默认工具"""
        # 注册时间工具
        self.register_time_tools()
        # 注册自定义示例工具
        self.register_custom_tools()

    def create_custom_tools(self) -> List[FunctionTool]:
        """创建自定义示例工具"""
        tools = []

        # 计算器工具
        def calculator(inputs: dict, context=None):
            """简单计算器"""
            expression = inputs.get("expression", "")
            try:
                # 安全的数学表达式计算
                import ast
                import operator

                # 支持的操作
                ops = {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                    ast.Pow: operator.pow,
                    ast.USub: operator.neg,
                }

                def eval_expr(node):
                    if isinstance(node, ast.Constant):
                        return node.value
                    elif isinstance(node, ast.BinOp):
                        return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
                    elif isinstance(node, ast.UnaryOp):
                        return ops[type(node.op)](eval_expr(node.operand))
                    else:
                        raise TypeError(node)

                result = eval_expr(ast.parse(expression, mode="eval").body)
                return {"result": result, "expression": expression}
            except Exception as e:
                return {"error": f"计算错误: {str(e)}"}

        calc_tool = FunctionTool(
            name="calculator",
            description="执行基本数学计算",
            func=calculator,
            schema={
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "要计算的数学表达式"}},
                "required": ["expression"],
            },
        )
        tools.append(calc_tool)

        return tools

    def create_time_tools(self) -> List[FunctionTool]:
        """创建时间相关工具"""
        tools = []

        # 获取当前时间工具
        def get_current_time(inputs: dict, context=None):
            """获取当前时间"""
            timezone = inputs.get("timezone", "UTC")
            format_type = inputs.get("format", "iso")

            try:
                if HAS_PYTZ:
                    if timezone == "UTC":
                        tz = pytz.UTC
                    else:
                        tz = pytz.timezone(timezone)
                    now = datetime.datetime.now(tz)
                else:
                    # 使用标准库的UTC时区支持
                    if timezone == "UTC":
                        now = datetime.datetime.now(datetime.timezone.utc)
                    else:
                        # 如果没有pytz，默认使用本地时间
                        now = datetime.datetime.now()

                if format_type == "iso":
                    result = now.isoformat()
                elif format_type == "timestamp":
                    result = str(int(now.timestamp()))
                elif format_type == "readable":
                    result = now.strftime("%Y-%m-%d %H:%M:%S %Z")
                else:
                    result = now.strftime(format_type)

                return {"current_time": result, "timezone": timezone, "format": format_type}
            except Exception as e:
                return {"error": f"获取时间错误: {str(e)}"}

        time_tool = FunctionTool(
            name="get_current_time",
            description="获取当前时间",
            func=get_current_time,
            schema={
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "时区", "default": "UTC"},
                    "format": {"type": "string", "description": "时间格式", "default": "iso"},
                },
                "required": [],
            },
        )
        tools.append(time_tool)

        return tools

    def register_custom_tools(self):
        """注册自定义示例工具"""
        custom_tools = self.create_custom_tools()
        for tool in custom_tools:
            self.register_tool(tool)
        logger.info(f"Registered {len(custom_tools)} custom tools")

    def register_time_tools(self):
        """注册时间相关工具"""
        time_tools = self.create_time_tools()
        for tool in time_tools:
            self.register_tool(tool)
        logger.info(f"Registered {len(time_tools)} time tools")


# 保持向后兼容性
UnifiedToolManager = ToolManager


# 全局工具管理器实例
_tool_manager: Optional[ToolManager] = None


def get_tool_manager() -> ToolManager:
    """获取全局工具管理器实例"""
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ToolManager()
    return _tool_manager


# 保持向后兼容性
def get_function_tool_manager() -> ToolManager:
    """获取全局函数工具管理器实例（向后兼容）"""
    return get_tool_manager()
