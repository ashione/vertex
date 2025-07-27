#!/usr/bin/env python3
"""
MCP Manager for Vertex Flow

Manages MCP client connections and provides unified access to MCP resources, tools, and prompts.
"""

import asyncio
import atexit
import json
import signal
import sys
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Union

from vertex_flow.utils.logger import LoggerUtil

logger = LoggerUtil.get_logger(__name__)

# MCP support
try:
    from vertex_flow.mcp.client import MCPClient as MCPVertexFlowClient
    from vertex_flow.mcp.types import MCPClientInfo, MCPPrompt, MCPResource, MCPTool, MCPToolResult

    MCP_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MCP dependencies not available: {e}")
    MCP_AVAILABLE = False
    MCPVertexFlowClient = None
    MCPPrompt = MCPResource = MCPTool = MCPToolResult = MCPClientInfo = None


class MCPRequest:
    """MCP请求对象"""

    def __init__(self, request_type: str, **kwargs):
        self.id = str(uuid.uuid4())
        self.request_type = request_type
        self.kwargs = kwargs
        self.future: asyncio.Future = asyncio.Future()


class MCPManager:
    """Thread-safe MCP Manager using single event loop and async queues"""

    def __init__(self):
        self.clients: Dict[str, MCPVertexFlowClient] = {}
        self.client_configs: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        self._lock = threading.RLock()

        # Event loop and queue for thread-safe communication
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._request_queue: Optional[asyncio.Queue] = None
        self._running = False

        # Start the dedicated event loop thread
        self._start_event_loop_thread()

    def _start_event_loop_thread(self):
        """启动专用的事件循环线程"""

        def run_event_loop():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            self._request_queue = asyncio.Queue()
            self._running = True

            logger.info("MCP Manager event loop thread started")

            # 启动请求处理任务
            self._event_loop.create_task(self._process_requests())

            try:
                self._event_loop.run_forever()
            except Exception as e:
                logger.error(f"Event loop error: {e}")
            finally:
                logger.info("MCP Manager event loop thread stopped")

        self._loop_thread = threading.Thread(target=run_event_loop, daemon=True)
        self._loop_thread.start()

        # 等待事件循环启动
        timeout = 5.0
        start_time = time.time()
        while self._event_loop is None and (time.time() - start_time) < timeout:
            time.sleep(0.01)

        if self._event_loop is None:
            raise RuntimeError("Failed to start MCP event loop thread")

    async def _process_requests(self):
        """处理来自其他线程的请求"""
        while self._running:
            try:
                request = await self._request_queue.get()
                if request is None:  # 停止信号
                    break

                try:
                    result = await self._handle_request(request)
                    if not request.future.done():
                        request.future.set_result(result)
                except Exception as e:
                    if not request.future.done():
                        request.future.set_exception(e)
                finally:
                    self._request_queue.task_done()

            except Exception as e:
                logger.error(f"Error processing request: {e}")

    async def _handle_request(self, request: MCPRequest):
        """处理具体的MCP请求"""
        request_type = request.request_type
        kwargs = request.kwargs

        if request_type == "initialize":
            return await self._async_initialize(kwargs.get("mcp_config", {}))
        elif request_type == "get_all_tools":
            return await self._async_get_all_tools()
        elif request_type == "get_all_resources":
            return await self._async_get_all_resources()
        elif request_type == "get_all_prompts":
            return await self._async_get_all_prompts()
        elif request_type == "call_tool":
            return await self._async_call_tool(
                kwargs.get("tool_name"), kwargs.get("arguments", {}), kwargs.get("tool_call_id")
            )
        elif request_type == "read_resource":
            return await self._async_read_resource(kwargs.get("resource_uri"))
        elif request_type == "get_prompt":
            return await self._async_get_prompt(kwargs.get("prompt_name"), kwargs.get("arguments"))
        elif request_type == "close_all":
            return await self._async_close_all()
        elif request_type == "refresh_client":
            return await self._async_refresh_client(kwargs.get("client_name"))
        else:
            raise ValueError(f"Unknown request type: {request_type}")

    def _submit_request(self, request_type: str, **kwargs) -> Any:
        """线程安全地提交请求到事件循环"""
        if not self._running or not self._event_loop:
            raise RuntimeError("MCP Manager not running")

        request = MCPRequest(request_type, **kwargs)

        # 将请求提交到事件循环
        future = asyncio.run_coroutine_threadsafe(self._request_queue.put(request), self._event_loop)
        future.result(timeout=1.0)  # 等待请求入队

        # 等待请求处理完成
        timeout_seconds = 60.0
        start_time = time.time()

        while not request.future.done():
            if time.time() - start_time > timeout_seconds:
                logger.error(f"Request {request_type} timed out after {timeout_seconds}s")
                raise RuntimeError(f"Request {request_type} timed out")
            time.sleep(0.01)  # 10ms polling

        return request.future.result()

    # 公共接口方法 - 线程安全
    def initialize(self, mcp_config: Dict[str, Any]):
        """Initialize MCP clients from configuration - thread safe"""
        return self._submit_request("initialize", mcp_config=mcp_config)

    def get_all_tools(self) -> List[MCPTool]:
        """Get all tools from all connected MCP clients - thread safe"""
        return self._submit_request("get_all_tools")

    def get_all_resources(self) -> List[MCPResource]:
        """Get all resources from all connected MCP clients - thread safe"""
        return self._submit_request("get_all_resources")

    def get_all_prompts(self) -> List[MCPPrompt]:
        """Get all prompts from all connected MCP clients - thread safe"""
        return self._submit_request("get_all_prompts")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any], tool_call_id: str = None) -> Optional[MCPToolResult]:
        """Call a tool from appropriate MCP client - thread safe"""
        import json

        logger.info(f"🔧 [MCPManager] Calling MCP tool: {tool_name} with arguments: {arguments}")
        if tool_call_id:
            logger.info(f"🔧 [MCPManager] Tool Call ID: {tool_call_id}")
        logger.info(f"🔧 [MCPManager] Tool Name: {tool_name}")
        logger.info(f"🔧 [MCPManager] Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")

        result = self._submit_request("call_tool", tool_name=tool_name, arguments=arguments, tool_call_id=tool_call_id)

        if tool_call_id:
            logger.info(f"🔧 [MCPManager] Result for Tool Call ID {tool_call_id} - Tool Name: {tool_name}")
        else:
            logger.info(f"🔧 [MCPManager] Result - Tool Name: {tool_name}")
        logger.info(f"🔧 [MCPManager] Result Type: {type(result)}")
        if result:
            logger.info(f"🔧 [MCPManager] Content Type: {type(result.content)}")
            logger.info(f"🔧 [MCPManager] Content: {result.content}")
            if hasattr(result, "__dict__"):
                logger.info(f"🔧 [MCPManager] Attributes: {result.__dict__}")
        else:
            logger.info(f"🔧 [MCPManager] Result: None")

        logger.info(f"🔧 [MCPManager] Tool {tool_name} completed with result type: {type(result)}")
        return result

    def read_resource(self, resource_uri: str) -> Optional[str]:
        """Read a resource by URI - thread safe"""
        return self._submit_request("read_resource", resource_uri=resource_uri)

    def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get a prompt by name - thread safe"""
        return self._submit_request("get_prompt", prompt_name=prompt_name, arguments=arguments)

    def close_all(self):
        """Close all MCP client connections - thread safe"""
        return self._submit_request("close_all")

    def refresh_client(self, client_name: str):
        """Refresh a specific MCP client - thread safe"""
        return self._submit_request("refresh_client", client_name=client_name)

    # 异步实现方法 - 在专用事件循环中运行
    async def _async_initialize(self, mcp_config: Dict[str, Any]):
        """Initialize MCP clients from configuration"""
        if not MCP_AVAILABLE:
            logger.warning("MCP dependencies not available")
            return

        logger.info("Initializing MCP Manager")

        clients_config = mcp_config.get("clients", {})
        for client_name, client_config in clients_config.items():
            if client_config.get("enabled", False):
                await self._create_client(client_name, client_config)

        self._initialized = True
        logger.info(f"MCP Manager initialized with {len(self.clients)} clients")

    async def _create_client(self, client_name: str, client_config: Dict[str, Any]):
        """Create and initialize a single MCP client"""
        try:
            client_info = MCPClientInfo(name=client_name, version="1.0.0")
            client = MCPVertexFlowClient(client_info)

            transport = client_config.get("transport", "stdio")
            if transport == "stdio":
                command = client_config.get("command", "")
                args = client_config.get("args", [])
                env = client_config.get("env", {})

                # Set environment variables
                if env:
                    import os

                    for key, value in env.items():
                        os.environ[key] = value

                await client.connect_stdio(command, *args)
            elif transport == "http":
                base_url = client_config.get("base_url", "")
                await client.connect_http(base_url)
            else:
                raise ValueError(f"Unsupported transport: {transport}")

            self.clients[client_name] = client
            self.client_configs[client_name] = client_config

            logger.info(f"Successfully initialized MCP client: {client_name}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP client {client_name}: {e}")

    async def _async_get_all_tools(self) -> List[MCPTool]:
        """Get all tools from all connected MCP clients"""
        if not MCP_AVAILABLE:
            return []

        if not self._initialized:
            logger.warning("MCP Manager not initialized")
            return []

        all_tools = []

        for client_name, client in self.clients.items():
            try:
                if client.is_connected:
                    logger.debug(f"Getting tools from client {client_name}")
                    tools = await asyncio.wait_for(client.list_tools(), timeout=15.0)
                    logger.info(f"Got {len(tools)} tools from client {client_name}")

                    # Add client name prefix to avoid conflicts
                    for tool in tools:
                        tool.name = f"{client_name}_{tool.name}"
                        tool.description = f"[{client_name}] {tool.description or ''}"

                    all_tools.extend(tools)
                else:
                    logger.debug(f"Client {client_name} not connected, skipping")

            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting tools from client {client_name}")
                continue
            except Exception as e:
                logger.error(f"Error processing client {client_name}: {e}")
                continue

        logger.info(f"Total tools collected: {len(all_tools)}")
        return all_tools

    async def _async_get_all_resources(self) -> List[MCPResource]:
        """Get all resources from all connected MCP clients"""
        if not MCP_AVAILABLE:
            return []

        if not self._initialized:
            return []

        all_resources = []

        for client_name, client in self.clients.items():
            try:
                if client.is_connected:
                    resources = await asyncio.wait_for(client.list_resources(), timeout=15.0)
                    logger.info(f"Got {len(resources)} resources from client {client_name}")

                    # Add client name prefix to avoid conflicts
                    for resource in resources:
                        resource.name = f"{client_name}_{resource.name}"
                        if resource.description:
                            resource.description = f"[{client_name}] {resource.description}"

                    all_resources.extend(resources)

            except Exception as e:
                logger.error(f"Error processing client {client_name}: {e}")
                continue

        logger.info(f"Total resources collected: {len(all_resources)}")
        return all_resources

    async def _async_get_all_prompts(self) -> List[MCPPrompt]:
        """Get all prompts from all connected MCP clients"""
        if not MCP_AVAILABLE:
            return []

        if not self._initialized:
            return []

        all_prompts = []

        for client_name, client in self.clients.items():
            try:
                if client.is_connected:
                    prompts = await client.list_prompts()
                    # Add client name prefix to avoid conflicts
                    for prompt in prompts:
                        prompt.name = f"{client_name}:{prompt.name}"
                        prompt.description = f"[{client_name}] {prompt.description or ''}"
                    all_prompts.extend(prompts)

            except Exception as e:
                logger.error(f"Failed to get prompts from client {client_name}: {e}")

        return all_prompts

    async def _async_call_tool(
        self, tool_name: str, arguments: Dict[str, Any], tool_call_id: str = None
    ) -> Optional[MCPToolResult]:
        """Call a tool from appropriate MCP client with enhanced error handling"""
        if not MCP_AVAILABLE:
            # 返回错误结果而不是None，确保错误信息能传递给LLM
            from vertex_flow.mcp.types import MCPToolResult

            error_msg = "MCP is not available in this environment"
            if tool_call_id:
                logger.error(f"🔧 [MCPManager._async_call_tool] Tool Call ID {tool_call_id} - {error_msg}")
            else:
                logger.error(f"🔧 [MCPManager._async_call_tool] {error_msg}")
            return MCPToolResult(content=[{"type": "text", "text": error_msg}], isError=True)

        import json

        if "_" not in tool_name:
            error_msg = f"Invalid tool name format: {tool_name}"
            if tool_call_id:
                logger.error(f"🔧 [MCPManager._async_call_tool] Tool Call ID {tool_call_id} - {error_msg}")
            else:
                logger.error(f"🔧 [MCPManager._async_call_tool] {error_msg}")
            from vertex_flow.mcp.types import MCPToolResult

            return MCPToolResult(content=[{"type": "text", "text": error_msg}], isError=True)

        client_name, original_tool_name = tool_name.split("_", 1)

        logger.debug(f"🔧 [MCPManager._async_call_tool] Calling tool {original_tool_name} from client {client_name}")
        if tool_call_id:
            logger.info(f"🔧 [MCPManager._async_call_tool] Tool Call ID: {tool_call_id}")
        logger.info(f"🔧 [MCPManager._async_call_tool] Tool Name: {tool_name}")
        logger.info(f"🔧 [MCPManager._async_call_tool] Client Name: {client_name}")
        logger.info(f"🔧 [MCPManager._async_call_tool] Original Tool Name: {original_tool_name}")
        logger.info(
            f"🔧 [MCPManager._async_call_tool] Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}"
        )

        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                client = self.clients.get(client_name)
                if not client:
                    error_msg = f"Client {client_name} not found"
                    logger.error(error_msg)
                    from vertex_flow.mcp.types import MCPToolResult

                    return MCPToolResult(content=[{"type": "text", "text": error_msg}], isError=True)

                # 检查客户端连接状态，但不强制重连以避免进程终止
                if not client.is_connected:
                    logger.warning(f"Client {client_name} not connected")
                    # 尝试重连，但如果失败不要终止整个流程
                    try:
                        await self._async_refresh_client(client_name)
                        client = self.clients.get(client_name)
                        if not client or not client.is_connected:
                            error_msg = f"Client {client_name} connection failed"
                            logger.error(error_msg)
                            if attempt == max_retries:  # 最后一次尝试失败
                                from vertex_flow.mcp.types import MCPToolResult

                                return MCPToolResult(content=[{"type": "text", "text": error_msg}], isError=True)
                            continue
                    except Exception as refresh_error:
                        logger.error(f"Failed to refresh client {client_name}: {refresh_error}")
                        if attempt == max_retries:  # 最后一次尝试失败
                            from vertex_flow.mcp.types import MCPToolResult

                            return MCPToolResult(
                                content=[{"type": "text", "text": f"Client refresh failed: {refresh_error}"}],
                                isError=True,
                            )
                        continue

                if tool_call_id:
                    logger.info(
                        f"🔧 [MCPManager._async_call_tool] Tool Call ID {tool_call_id} - Calling tool {original_tool_name} with arguments: {arguments} (attempt {attempt + 1})"
                    )
                else:
                    logger.info(
                        f"🔧 [MCPManager._async_call_tool] Calling tool {original_tool_name} with arguments: {arguments} (attempt {attempt + 1})"
                    )
                logger.info(f"🔧 [MCPManager._async_call_tool] Client: {client_name} (Attempt {attempt + 1})")
                logger.info(f"🔧 [MCPManager._async_call_tool] Tool: {original_tool_name} (Attempt {attempt + 1})")
                logger.info(
                    f"🔧 [MCPManager._async_call_tool] Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)} (Attempt {attempt + 1})"
                )
                logger.info(
                    f"🔧 [MCPManager._async_call_tool] Client Connected: {client.is_connected} (Attempt {attempt + 1})"
                )

                try:
                    # 使用更短的超时时间，避免长时间阻塞
                    result = await asyncio.wait_for(client.call_tool(original_tool_name, arguments), timeout=20.0)

                    if result:
                        if tool_call_id:
                            logger.info(
                                f"🔧 [MCPManager._async_call_tool] Tool Call ID {tool_call_id} - Client Result - Tool: {original_tool_name}"
                            )
                        else:
                            logger.info(f"🔧 [MCPManager._async_call_tool] Client Result - Tool: {original_tool_name}")
                        logger.info(f"🔧 [MCPManager._async_call_tool] Result Type: {type(result)}")
                        logger.info(f"🔧 [MCPManager._async_call_tool] Content Type: {type(result.content)}")
                        logger.info(f"🔧 [MCPManager._async_call_tool] Content: {result.content}")
                        if hasattr(result, "__dict__"):
                            logger.info(f"🔧 [MCPManager._async_call_tool] Result Attributes: {result.__dict__}")
                        if tool_call_id:
                            logger.info(
                                f"🔧 [MCPManager._async_call_tool] Tool Call ID {tool_call_id} - Tool {original_tool_name} executed successfully"
                            )
                        else:
                            logger.info(
                                f"🔧 [MCPManager._async_call_tool] Tool {original_tool_name} executed successfully"
                            )
                        return result
                    else:
                        if tool_call_id:
                            logger.warning(
                                f"🔧 [MCPManager._async_call_tool] Tool Call ID {tool_call_id} - Tool {original_tool_name} returned empty result"
                            )
                        else:
                            logger.warning(
                                f"🔧 [MCPManager._async_call_tool] Tool {original_tool_name} returned empty result"
                            )
                        from vertex_flow.mcp.types import MCPToolResult

                        return MCPToolResult(
                            content=[{"type": "text", "text": f"Tool {original_tool_name} returned no content"}],
                            isError=False,
                        )

                except asyncio.TimeoutError as e:
                    last_error = f"Tool {original_tool_name} timed out after 20 seconds"
                    logger.warning(f"{last_error} (attempt {attempt + 1})")
                    if attempt < max_retries:
                        # 不要强制重连，只是等待后重试
                        await asyncio.sleep(1.0)
                        continue
                    else:
                        logger.error(
                            f"Tool {original_tool_name} failed after {max_retries + 1} attempts due to timeout"
                        )
                        from vertex_flow.mcp.types import MCPToolResult

                        return MCPToolResult(content=[{"type": "text", "text": last_error}], isError=True)

                except Exception as tool_error:
                    last_error = f"Tool execution error: {str(tool_error)}"
                    logger.error(f"Error calling tool {original_tool_name} (attempt {attempt + 1}): {tool_error}")
                    if attempt < max_retries:
                        await asyncio.sleep(1.0)
                        continue
                    else:
                        logger.error(f"Tool {original_tool_name} failed after {max_retries + 1} attempts")
                        from vertex_flow.mcp.types import MCPToolResult

                        return MCPToolResult(content=[{"type": "text", "text": last_error}], isError=True)

            except Exception as e:
                last_error = f"Client error: {str(e)}"
                logger.error(f"Error calling tool {original_tool_name} (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    # 不要强制重连客户端，避免进程终止
                    await asyncio.sleep(1.0)
                    continue
                else:
                    logger.error(f"Tool {original_tool_name} failed after {max_retries + 1} attempts")
                    from vertex_flow.mcp.types import MCPToolResult

                    return MCPToolResult(
                        content=[
                            {"type": "text", "text": last_error or f"Unknown error calling tool {original_tool_name}"}
                        ],
                        isError=True,
                    )

        # 如果所有重试都失败，返回错误结果
        from vertex_flow.mcp.types import MCPToolResult

        return MCPToolResult(
            content=[
                {
                    "type": "text",
                    "text": last_error
                    or f"Failed to execute tool {original_tool_name} after {max_retries + 1} attempts",
                }
            ],
            isError=True,
        )

    async def _async_read_resource(self, resource_uri: str) -> Optional[str]:
        """Read a resource by URI from appropriate MCP client"""
        if not MCP_AVAILABLE:
            return None

        if not self._initialized:
            return None

        for client_name, client in self.clients.items():
            try:
                if client.is_connected:
                    content = await client.read_resource(resource_uri)
                    return content
            except Exception as e:
                logger.debug(f"Client {client_name} cannot read resource {resource_uri}: {e}")
                continue

        logger.warning(f"No client can read resource: {resource_uri}")
        return None

    async def _async_get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get a prompt by name from appropriate MCP client"""
        if not MCP_AVAILABLE:
            return None

        if not self._initialized:
            return None

        # Parse prompt name to get client and original prompt name
        if ":" not in prompt_name:
            logger.error(f"Invalid prompt name format: {prompt_name}")
            return None

        client_name, original_prompt_name = prompt_name.split(":", 1)

        client = self.clients.get(client_name)
        if not client or not client.is_connected:
            logger.error(f"Client {client_name} not available")
            return None

        try:
            content = await client.get_prompt(original_prompt_name, arguments)
            return content
        except Exception as e:
            logger.error(f"Failed to get prompt {original_prompt_name} from client {client_name}: {e}")
            return None

    async def _async_close_all(self):
        """Close all MCP client connections"""
        logger.info("Closing all MCP client connections")

        for client_name, client in self.clients.items():
            try:
                await client.close()
                logger.debug(f"Closed client {client_name}")
            except Exception as e:
                logger.error(f"Error closing client {client_name}: {e}")

        self.clients.clear()
        self.client_configs.clear()
        self._initialized = False

    async def _async_refresh_client(self, client_name: str):
        """Refresh a specific MCP client connection"""
        if client_name not in self.client_configs:
            logger.error(f"Client config for {client_name} not found")
            return

        # Close existing client
        if client_name in self.clients:
            try:
                await self.clients[client_name].close()
            except Exception as e:
                logger.debug(f"Error closing client {client_name}: {e}")
            del self.clients[client_name]

        # Recreate client
        client_config = self.client_configs[client_name]
        await self._create_client(client_name, client_config)

        if client_name in self.clients:
            logger.info(f"Successfully refreshed MCP client: {client_name}")
        else:
            logger.error(f"Failed to refresh MCP client: {client_name}")

    def get_connected_clients(self) -> List[str]:
        """Get list of connected client names"""
        return [name for name, client in self.clients.items() if client.is_connected]

    def get_client_info(self, client_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific client"""
        client = self.clients.get(client_name)
        if not client:
            return None

        return {
            "name": client_name,
            "connected": client.is_connected,
            "server_info": (
                {
                    "name": client.server_info.name if client.server_info else "Unknown",
                    "version": client.server_info.version if client.server_info else "Unknown",
                }
                if client.server_info
                else None
            ),
            "config": self.client_configs.get(client_name, {}),
        }

    def shutdown(self):
        """Shutdown the MCP manager and event loop"""
        if self._running:
            self._running = False

            # 发送停止信号
            if self._event_loop and self._request_queue:
                future = asyncio.run_coroutine_threadsafe(self._request_queue.put(None), self._event_loop)
                try:
                    future.result(timeout=1.0)
                except Exception:
                    pass

            # 停止事件循环
            if self._event_loop:
                self._event_loop.call_soon_threadsafe(self._event_loop.stop)

            # 等待线程结束
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=5.0)

            logger.info("MCP Manager shutdown complete")


# Global MCP manager instance with module-level persistence
_mcp_manager: Optional[MCPManager] = None
_mcp_manager_lock = threading.Lock()


class MCPManagerSingleton:
    """Thread-safe singleton for MCP Manager"""

    _instance: Optional[MCPManager] = None
    _instance_created_time: Optional[float] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> MCPManager:
        """Get the singleton instance with thread safety and module reload detection"""
        with cls._lock:
            # Check if we have a valid instance
            if cls._instance is not None:
                # Simple validity check - if instance exists and is properly initialized, use it
                if hasattr(cls._instance, "_initialized"):
                    return cls._instance
                else:
                    logger.warning(f"Detected invalid MCP manager instance, creating new one")
                    cls._instance = None
                    cls._instance_created_time = None

            # Create new instance
            if cls._instance is None:
                import time

                logger.info("Creating new MCP manager singleton instance")
                cls._instance = MCPManager()
                cls._instance_created_time = time.time()
                logger.info(
                    f"Created MCP manager instance with ID: {id(cls._instance)} at {cls._instance_created_time}"
                )

            return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (for testing)"""
        with cls._lock:
            if cls._instance is not None:
                logger.info("Resetting MCP manager singleton instance")
            cls._instance = None
            cls._instance_created_time = None

    @classmethod
    def get_instance_info(cls) -> Dict[str, Any]:
        """Get information about current instance"""
        with cls._lock:
            if cls._instance is None:
                return {"exists": False}
            return {
                "exists": True,
                "instance_id": id(cls._instance),
                "created_time": cls._instance_created_time,
                "initialized": getattr(cls._instance, "_initialized", False),
                "current_thread": threading.current_thread().ident,
            }


def get_mcp_manager() -> MCPManager:
    """Get the global MCP manager instance with enhanced singleton pattern"""
    return MCPManagerSingleton.get_instance()


def _cleanup_mcp_processes():
    """Cleanup function to be called on exit"""
    if MCP_AVAILABLE:
        try:
            import subprocess

            # Kill any remaining MCP server processes
            subprocess.run(["pkill", "-f", "server-filesystem"], check=False)
            subprocess.run(["pkill", "-f", "server-everything"], check=False)
            try:
                # avoid logger crash
                print("Cleaned up MCP server processes")
            except (ValueError, OSError):
                # 忽略日志文件已关闭的错误
                pass
        except Exception as e:
            try:
                # avoid logger crash
                print(f"Error during MCP cleanup: {e}")
            except (ValueError, OSError):
                # 忽略日志文件已关闭的错误
                pass


# Register cleanup function
atexit.register(_cleanup_mcp_processes)


def _signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    logger.info(f"Received signal {signum}, cleaning up MCP processes...")
    _cleanup_mcp_processes()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
