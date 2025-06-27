"""
MCP Client Implementation

Provides a client for connecting to MCP servers and managing resources, tools, and prompts.
"""

import asyncio
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional, Union

from vertex_flow.utils.logger import LoggerUtil

from .transport import HTTPTransport, MCPTransport, StdioTransport
from .types import (
    MCPCapabilities,
    MCPClientInfo,
    MCPErrorCode,
    MCPMessage,
    MCPMethod,
    MCPNotification,
    MCPPrompt,
    MCPRequest,
    MCPResource,
    MCPResponse,
    MCPServerInfo,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
)

logger = LoggerUtil.get_logger(__name__)


class MCPClient:
    """MCP Client for connecting to MCP servers"""

    def __init__(self, client_info: MCPClientInfo, capabilities: Optional[MCPCapabilities] = None):
        self.client_info = client_info
        self.capabilities = capabilities or MCPCapabilities()
        self.protocol_version = "2024-11-05"  # Add missing protocol version
        self.transport: Optional[MCPTransport] = None
        self.server_info: Optional[MCPServerInfo] = None
        self.server_capabilities: Optional[MCPCapabilities] = None

        # Internal state
        self._initialized = False
        self._running = False
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self._request_id_counter = 0
        self._lock = threading.RLock()  # Use RLock for nested locking
        # Track event loop
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        # Caches
        self._resources: Dict[str, MCPResource] = {}
        self._tools: Dict[str, MCPTool] = {}
        self._prompts: Dict[str, MCPPrompt] = {}

        # Message handlers
        self._message_handlers: Dict[str, Callable] = {}
        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Setup default message handlers"""
        # Handle notifications
        self._message_handlers["resources/updated"] = self._handle_resources_updated
        self._message_handlers["tools/updated"] = self._handle_tools_updated
        self._message_handlers["prompts/updated"] = self._handle_prompts_updated
        self._message_handlers["notifications/message"] = self._handle_notification_message

    def _get_next_request_id(self) -> str:
        """Get next request ID with thread safety - 使用字符串ID避免跨线程冲突"""
        with self._lock:
            self._request_id_counter += 1
            # 使用线程ID和UUID确保跨线程唯一性
            thread_id = threading.get_ident()
            return f"{thread_id}_{self._request_id_counter}_{uuid.uuid4().hex[:8]}"

    async def connect_stdio(self, command: str, *args: str) -> None:
        """Connect to an MCP server via stdio with event loop tracking"""
        transport = StdioTransport()
        await transport.start_server(command, *args)
        self.transport = transport

        # 记录当前事件循环
        self._event_loop = asyncio.get_running_loop()

        # Start message handling loop
        asyncio.create_task(self._message_loop())

        # Initialize the connection
        await self._initialize()

    async def connect_http(self, base_url: str) -> None:
        """Connect to an MCP server via HTTP with event loop tracking"""
        transport = HTTPTransport(base_url)
        await transport.connect()
        self.transport = transport

        # 记录当前事件循环
        self._event_loop = asyncio.get_running_loop()

        # Start message handling loop
        asyncio.create_task(self._message_loop())

        # Initialize the connection
        await self._initialize()

    async def _initialize(self) -> None:
        """Initialize the MCP connection"""
        if not self.transport:
            raise RuntimeError("No transport connected")

        # Send initialize request
        request = MCPRequest(
            method=MCPMethod.INITIALIZE.value,
            id=self._get_next_request_id(),
            params={
                "protocolVersion": self.protocol_version,
                "capabilities": self._capabilities_to_dict(self.capabilities),
                "clientInfo": {"name": self.client_info.name, "version": self.client_info.version},
            },
        )

        response = await self._send_request(request)

        if response.error:
            raise RuntimeError(f"Initialize failed: {response.error}")

        # Parse server info and capabilities
        result = response.result or {}
        self.server_info = MCPServerInfo(
            name=result.get("serverInfo", {}).get("name", "Unknown"),
            version=result.get("serverInfo", {}).get("version", "Unknown"),
        )

        server_caps = result.get("capabilities", {})
        self.server_capabilities = self._dict_to_capabilities(server_caps)

        # Send initialized notification
        notification = MCPNotification(method=MCPMethod.INITIALIZED.value)
        await self._send_notification(notification)

        self._initialized = True
        logger.info(
            f"Connected to MCP server: {
                self.server_info.name} v{
                self.server_info.version}"
        )

    async def _message_loop(self) -> None:
        """Main message handling loop"""
        if not self.transport:
            return

        self._running = True

        try:
            while self._running:
                try:
                    message = await self.transport.receive_message()
                    await self._handle_message(message)
                except EOFError:
                    logger.info("Connection closed by server")
                    break
                except Exception as e:
                    logger.error(f"Error in message loop: {e}")
                    break
        finally:
            self._running = False

    async def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message"""
        try:
            if message.method:
                # Handle request
                handler = self._message_handlers.get(message.method)
                if handler and self.transport:
                    result = await handler(message)
                    response = MCPResponse(id=message.id or 0, result=result)
                    await self.transport.send_message(response)
                else:
                    logger.warning(f"No handler for method: {message.method}")
                    if self.transport:
                        error = MCPResponse(
                            id=message.id or 0,
                            error={
                                "code": -32601,
                                "message": f"Method {
                                    message.method} not found",
                            },
                        )
                        await self.transport.send_message(error)
            elif message.result is not None:
                # Handle response
                if message.id is not None and message.id in self._pending_requests:
                    future = self._pending_requests[message.id]
                    if not future.done():
                        future.set_result(MCPResponse(id=message.id, result=message.result))
                    del self._pending_requests[message.id]
            elif message.error is not None:
                # Handle error response
                if message.id is not None and message.id in self._pending_requests:
                    future = self._pending_requests[message.id]
                    if not future.done():
                        future.set_exception(RuntimeError(f"MCP Error: {message.error}"))
                    del self._pending_requests[message.id]
            elif message.params:
                # Handle notification
                handler = self._message_handlers.get(message.method or "")
                if handler:
                    await handler(message)
                else:
                    logger.debug(
                        f"No handler for notification: {
                            message.method}"
                    )

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _send_request(self, request: MCPRequest, timeout: float = 10.0) -> MCPResponse:
        """Send a request and wait for response with thread safety"""
        if not self.transport:
            raise RuntimeError("No transport connected")

        # Create future for response
        future: asyncio.Future[MCPResponse] = asyncio.Future()

        # Only lock the critical sections, not the entire method
        if request.id is not None:
            with self._lock:
                self._pending_requests[request.id] = future

        try:
            # Send request (transport should be thread-safe)
            await self.transport.send_message(request)

            # Wait for response (don't hold lock while waiting)
            response = await asyncio.wait_for(future, timeout=timeout)
            return response

        except asyncio.TimeoutError:
            # Clean up pending request
            if request.id is not None:
                with self._lock:
                    if request.id in self._pending_requests:
                        del self._pending_requests[request.id]
            logger.warning(
                f"Request {
                    request.id} ({
                    request.method}) timed out after {timeout}s"
            )
            raise RuntimeError(f"Request {request.id} timed out")
        except Exception as e:
            # Clean up pending request
            if request.id is not None:
                with self._lock:
                    if request.id in self._pending_requests:
                        del self._pending_requests[request.id]
            raise

    async def _send_notification(self, notification: MCPNotification) -> None:
        """Send a notification"""
        if not self.transport:
            raise RuntimeError("No transport connected")

        await self.transport.send_message(notification)

    # Resource management
    async def list_resources(self) -> List[MCPResource]:
        """List available resources"""
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        if not self.server_capabilities or not self.server_capabilities.resources:
            return []

        request = MCPRequest(method=MCPMethod.RESOURCES_LIST.value, id=self._get_next_request_id())

        response = await self._send_request(request)

        if response.error:
            raise RuntimeError(f"Failed to list resources: {response.error}")

        resources = []
        result = response.result or {}
        for resource_data in result.get("resources", []):
            resource = MCPResource(
                uri=resource_data["uri"],
                name=resource_data["name"],
                description=resource_data.get("description"),
                mimeType=resource_data.get("mimeType"),
            )
            resources.append(resource)
            self._resources[resource.uri] = resource

        return resources

    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI"""
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        request = MCPRequest(method=MCPMethod.RESOURCES_READ.value, id=self._get_next_request_id(), params={"uri": uri})

        response = await self._send_request(request)

        if response.error:
            raise RuntimeError(
                f"Failed to read resource {uri}: {
                    response.error}"
            )

        result = response.result or {}
        contents = result.get("contents", [])
        if not contents:
            return ""

        # Return the first content item's text
        return contents[0].get("text", "")

    # Tool management
    async def list_tools(self) -> List[MCPTool]:
        """List available tools"""
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        # Always try to get tools - some servers don't properly declare tools capability
        # but still provide tools (like filesystem server)
        request = MCPRequest(method=MCPMethod.TOOLS_LIST.value, id=self._get_next_request_id())

        try:
            # Increased timeout for tools
            response = await self._send_request(request, timeout=15.0)

            if response.error:
                # If server doesn't support tools, return empty list
                if "not supported" in str(response.error).lower() or "not found" in str(response.error).lower():
                    logger.debug(
                        f"Server does not support tools: {
                            response.error}"
                    )
                    return []
                raise RuntimeError(f"Failed to list tools: {response.error}")

            tools = []
            result = response.result or {}
            for tool_data in result.get("tools", []):
                tool = MCPTool(
                    name=tool_data["name"], description=tool_data["description"], inputSchema=tool_data["inputSchema"]
                )
                tools.append(tool)
                self._tools[tool.name] = tool

            logger.info(f"Found {len(tools)} tools from MCP server")
            return tools

        except Exception as e:
            # Log the error but don't fail completely
            logger.warning(f"Failed to list tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool"""
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        request = MCPRequest(
            method=MCPMethod.TOOLS_CALL.value,
            id=self._get_next_request_id(),
            params={"name": name, "arguments": arguments},
        )

        # 增加超时时间到30秒，给工具足够的执行时间
        response = await self._send_request(request, timeout=30.0)

        if response.error:
            raise RuntimeError(f"Failed to call tool {name}: {response.error}")

        result_data = response.result or {}
        return MCPToolResult(content=result_data.get("content", []), isError=result_data.get("isError", False))

    # Prompt management
    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompts"""
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        if not self.server_capabilities or not self.server_capabilities.prompts:
            return []

        request = MCPRequest(method=MCPMethod.PROMPTS_LIST.value, id=self._get_next_request_id())

        response = await self._send_request(request)

        if response.error:
            raise RuntimeError(f"Failed to list prompts: {response.error}")

        prompts = []
        result = response.result or {}
        for prompt_data in result.get("prompts", []):
            prompt = MCPPrompt(
                name=prompt_data["name"],
                description=prompt_data.get("description"),
                arguments=prompt_data.get("arguments", []),
            )
            prompts.append(prompt)
            self._prompts[prompt.name] = prompt

        return prompts

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a prompt by name"""
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        params = {"name": name}
        if arguments:
            params["arguments"] = arguments

        request = MCPRequest(method=MCPMethod.PROMPTS_GET.value, id=self._get_next_request_id(), params=params)

        response = await self._send_request(request)

        if response.error:
            raise RuntimeError(
                f"Failed to get prompt {name}: {
                    response.error}"
            )

        result = response.result or {}
        messages = result.get("messages", [])
        if not messages:
            return ""

        # Combine all message contents
        content_parts = []
        for msg in messages:
            if "content" in msg:
                if isinstance(msg["content"], str):
                    content_parts.append(msg["content"])
                elif isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if isinstance(item, dict) and "text" in item:
                            content_parts.append(item["text"])

        return "\n".join(content_parts)

    # Event handlers
    async def _handle_resources_updated(self, message: MCPMessage) -> None:
        """Handle resource update notifications"""
        logger.debug("Resources updated, clearing cache")
        self._resources.clear()

    async def _handle_tools_updated(self, message: MCPMessage) -> None:
        """Handle tool update notifications"""
        logger.debug("Tools updated, clearing cache")
        self._tools.clear()

    async def _handle_prompts_updated(self, message: MCPMessage) -> None:
        """Handle prompt update notifications"""
        logger.debug("Prompts updated, clearing cache")
        self._prompts.clear()

    async def _handle_notification_message(self, message: MCPMessage) -> None:
        """Handle generic notification messages"""
        logger.debug(f"Received notification: {message.params}")
        return None

    # Utility methods
    def _capabilities_to_dict(self, capabilities: MCPCapabilities) -> Dict[str, Any]:
        """Convert capabilities to dictionary"""
        result = {}

        if capabilities.prompts is not None:
            result["prompts"] = capabilities.prompts
        if capabilities.resources is not None:
            result["resources"] = capabilities.resources
        if capabilities.tools is not None:
            result["tools"] = capabilities.tools
        if capabilities.logging is not None:
            result["logging"] = capabilities.logging
        if capabilities.roots is not None:
            result["roots"] = capabilities.roots
        if capabilities.sampling is not None:
            result["sampling"] = capabilities.sampling
        if capabilities.experimental is not None:
            result["experimental"] = capabilities.experimental

        return result

    def _dict_to_capabilities(self, data: Dict[str, Any]) -> MCPCapabilities:
        """Convert dictionary to capabilities"""
        return MCPCapabilities(
            prompts=data.get("prompts"),
            resources=data.get("resources"),
            tools=data.get("tools"),
            logging=data.get("logging"),
            roots=data.get("roots"),
            sampling=data.get("sampling"),
            experimental=data.get("experimental"),
        )

    async def ping(self) -> bool:
        """Ping the server"""
        if not self._initialized:
            return False

        try:
            request = MCPRequest(method=MCPMethod.PING.value, id=self._get_next_request_id())

            response = await self._send_request(request, timeout=5.0)
            return response.error is None

        except Exception:
            return False

    async def close(self) -> None:
        """Close the client connection"""
        self._running = False

        # Cancel all pending requests
        for future in self._pending_requests.values():
            if not future.cancelled():
                future.cancel()
        self._pending_requests.clear()

        # Close transport
        if self.transport:
            await self.transport.close()

        logger.info("MCP client closed")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected and initialized"""
        return self._initialized and self._running
