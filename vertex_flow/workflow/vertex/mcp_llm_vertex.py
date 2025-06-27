#!/usr/bin/env python3
"""
MCP-enabled LLM Vertex

Enhanced LLM Vertex with MCP (Model Context Protocol) integration.
Provides access to external resources, tools, and prompts through MCP.
Extends the base LLM vertex with minimal code duplication and full streaming support.
"""

import asyncio
import inspect
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Generator, List, Optional, Union

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.vertex import WorkflowContext

logger = LoggerUtil.get_logger(__name__)

# MCP support
try:
    from vertex_flow.mcp.types import MCPPrompt, MCPResource, MCPTool, MCPToolResult
    from vertex_flow.workflow.mcp_manager import get_mcp_manager

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP functionality not available")


class MCPLLMVertex(LLMVertex):
    """
    LLM Vertex with MCP integration support

    This class extends the base LLMVertex to add MCP capabilities while maintaining
    full compatibility with all parent class features including streaming, reasoning,
    and tool calling.

    Key features:
    - Full streaming support with MCP context
    - Async MCP tool integration
    - Resource and prompt access
    - Context enhancement
    - Minimal code duplication
    """

    def __init__(self, id: str, **kwargs):
        # Extract MCP-specific parameters
        self.mcp_enabled = kwargs.pop("mcp_enabled", True) and MCP_AVAILABLE
        self.mcp_context_enabled = kwargs.pop("mcp_context_enabled", True)
        self.mcp_tools_enabled = kwargs.pop("mcp_tools_enabled", True)
        self.mcp_prompts_enabled = kwargs.pop("mcp_prompts_enabled", True)

        # Initialize parent class
        super().__init__(id, **kwargs)

        # MCP-specific state
        self._mcp_resources_cache: Optional[List[MCPResource]] = None
        self._mcp_tools_cache: Optional[List[MCPTool]] = None
        self._mcp_prompts_cache: Optional[List[MCPPrompt]] = None
        self._mcp_context_cache: Optional[str] = None
        self._mcp_context_cache_time: float = 0
        self._mcp_cache_ttl: float = 300.0  # 5 minutes cache TTL

        # Add LLM format tools cache to avoid frequent conversion
        self._mcp_llm_tools_cache: Optional[List[Dict[str, Any]]] = None
        self._mcp_llm_tools_cache_time: float = 0

        # Thread pool for async operations
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mcp_llm")

        logger.info(f"MCPLLMVertex {id} initialized with MCP enabled: {self.mcp_enabled}")

    def __del__(self):
        """Cleanup thread pool on deletion"""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)

    def messages_redirect(self, inputs: Dict[str, Any], context: WorkflowContext):
        """
        Override messages_redirect to add MCP context enhancement

        This method extends the parent's message processing to include MCP context
        when available, while maintaining full compatibility with the parent implementation.
        """
        # Call parent implementation first
        super().messages_redirect(inputs, context)

        # Add MCP context if enabled
        if self.mcp_enabled and self.mcp_context_enabled:
            self._add_mcp_context_to_messages()

    def _add_mcp_context_to_messages(self):
        """Add MCP context to messages in a thread-safe way"""
        try:
            # Get MCP context (with caching)
            mcp_context = self._get_mcp_context_sync()

            if mcp_context:
                # Find or create system message
                system_message_idx = None
                for i, msg in enumerate(self.messages):
                    if msg.get("role") == "system":
                        system_message_idx = i
                        break

                if system_message_idx is not None:
                    # Append to existing system message
                    self.messages[system_message_idx]["content"] += f"\n\nMCP Context:\n{mcp_context}"
                else:
                    # Insert new system message at the beginning
                    self.messages.insert(0, {"role": "system", "content": f"MCP Context:\n{mcp_context}"})

                logger.debug("Added MCP context to messages")

        except Exception as e:
            logger.warning(f"Failed to add MCP context: {e}")

    def _get_mcp_context_sync(self) -> Optional[str]:
        """Get MCP context synchronously with caching"""
        import time

        # Check cache validity
        current_time = time.time()
        if self._mcp_context_cache and current_time - self._mcp_context_cache_time < self._mcp_cache_ttl:
            return self._mcp_context_cache

        # Get fresh context
        try:
            # Use thread pool to run async operation
            future = self._executor.submit(self._get_mcp_context_async)
            mcp_context = future.result(timeout=15.0)  # 增加超时时间到15秒

            # Update cache
            self._mcp_context_cache = mcp_context
            self._mcp_context_cache_time = current_time

            return mcp_context

        except Exception as e:
            logger.warning(f"Failed to get MCP context: {e}")
            return None

    def _get_mcp_context_async(self) -> Optional[str]:
        """Get MCP context asynchronously"""
        if not MCP_AVAILABLE:
            return None

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self._fetch_mcp_context())
        finally:
            loop.close()

    async def _fetch_mcp_context(self) -> str:
        """Fetch MCP context information with timeout"""
        context_parts = []
        mcp_manager = get_mcp_manager()

        try:
            # Get available resources
            if self._mcp_resources_cache is None:
                self._mcp_resources_cache = mcp_manager.get_all_resources()

            if self._mcp_resources_cache:
                resources_info = []
                for resource in self._mcp_resources_cache[:10]:  # Limit to first 10
                    resources_info.append(f"- {resource.name}: {resource.description}")
                context_parts.append("Available Resources:\n" + "\n".join(resources_info))

            # Get available tools
            if self._mcp_tools_cache is None:
                self._mcp_tools_cache = mcp_manager.get_all_tools()

            if self._mcp_tools_cache:
                tools_info = []
                for tool in self._mcp_tools_cache[:10]:  # Limit to first 10
                    tools_info.append(f"- {tool.name}: {tool.description}")
                context_parts.append("Available Tools:\n" + "\n".join(tools_info))

            # Get available prompts
            if self._mcp_prompts_cache is None:
                self._mcp_prompts_cache = mcp_manager.get_all_prompts()

            if self._mcp_prompts_cache:
                prompts_info = []
                for prompt in self._mcp_prompts_cache[:5]:  # Limit to first 5
                    prompts_info.append(f"- {prompt.name}: {prompt.description}")
                context_parts.append("Available Prompts:\n" + "\n".join(prompts_info))

        except Exception as e:
            logger.error(f"Error fetching MCP context: {e}")

        return "\n\n".join(context_parts)

    def _build_llm_tools(self):
        """
        Override to add MCP tools to the base tools with deduplication

        This method extends the parent's tool building to include MCP tools
        while preserving all existing functionality and preventing duplicates.
        """
        # Get base tools from parent
        base_tools = super()._build_llm_tools() or []

        # Create a set to track tool names for deduplication
        existing_tool_names = set()
        deduplicated_tools = []

        # First, add all base tools and track their names
        for tool in base_tools:
            if isinstance(tool, dict) and "function" in tool and "name" in tool["function"]:
                tool_name = tool["function"]["name"]
                if tool_name not in existing_tool_names:
                    existing_tool_names.add(tool_name)
                    deduplicated_tools.append(tool)
                    logger.debug(f"Added base tool: {tool_name}")
                else:
                    logger.warning(f"Duplicate base tool found and skipped: {tool_name}")
            else:
                # Add tools that don't follow expected format (defensive programming)
                deduplicated_tools.append(tool)

        # Add MCP tools if enabled, using cache to avoid frequent refresh
        if self.mcp_enabled and self.mcp_tools_enabled:
            try:
                # Use cached LLM format tools to avoid frequent conversion
                mcp_tools = self._get_cached_mcp_llm_tools()
                if mcp_tools:
                    mcp_added_count = 0
                    mcp_skipped_count = 0

                    for mcp_tool in mcp_tools:
                        if isinstance(mcp_tool, dict) and "function" in mcp_tool and "name" in mcp_tool["function"]:
                            mcp_tool_name = mcp_tool["function"]["name"]

                            # Check for duplicates (including MCP prefix consideration)
                            if mcp_tool_name not in existing_tool_names:
                                existing_tool_names.add(mcp_tool_name)
                                deduplicated_tools.append(mcp_tool)
                                mcp_added_count += 1
                                logger.debug(f"Added MCP tool: {mcp_tool_name}")
                            else:
                                mcp_skipped_count += 1
                                logger.warning(f"Duplicate MCP tool found and skipped: {mcp_tool_name}")
                        else:
                            # Add MCP tools that don't follow expected format (defensive programming)
                            deduplicated_tools.append(mcp_tool)
                            mcp_added_count += 1

                    logger.info(f"MCP tools processed: {mcp_added_count} added, {mcp_skipped_count} duplicates skipped")
                else:
                    logger.debug("No MCP tools available, continuing with base tools only")

            except Exception as e:
                logger.debug(f"MCP tools not available, continuing with base tools only: {e}")

        # Log final tool summary
        total_tools = len(deduplicated_tools)
        if total_tools > 0:
            tool_names = []
            for tool in deduplicated_tools:
                if isinstance(tool, dict) and "function" in tool and "name" in tool["function"]:
                    tool_names.append(tool["function"]["name"])
            logger.info(f"Final tool list ({total_tools} tools): {', '.join(tool_names)}")

        return deduplicated_tools if deduplicated_tools else None

    def _get_cached_mcp_llm_tools(self) -> List[Dict[str, Any]]:
        """Get cached LLM format MCP tools, refresh only if needed"""
        import time

        current_time = time.time()

        # Check if cache is valid
        if (
            self._mcp_llm_tools_cache is not None
            and current_time - self._mcp_llm_tools_cache_time < self._mcp_cache_ttl
        ):
            logger.debug("Using cached MCP LLM tools")
            return self._mcp_llm_tools_cache

        # Cache expired or not initialized, refresh
        logger.debug("Refreshing MCP LLM tools cache")
        try:
            # Use thread pool to run async operation
            future = self._executor.submit(self._get_mcp_tools_async)
            fresh_tools = future.result(timeout=10.0)

            # Update cache
            self._mcp_llm_tools_cache = fresh_tools
            self._mcp_llm_tools_cache_time = current_time

            return fresh_tools

        except Exception as e:
            logger.warning(f"Failed to refresh MCP tools cache: {e}")
            # Return cached version if available, even if expired
            return self._mcp_llm_tools_cache or []

    def _get_mcp_tools_sync(self) -> List[Dict[str, Any]]:
        """Get MCP tools synchronously with reasonable timeout"""
        try:
            # Use thread pool to run async operation
            future = self._executor.submit(self._get_mcp_tools_async)
            return future.result(timeout=10.0)  # 增加超时时间到10秒，适应Gradio环境
        except Exception as e:
            logger.warning(f"Failed to get MCP tools sync: {e}")
            return []

    def _get_mcp_tools_async(self) -> List[Dict[str, Any]]:
        """Get MCP tools asynchronously"""
        if not MCP_AVAILABLE:
            return []

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self._fetch_mcp_tools())
        finally:
            loop.close()

    async def _fetch_mcp_tools(self) -> List[Dict[str, Any]]:
        """Fetch MCP tools in LLM format with reasonable timeout"""
        mcp_manager = get_mcp_manager()
        llm_tools = []

        try:
            if self._mcp_tools_cache is None:
                # Check for MCP tools with reasonable timeout for Gradio environment
                try:
                    logger.debug("Fetching MCP tools for Gradio environment")
                    self._mcp_tools_cache = mcp_manager.get_all_tools()

                    if self._mcp_tools_cache:
                        logger.info(f"Successfully fetched {len(self._mcp_tools_cache)} MCP tools")
                    else:
                        logger.debug("No MCP tools returned, continuing without MCP tools")
                        self._mcp_tools_cache = []

                except asyncio.TimeoutError:
                    logger.warning("MCP tools fetch timeout (8s), continuing without MCP tools")
                    self._mcp_tools_cache = []
                except Exception as e:
                    logger.warning(f"MCP tools fetch failed, continuing without MCP tools: {e}")
                    self._mcp_tools_cache = []

            # Convert MCP tools to LLM format
            if self._mcp_tools_cache:
                for tool in self._mcp_tools_cache:
                    llm_tool = {
                        "type": "function",
                        "function": {
                            "name": f"mcp_{tool.name}",  # Prefix to identify MCP tools
                            "description": tool.description,
                            "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                        },
                    }
                    llm_tools.append(llm_tool)

            # Log the results
            if llm_tools:
                tool_names = [tool["function"]["name"] for tool in llm_tools]
                logger.info(f"MCP tools available: {tool_names}")
            else:
                logger.info("No MCP tools available")

        except Exception as e:
            logger.error(f"Error fetching MCP tools: {e}")

        return llm_tools

    def _handle_tool_calls(self, choice, context: WorkflowContext):
        """Handle tool calls including MCP tools"""
        if not hasattr(choice, "message") or not hasattr(choice.message, "tool_calls"):
            return

        # 首先添加assistant消息（包含tool_calls）
        if hasattr(choice.message, "content") and choice.message.content:
            self.messages.append(
                {
                    "role": "assistant",
                    "content": choice.message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                        }
                        for tool_call in choice.message.tool_calls
                    ],
                }
            )
        else:
            self.messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                        }
                        for tool_call in choice.message.tool_calls
                    ],
                }
            )

        # 分离MCP工具和常规工具
        mcp_tool_calls = []
        regular_tool_calls = []

        for tool_call in choice.message.tool_calls:
            if hasattr(tool_call, "function") and tool_call.function:
                function_name = tool_call.function.name
                if function_name.startswith("mcp_"):  # 修复：使用mcp_前缀识别MCP工具
                    mcp_tool_calls.append(tool_call)
                else:
                    regular_tool_calls.append(tool_call)

        # 处理MCP工具调用
        for tool_call in mcp_tool_calls:
            try:
                self._handle_mcp_tool_call(tool_call)
            except Exception as e:
                logger.error(f"Error handling MCP tool call: {e}")
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": getattr(tool_call, "id", "unknown"),
                        "content": f"Error calling MCP tool: {str(e)}",
                    }
                )

        # 处理常规工具调用
        if regular_tool_calls:
            # 创建包含常规工具调用的choice对象，但不重复添加assistant消息
            class MockChoice:
                def __init__(self, original_choice, filtered_tool_calls):
                    self.finish_reason = "tool_calls"
                    self.message = type(
                        "MockMessage",
                        (),
                        {"tool_calls": filtered_tool_calls, "role": "assistant", "content": None},
                    )()

            mock_choice = MockChoice(choice, regular_tool_calls)

            # 临时保存当前消息长度，避免重复添加assistant消息
            original_length = len(self.messages)
            super()._handle_tool_calls(mock_choice, context)

            # 如果父类添加了重复的assistant消息，移除它
            if len(self.messages) > original_length:
                # 检查是否有重复的assistant消息
                for i in range(original_length, len(self.messages)):
                    if self.messages[i].get("role") == "assistant" and "tool_calls" in self.messages[i]:
                        # 移除重复的assistant消息
                        self.messages.pop(i)
                        break

    def _handle_mcp_tool_call(self, tool_call):
        """Handle a single MCP tool call"""
        try:
            # Use thread pool to run async operation
            future = self._executor.submit(self._call_mcp_tool_async, tool_call)
            result = future.result(timeout=30.0)  # 30 second timeout for tool calls

            # Add tool result to messages
            self.messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_call.function.name}: {e}")
            # Add error message
            self.messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": f"Error calling tool: {str(e)}"}
            )

    def _call_mcp_tool_async(self, tool_call) -> str:
        """Call MCP tool asynchronously"""
        if not MCP_AVAILABLE:
            return "MCP functionality not available"

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self._execute_mcp_tool(tool_call))
        finally:
            loop.close()

    async def _execute_mcp_tool(self, tool_call) -> str:
        """Execute MCP tool call"""
        try:
            # Parse the tool call
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

            # Remove the mcp_ prefix to get the original tool name
            if tool_name.startswith("mcp_"):
                original_tool_name = tool_name[4:]  # Remove "mcp_" prefix
            else:
                original_tool_name = tool_name

            logger.info(f"Executing MCP tool: {original_tool_name} with arguments: {arguments}")

            # Call the MCP tool
            mcp_manager = get_mcp_manager()
            result = mcp_manager.call_tool(original_tool_name, arguments)

            if result and result.content:
                if isinstance(result.content, list):
                    # Handle list of content items
                    content_parts = []
                    for item in result.content:
                        if hasattr(item, "text"):
                            content_parts.append(item.text)
                        elif isinstance(item, dict) and "text" in item:
                            content_parts.append(item["text"])
                        else:
                            content_parts.append(str(item))
                    return "\n".join(content_parts)
                else:
                    return str(result.content)
            else:
                return f"MCP tool {original_tool_name} executed successfully but returned no content"

        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_name}: {e}")
            return f"Error executing MCP tool {tool_name}: {str(e)}"

    # === Streaming Support ===

    def chat_stream_generator(
        self, inputs: Dict[str, Any], context: WorkflowContext = None
    ) -> Generator[str, None, None]:
        """Generate streaming chat response with MCP support"""
        # 使用父类的流式生成器，MCP工具会在_build_llm_tools中自动添加
        yield from super().chat_stream_generator(inputs, context)

    def _chat_stream_with_tools(
        self, inputs: Dict[str, Any], context: WorkflowContext, tools: List[Dict[str, Any]]
    ) -> Generator[str, None, None]:
        """Stream chat with tool calling support"""
        try:
            # Use the model's streaming with tools
            for chunk in self.model.chat_stream(self.messages, tools=tools):
                yield chunk

        except Exception as e:
            logger.error(f"Error in streaming with tools: {e}")
            yield f"Error: {str(e)}"

    def _chat_stream(self, inputs: Dict[str, Any], context: Optional[WorkflowContext] = None):
        """Regular chat stream without tools"""
        if context is None:
            context = WorkflowContext()

        try:
            # Use parent's chat stream method
            for chunk in self.model.chat_stream(self.messages):
                yield chunk
        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield f"Error: {str(e)}"

    # === MCP Utility Methods ===

    def chat(self, inputs: Dict[str, Any], context: Union[WorkflowContext, None] = None):
        """
        Override chat method to fix parent class bug and add MCP support

        This method fixes the _build_llm_option parameter issue in the parent class
        while maintaining full MCP integration.
        """
        finish_reason = None
        if self.enable_stream and hasattr(self.model, "chat_stream"):
            return self._chat_stream(inputs, context)

        llm_tools = self._build_llm_tools()
        option = self._build_llm_option(inputs, context) if context else {}

        while finish_reason is None or finish_reason == "tool_calls":
            choice = self.model.chat(self.messages, option=option, tools=llm_tools)
            finish_reason = choice.finish_reason
            if finish_reason == "tool_calls":
                self._handle_tool_calls(choice, context)

        result = (
            choice.message.content
            if self.postprocess is None
            else self.postprocess(choice.message.content, inputs, context)
        )

        logger.debug(f"MCP chat bot response: {result}")
        return result

    async def read_mcp_resource(self, resource_uri: str) -> Optional[str]:
        """Read an MCP resource by URI"""
        try:
            mcp_manager = get_mcp_manager()
            return mcp_manager.read_resource(resource_uri)
        except Exception as e:
            logger.error(f"Error reading MCP resource {resource_uri}: {e}")
            return None

    async def get_mcp_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get an MCP prompt by name"""
        try:
            mcp_manager = get_mcp_manager()
            return mcp_manager.get_prompt(prompt_name, arguments)
        except Exception as e:
            logger.error(f"Error getting MCP prompt {prompt_name}: {e}")
            return None

    def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP status information"""
        if not MCP_AVAILABLE:
            return {"available": False, "reason": "MCP not installed"}

        try:
            mcp_manager = get_mcp_manager()
            connected_clients = mcp_manager.get_connected_clients()

            return {
                "available": True,
                "enabled": self.mcp_enabled,
                "connected_clients": connected_clients,
                "context_enabled": self.mcp_context_enabled,
                "tools_enabled": self.mcp_tools_enabled,
                "prompts_enabled": self.mcp_prompts_enabled,
                "cache_status": {
                    "resources_cached": self._mcp_resources_cache is not None,
                    "tools_cached": self._mcp_tools_cache is not None,
                    "prompts_cached": self._mcp_prompts_cache is not None,
                    "context_cached": self._mcp_context_cache is not None,
                },
            }
        except Exception as e:
            return {"available": False, "reason": str(e)}

    def clear_mcp_cache(self):
        """Clear all MCP caches to force refresh"""
        logger.info("Clearing MCP caches")
        self._mcp_resources_cache = None
        self._mcp_tools_cache = None
        self._mcp_prompts_cache = None
        self._mcp_context_cache = None
        self._mcp_context_cache_time = 0
        # Clear LLM format tools cache as well
        self._mcp_llm_tools_cache = None
        self._mcp_llm_tools_cache_time = 0

    def set_mcp_cache_ttl(self, ttl_seconds: float):
        """Set MCP cache TTL in seconds"""
        self._mcp_cache_ttl = ttl_seconds
        logger.info(f"MCP cache TTL set to {ttl_seconds} seconds")


def create_mcp_llm_vertex(vertex_id: str, **kwargs) -> MCPLLMVertex:
    """
    Create an MCP-enabled LLM vertex

    Args:
        vertex_id: Unique identifier for the vertex
        **kwargs: Additional parameters including:
            - mcp_enabled: Enable MCP functionality (default: True)
            - mcp_context_enabled: Enable MCP context enhancement (default: True)
            - mcp_tools_enabled: Enable MCP tools (default: True)
            - mcp_prompts_enabled: Enable MCP prompts (default: True)
            - All other LLMVertex parameters

    Returns:
        MCPLLMVertex instance with MCP capabilities
    """
    return MCPLLMVertex(vertex_id, **kwargs)
