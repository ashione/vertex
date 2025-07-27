import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.context import WorkflowContext

logger = LoggerUtil.get_logger(__name__)


class RuntimeToolCall:
    """统一处理tool_call的格式转换，将dict格式转换为对象格式"""

    def __init__(self, data):
        """
        初始化RuntimeToolCall

        Args:
            data: dict格式的tool_call数据，包含id、type、function等信息
        """
        # 确保id不为None，如果是None或空字符串则生成一个新的ID
        original_id = data.get("id")
        if original_id is None or original_id == "":
            import uuid

            self.id = f"call_{uuid.uuid4().hex[:8]}"
            logger.info(f"🔧 [RuntimeToolCall.__init__] Generated new tool call ID: {original_id} → {self.id}")
        else:
            self.id = original_id
            logger.info(f"🔧 [RuntimeToolCall.__init__] Using provided tool call ID: {self.id}")
        self.type = data.get("type", "function")

        # 安全获取function信息，确保name和arguments永远不为None
        function_data = data.get("function", {})
        function_name = function_data.get("name") or ""
        function_args = function_data.get("arguments") or "{}"

        self.function = type("RuntimeFunction", (), {"name": function_name, "arguments": function_args})()

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

    def __init__(self, tools: Optional[List[Any]] = None):
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

    def format_tool_call_request(self, tool_calls):
        """格式化工具调用请求消息"""
        logger.info(f"Formatting tool call request for {len(tool_calls)} tool calls")
        for tool_call in tool_calls:
            # 构建工具调用请求消息
            tool_name = (
                tool_call.get("function", {}).get("name", "")
                if isinstance(tool_call, dict)
                else tool_call.function.name
            )
            tool_args = (
                tool_call.get("function", {}).get("arguments", "{}")
                if isinstance(tool_call, dict)
                else tool_call.function.arguments
            )

            logger.info(f"Tool Call Request - Tool Name: {tool_name}")
            logger.info(f"Tool Call Request - Arguments: {tool_args}")

            # 格式化JSON参数以便更好显示
            try:
                import json

                parsed_args = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                formatted_args = json.dumps(parsed_args, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                formatted_args = str(tool_args)

            request_message = f"🔧 调用工具: {tool_name}\n📋 参数:\n```json\n{formatted_args}\n```"
            logger.info(f"Yielding tool call request message for {tool_name}")
            yield f"\n{request_message}\n"

    def format_tool_call_results(self, tool_calls, messages):
        """格式化工具调用结果消息"""
        logger.info(f"Formatting tool call results for {len(tool_calls)} tool calls")
        # 查找最新的工具响应消息
        for tool_call in tool_calls:
            tool_call_id = tool_call.get("id", "") if isinstance(tool_call, dict) else tool_call.id
            tool_name = (
                tool_call.get("function", {}).get("name", "")
                if isinstance(tool_call, dict)
                else tool_call.function.name
            )

            logger.info(f"Tool Call Result - Looking for tool_call_id: {tool_call_id}, tool_name: {tool_name}")

            # 在messages中查找对应的tool响应
            found_result = False
            for msg in reversed(messages):
                if msg.get("role") == "tool" and msg.get("tool_call_id") == tool_call_id:
                    result_content = msg.get("content", "")
                    logger.info(f"Tool Call Result - Found result for {tool_name}: {result_content[:200]}...")
                    found_result = True

                    # 尝试格式化JSON结果
                    try:
                        import json

                        parsed_result = (
                            json.loads(result_content) if isinstance(result_content, str) else result_content
                        )
                        if isinstance(parsed_result, dict) or isinstance(parsed_result, list):
                            formatted_result = json.dumps(parsed_result, indent=2, ensure_ascii=False)
                            result_message = f"✅ 工具 {tool_name} 执行结果:\n```json\n{formatted_result}\n```"
                        else:
                            result_message = f"✅ 工具 {tool_name} 执行结果:\n```\n{result_content}\n```"
                    except (json.JSONDecodeError, TypeError):
                        result_message = f"✅ 工具 {tool_name} 执行结果:\n```\n{result_content}\n```"

                    logger.info(f"Yielding tool call result message for {tool_name}")
                    yield f"\n{result_message}\n"
                    break

            if not found_result:
                logger.warning(
                    f"Tool Call Result - No result found for tool_call_id: {tool_call_id}, tool_name: {tool_name}"
                )
                logger.info(f"Available tool messages: {[msg for msg in messages if msg.get('role') == 'tool']}")

    async def execute_tool_calls(
        self, tool_calls: List[Dict[str, Any]], context: Optional[WorkflowContext] = None
    ) -> List[Dict[str, Any]]:
        """执行工具调用并返回工具响应消息列表"""
        logger.info(f"Executing {len(tool_calls)} tool calls")
        tool_messages = []

        async def call_tool(tool_call: Dict[str, Any], context: Optional[WorkflowContext] = None):
            tool_call_id = tool_call.get("id", "")
            tool_name = tool_call.get("function", {}).get("name", "")
            arguments_str = tool_call.get("function", {}).get("arguments", "{}")

            logger.info(f"Executing tool call - ID: {tool_call_id}, Name: {tool_name}")
            logger.info(f"Tool arguments string: {arguments_str}")

            try:
                arguments = json.loads(arguments_str)
                logger.info(f"Parsed arguments: {arguments}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse arguments as JSON: {e}, using empty dict")
                arguments = {}

            # 查找对应的工具
            tool = None
            available_tools = [getattr(t, "name", "unknown") for t in self.tools if hasattr(t, "name")]
            logger.info(f"Available tools: {available_tools}")

            for t in self.tools:
                if hasattr(t, "name") and t.name == tool_name:
                    tool = t
                    logger.info(f"Found matching tool: {tool_name}")
                    break

            if tool:
                try:
                    logger.info(f"Executing tool {tool_name} with arguments: {arguments}")
                    # 执行工具
                    if asyncio.iscoroutinefunction(tool.execute):
                        result = await tool.execute(arguments, context)
                    else:
                        result = await asyncio.to_thread(tool.execute, arguments, context)

                    logger.info(f"Tool {tool_name} execution completed with result: {str(result)[:200]}...")
                    return self.create_tool_message(tool_call_id, tool_name, result)
                except Exception as e:
                    error_msg = f"Error executing tool '{tool_name}': {str(e)}"
                    logger.error(error_msg)
                    return self.create_tool_message(tool_call_id, tool_name, {"error": error_msg})
            else:
                error_msg = f"Tool '{tool_name}' not found"
                logger.error(error_msg)
                return self.create_tool_message(tool_call_id, tool_name, {"error": error_msg})

        # 并发执行所有工具调用
        tasks = [call_tool(tool_call, context) for tool_call in tool_calls]
        logger.info(f"Created {len(tasks)} tasks for tool execution")
        results = await asyncio.gather(*tasks) if tasks else []
        logger.info(f"Tool execution completed, got {len(results)} results")

        return results

    def execute_tool_calls_sync(
        self, tool_calls: List[Dict[str, Any]], context: Optional[WorkflowContext] = None
    ) -> List[Dict[str, Any]]:
        """同步执行工具调用"""
        logger.info(f"Synchronously executing {len(tool_calls)} tool calls")
        try:
            loop = asyncio.get_running_loop()
            logger.info("Running in existing event loop")
            # 已在事件循环中
            coro = self.execute_tool_calls(tool_calls, context)
            if loop.is_running():
                import nest_asyncio

                logger.info("Applying nest_asyncio for nested event loop")
                nest_asyncio.apply()
            result = loop.run_until_complete(coro)
            logger.info(f"Sync execution completed with {len(result)} results")
            return result
        except RuntimeError:
            logger.info("No event loop running, creating new one")
            # 不在事件循环中
            result = asyncio.run(self.execute_tool_calls(tool_calls, context))
            logger.info(f"Sync execution completed with {len(result)} results")
            return result


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
        """合并工具调用分片 - 改进版本，支持序列合并和工具名称修复"""
        if not fragments:
            return []

        # 首先尝试按ID分组的传统方式
        tool_calls_by_id = {}
        sequential_fragments = []  # 用于存储可能需要序列合并的分片
        last_valid_tool_call_id = None  # 记录最后一个有效的工具调用ID

        for i, frag in enumerate(fragments):
            # 统一处理不同的片段格式
            if isinstance(frag, dict):
                # 字典格式
                frag_dict = frag
                original_id = frag_dict.get("id")
                function_info = frag_dict.get("function", {})
                func_dict = function_info if isinstance(function_info, dict) else getattr(function_info, "__dict__", {})
                fragment_name = (func_dict.get("name") or "").strip()
                fragment_args = func_dict.get("arguments") or ""
            else:
                # 对象格式（如 ChoiceDeltaToolCallFunction）
                frag_dict = getattr(frag, "__dict__", {})
                # 对于流式响应片段，通常没有独立的id，需要推断
                original_id = getattr(frag, "id", None)

                # 获取function对象，可能是frag.function或直接在frag中
                function_obj = getattr(frag, "function", None)
                if function_obj:
                    # function属性存在，从中获取name和arguments
                    fragment_name = (getattr(function_obj, "name", None) or "").strip()
                    fragment_args = getattr(function_obj, "arguments", "") or ""
                else:
                    # 直接从对象获取name和arguments（兼容性处理）
                    fragment_name = (getattr(frag, "name", None) or "").strip()
                    fragment_args = getattr(frag, "arguments", "") or ""

            # 如果有有效的工具名称和ID，说明这是一个新工具调用的开始
            if fragment_name and original_id:
                tool_call_id = original_id
                last_valid_tool_call_id = tool_call_id

                if tool_call_id not in tool_calls_by_id:
                    logger.info(
                        f"🔧 [merge_tool_call_fragments] Creating new tool call: {tool_call_id} → {fragment_name}"
                    )
                    tool_calls_by_id[tool_call_id] = {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {"name": fragment_name, "arguments": fragment_args},
                    }
                else:
                    # 更新名称（以防有更完整的名称）
                    existing_name = tool_calls_by_id[tool_call_id]["function"]["name"]
                    if not existing_name or len(fragment_name) > len(existing_name):
                        tool_calls_by_id[tool_call_id]["function"]["name"] = fragment_name
                    logger.debug(f"🔧 [merge_tool_call_fragments] Appending to existing tool call: {tool_call_id}")
                    tool_calls_by_id[tool_call_id]["function"]["arguments"] += fragment_args

            # 如果有有效ID但没有工具名称，尝试匹配现有工具调用
            elif original_id and original_id in tool_calls_by_id:
                tool_calls_by_id[original_id]["function"]["arguments"] += fragment_args

            # 如果没有原始ID，可能是流式处理中的参数片段
            elif not original_id:
                # 无ID的片段应该合并到最后一个有效工具调用或序列化列表
                cleaned_fragment_args = fragment_args.strip()
                if cleaned_fragment_args:
                    # 如果有最后一个有效的工具调用ID，则将此片段合并到该工具调用
                    if last_valid_tool_call_id and last_valid_tool_call_id in tool_calls_by_id:
                        tool_calls_by_id[last_valid_tool_call_id]["function"]["arguments"] += cleaned_fragment_args
                        continue

                    # 如果没有最后的有效ID，将此片段添加到序列化片段列表
                    sequential_fragments.append(cleaned_fragment_args)
                else:
                    # 空片段，添加到序列化列表
                    sequential_fragments.append(fragment_args)
            else:
                # 有其他情况的片段，添加到序列化列表
                sequential_fragments.append(fragment_args)

        # 如果没有有效的工具调用，但有序列分片，尝试从序列分片中重构完整的工具调用
        if not tool_calls_by_id and sequential_fragments:
            # 将所有片段合并成一个完整的参数字符串
            combined_args = "".join(sequential_fragments)

            # 尝试从合并的参数中提取工具名称（基于常见模式）
            import re

            # 查找类似 mcp_xxx 的模式
            tool_name_match = re.search(r"(mcp_[a-zA-Z_]+)", combined_args)
            if tool_name_match:
                tool_name = tool_name_match.group(1)
                # 移除工具名称部分，剩余的作为参数
                remaining_args = combined_args.replace(tool_name, "").strip()
                if remaining_args.startswith('"') and remaining_args.endswith('"'):
                    remaining_args = remaining_args[1:-1]  # 移除两端的引号

                # 创建重构的工具调用
                reconstructed_id = f"call_reconstructed_{hash(combined_args) % 10000:04d}"
                logger.info(
                    f"🔧 [merge_tool_call_fragments] Creating reconstructed tool call with name: {reconstructed_id} → {tool_name}"
                )
                tool_calls_by_id[reconstructed_id] = {
                    "id": reconstructed_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": remaining_args or "{}"},
                }
            else:
                # 没有找到工具名称，但参数看起来像JSON，创建一个通用工具调用
                if combined_args.strip().startswith("{"):
                    reconstructed_id = f"call_reconstructed_{hash(combined_args) % 10000:04d}"
                    logger.info(
                        f"🔧 [merge_tool_call_fragments] Creating generic reconstructed tool call: {reconstructed_id}"
                    )
                    tool_calls_by_id[reconstructed_id] = {
                        "id": reconstructed_id,
                        "type": "function",
                        "function": {"name": "", "arguments": combined_args.strip()},
                    }

        # 处理序列分片 - 如果有有效的工具调用，将序列片段合并进去
        elif sequential_fragments and tool_calls_by_id and last_valid_tool_call_id:
            # 将所有序列分片的参数合并到最后一个工具调用中
            for seq_frag in sequential_fragments:
                tool_calls_by_id[last_valid_tool_call_id]["function"]["arguments"] += seq_frag

        # 过滤掉无效的工具调用并验证JSON
        valid_tool_calls = []
        for tool_call in tool_calls_by_id.values():
            function_name = (tool_call.get("function", {}).get("name") or "").strip()
            arguments_str = tool_call.get("function", {}).get("arguments") or ""

            # 注意：不再在合并阶段过滤工具名称，让所有工具调用通过
            # 工具名称的验证和过滤将在后续的执行阶段进行

            # 验证和清理arguments
            try:
                import json

                # 简化的JSON处理逻辑
                cleaned_args = (arguments_str or "").strip()
                if not cleaned_args:
                    cleaned_args = "{}"

                # 使用严格的JSON解析验证
                cleaned_args = self._validate_and_clean_json_arguments(arguments_str)

                tool_call["function"]["arguments"] = cleaned_args
                valid_tool_calls.append(tool_call)

            except Exception as e:
                logger.warning(f"Error processing tool call arguments: {e}")
                continue

        return valid_tool_calls

    def _validate_and_clean_json_arguments(self, arguments_str: str) -> str:
        """
        使用严格的JSON解析验证来清理和验证工具调用参数

        Args:
            arguments_str: 原始参数字符串

        Returns:
            str: 清理后的有效JSON字符串
        """
        if not arguments_str:
            return "{}"

        cleaned_args = arguments_str.strip()
        if not cleaned_args:
            return "{}"

        # 首先尝试直接解析
        try:
            parsed = json.loads(cleaned_args)
            # 重新序列化以确保格式正确
            return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
        except json.JSONDecodeError as e:
            logger.debug(f"Initial JSON parse failed: {e}, attempting repair")

        # 如果直接解析失败，尝试修复常见问题
        repaired_json = self._attempt_json_repair(cleaned_args)
        if repaired_json:
            try:
                parsed = json.loads(repaired_json)
                return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
            except json.JSONDecodeError:
                pass

        # 如果修复失败，尝试提取完整的JSON对象
        extracted_json = self._extract_complete_json_object(cleaned_args)
        if extracted_json:
            try:
                parsed = json.loads(extracted_json)
                return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
            except json.JSONDecodeError:
                pass

        # 最后的fallback：检查是否明显不完整
        if self._is_obviously_incomplete_json(cleaned_args):
            logger.warning(f"Arguments appear incomplete, using empty object: {cleaned_args[:50]}...")
            return "{}"

        # 如果看起来像JSON但无法解析，记录警告并返回空对象
        if cleaned_args.startswith(("{", "[")):
            logger.warning(f"Invalid JSON format, using empty object: {cleaned_args[:50]}...")
            return "{}"

        # 对于非JSON格式的字符串，包装成字符串值
        try:
            return json.dumps({"value": cleaned_args}, ensure_ascii=False)
        except Exception:
            return "{}"

    def _attempt_json_repair(self, json_str: str) -> Optional[str]:
        """
        尝试修复常见的JSON格式问题

        Args:
            json_str: 可能损坏的JSON字符串

        Returns:
            Optional[str]: 修复后的JSON字符串，如果无法修复则返回None
        """
        if not json_str:
            return None

        # 移除前后空白字符
        repaired = json_str.strip()

        # 修复常见的引号问题
        if repaired.count('"') % 2 != 0:
            # 奇数个引号，尝试在末尾添加引号
            if repaired.endswith('"'):
                repaired = repaired[:-1]
            else:
                repaired += '"'

        # 修复未闭合的大括号
        open_braces = repaired.count("{")
        close_braces = repaired.count("}")
        if open_braces > close_braces:
            repaired += "}" * (open_braces - close_braces)
        elif close_braces > open_braces:
            # 移除多余的闭合括号
            excess_closes = close_braces - open_braces
            for _ in range(excess_closes):
                repaired = repaired.rstrip("}")

        # 修复未闭合的方括号
        open_brackets = repaired.count("[")
        close_brackets = repaired.count("]")
        if open_brackets > close_brackets:
            repaired += "]" * (open_brackets - close_brackets)
        elif close_brackets > open_brackets:
            # 移除多余的闭合括号
            excess_closes = close_brackets - open_brackets
            for _ in range(excess_closes):
                repaired = repaired.rstrip("]")

        # 修复末尾的逗号
        import re

        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

        return repaired if repaired != json_str else None

    def _extract_complete_json_object(self, json_str: str) -> Optional[str]:
        """
        尝试从字符串中提取完整的JSON对象

        Args:
            json_str: 包含JSON的字符串

        Returns:
            Optional[str]: 提取的完整JSON对象，如果找不到则返回None
        """
        if not json_str:
            return None

        # 查找第一个 { 或 [
        start_pos = -1
        start_char = None
        for i, char in enumerate(json_str):
            if char in "{[":
                start_pos = i
                start_char = char
                break

        if start_pos == -1:
            return None

        # 匹配对应的结束字符
        end_char = "}" if start_char == "{" else "]"
        bracket_count = 0
        in_string = False
        escape_next = False

        for i in range(start_pos, len(json_str)):
            char = json_str[i]

            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == start_char:
                    bracket_count += 1
                elif char == end_char:
                    bracket_count -= 1
                    if bracket_count == 0:
                        # 找到完整的JSON对象
                        return json_str[start_pos : i + 1]

        return None

    def _is_obviously_incomplete_json(self, json_str: str) -> bool:
        """
        检查JSON字符串是否明显不完整

        Args:
            json_str: 要检查的JSON字符串

        Returns:
            bool: 如果明显不完整则返回True
        """
        if not json_str:
            return True

        stripped = json_str.strip()

        # 检查是否以JSON开始但没有正确结束
        if stripped.startswith("{") and not stripped.endswith("}"):
            return True
        if stripped.startswith("[") and not stripped.endswith("]"):
            return True
        if stripped.startswith('"') and not stripped.endswith('"'):
            return True

        # 检查括号是否匹配
        open_braces = stripped.count("{")
        close_braces = stripped.count("}")
        if open_braces != close_braces:
            return True

        open_brackets = stripped.count("[")
        close_brackets = stripped.count("]")
        if open_brackets != close_brackets:
            return True

        # 检查引号是否匹配
        quote_count = stripped.count('"')
        if quote_count % 2 != 0:
            return True

        return False

    def create_assistant_message(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建助手消息"""
        return {"role": "assistant", "content": "", "tool_calls": tool_calls}

    def create_tool_message(self, tool_call_id: str, tool_name: str, content: Any) -> Dict[str, Any]:
        """创建工具响应消息"""
        # 确保content不为None
        if content is None:
            final_content = ""
        elif isinstance(content, str):
            final_content = content
        else:
            final_content = json.dumps(content)

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": final_content,
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
    """DeepSeek工具调用器 - 支持去重功能以处理重复的tool_calls"""

    def can_handle_streaming(self) -> bool:
        return True

    def extract_tool_calls_from_stream(self, chunk: Any) -> List[Dict[str, Any]]:
        """DeepSeek的流式工具调用提取"""
        # DeepSeek的流式工具调用格式与OpenAI兼容
        return super().extract_tool_calls_from_stream(chunk)

    def _deduplicate_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于name+arguments去重工具调用

        DeepSeek等非OpenAI模型在流式调用中可能返回重复的tool_calls，
        这个方法通过比较function.name和function.arguments来去除重复项。

        Args:
            tool_calls: 原始工具调用列表

        Returns:
            List[Dict[str, Any]]: 去重后的工具调用列表
        """
        if not tool_calls:
            return tool_calls

        seen = set()
        deduplicated = []

        for call in tool_calls:
            function_info = call.get("function", {})
            fn_name = function_info.get("name", "")
            args_str = function_info.get("arguments", "{}")

            # 标准化arguments字符串以便比较
            try:
                import json

                # 解析并重新序列化以标准化格式
                args_obj = json.loads(args_str) if args_str else {}
                normalized_args = json.dumps(args_obj, sort_keys=True, separators=(",", ":"))
            except (json.JSONDecodeError, TypeError):
                # 如果解析失败，直接使用原始字符串
                normalized_args = args_str

            # 创建去重键
            dedup_key = (fn_name, normalized_args)

            if dedup_key not in seen:
                deduplicated.append(call)
                seen.add(dedup_key)
                logger.debug(f"✅ [DeepSeek去重] 保留工具调用: {fn_name}")
            else:
                logger.info(f"⚠️ [DeepSeek去重] 检测到重复工具调用，已跳过: {fn_name}({normalized_args[:100]}...)")

        if len(deduplicated) < len(tool_calls):
            logger.info(f"🔧 [DeepSeek去重] 原始调用数: {len(tool_calls)}, 去重后: {len(deduplicated)}")

        return deduplicated

    def merge_tool_call_fragments(self, fragments: List[Any]) -> List[Dict[str, Any]]:
        """合并工具调用分片并去重"""
        # 先使用父类方法合并片段
        merged_calls = super().merge_tool_call_fragments(fragments)
        # 然后对合并后的结果进行去重
        return self._deduplicate_tool_calls(merged_calls)

    def create_assistant_message(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建助手消息，自动去重工具调用"""
        # 对DeepSeek的工具调用进行去重处理
        deduplicated_calls = self._deduplicate_tool_calls(tool_calls)
        return super().create_assistant_message(deduplicated_calls)


class OllamaToolCaller(OpenAIToolCaller):
    """Ollama工具调用器"""

    def can_handle_streaming(self) -> bool:
        return False  # Ollama可能不支持流式工具调用

    def extract_tool_calls_from_stream(self, chunk: Any) -> List[Dict[str, Any]]:
        """Ollama的流式工具调用提取"""
        # Ollama可能不支持流式工具调用，返回空列表
        return []


def create_tool_caller(provider: str, tools: Optional[List[Any]] = None) -> ToolCaller:
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
