"""
MCP Server Implementation

Provides a server for exposing resources, tools, and prompts via the Model Context Protocol.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from vertex_flow.utils.logger import LoggerUtil

from .transport import HTTPServer, MCPTransport, StdioTransport
from .types import (
    MCPCapabilities,
    MCPClientInfo,
    MCPError,
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


class MCPResourceProvider(ABC):
    """Abstract base class for resource providers"""

    @abstractmethod
    async def list_resources(self) -> List[MCPResource]:
        """List available resources"""
        pass

    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI"""
        pass


class MCPToolProvider(ABC):
    """Abstract base class for tool providers"""

    @abstractmethod
    async def list_tools(self) -> List[MCPTool]:
        """List available tools"""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool"""
        pass


class MCPPromptProvider(ABC):
    """Abstract base class for prompt providers"""

    @abstractmethod
    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompts"""
        pass

    @abstractmethod
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a prompt by name"""
        pass


class MCPServer:
    """MCP Server for exposing resources, tools, and prompts"""

    def __init__(self, server_info: MCPServerInfo, capabilities: Optional[MCPCapabilities] = None):
        self.server_info = server_info
        self.capabilities = capabilities or MCPCapabilities(
            resources={"subscribe": True, "listChanged": True},
            tools={"listChanged": True},
            prompts={"listChanged": True},
            logging={},
        )

        self.transport: Optional[MCPTransport] = None
        self.client_info: Optional[MCPClientInfo] = None
        self.client_capabilities: Optional[MCPCapabilities] = None
        self.protocol_version = "2024-11-05"

        # State management
        self._initialized = False
        self._running = False

        # Providers
        self.resource_provider: Optional[MCPResourceProvider] = None
        self.tool_provider: Optional[MCPToolProvider] = None
        self.prompt_provider: Optional[MCPPromptProvider] = None

        # Message handlers
        self._request_handlers: Dict[str, Callable] = {}
        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Setup default request handlers"""
        self._request_handlers[MCPMethod.INITIALIZE.value] = self._handle_initialize
        self._request_handlers[MCPMethod.RESOURCES_LIST.value] = self._handle_resources_list
        self._request_handlers[MCPMethod.RESOURCES_READ.value] = self._handle_resources_read
        self._request_handlers[MCPMethod.TOOLS_LIST.value] = self._handle_tools_list
        self._request_handlers[MCPMethod.TOOLS_CALL.value] = self._handle_tools_call
        self._request_handlers[MCPMethod.PROMPTS_LIST.value] = self._handle_prompts_list
        self._request_handlers[MCPMethod.PROMPTS_GET.value] = self._handle_prompts_get
        self._request_handlers[MCPMethod.PING.value] = self._handle_ping

    def set_resource_provider(self, provider: MCPResourceProvider) -> None:
        """Set the resource provider"""
        self.resource_provider = provider

    def set_tool_provider(self, provider: MCPToolProvider) -> None:
        """Set the tool provider"""
        self.tool_provider = provider

    def set_prompt_provider(self, provider: MCPPromptProvider) -> None:
        """Set the prompt provider"""
        self.prompt_provider = provider

    async def run_stdio(self) -> None:
        """Run server using stdio transport"""
        transport = StdioTransport()
        await transport.connect_to_stdio()
        self.transport = transport

        # Start message handling loop
        await self._message_loop()

    async def run_http(self, host: str = "localhost", port: int = 8080) -> None:
        """Run server using HTTP transport"""
        http_server = HTTPServer(host, port)
        http_server.set_message_handler(self._handle_http_message)

        await http_server.start()
        logger.info(f"MCP HTTP server running on {host}:{port}")

        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down HTTP server")
        finally:
            await http_server.stop()

    def _handle_http_message(self, message: MCPMessage) -> MCPMessage:
        """Handle HTTP messages synchronously"""
        # Convert to async and run in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._handle_message(message))
        finally:
            loop.close()

    async def _message_loop(self) -> None:
        """Main message handling loop"""
        if not self.transport:
            return

        self._running = True

        try:
            while self._running:
                try:
                    message = await self.transport.receive_message()
                    response = await self._handle_message(message)
                    if response:
                        await self.transport.send_message(response)
                except EOFError:
                    logger.info("Client disconnected")
                    break
                except Exception as e:
                    logger.error(f"Error in message loop: {e}")
                    break
        finally:
            self._running = False

    async def _handle_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Handle incoming messages"""
        try:
            if message.method:
                # This is a request or notification
                if message.id is not None:
                    # Request - needs response
                    if message.method in self._request_handlers:
                        handler = self._request_handlers[message.method]
                        try:
                            result = await handler(message)
                            return MCPResponse(id=message.id, result=result)
                        except Exception as e:
                            logger.error(
                                f"Error handling {message.method}: {e}"
                            )
                            return MCPResponse(
                                id=message.id, error={"code": MCPErrorCode.INTERNAL_ERROR, "message": str(e)}
                            )
                    else:
                        # Method not found
                        return MCPResponse(
                            id=message.id,
                            error={
                                "code": MCPErrorCode.METHOD_NOT_FOUND,
                                "message": f"Method {message.method} not found",
                            },
                        )
                else:
                    # Notification - no response needed
                    if message.method == MCPMethod.INITIALIZED.value:
                        self._initialized = True
                        logger.info("Client initialized")

            return None

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            if message.id is not None:
                return MCPResponse(id=message.id, error={"code": MCPErrorCode.INTERNAL_ERROR, "message": str(e)})
            return None

    # Request handlers
    async def _handle_initialize(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle initialize request"""
        params = message.params or {}

        # Parse client info
        client_info_data = params.get("clientInfo", {})
        self.client_info = MCPClientInfo(
            name=client_info_data.get("name", "Unknown"), version=client_info_data.get("version", "Unknown")
        )

        # Parse client capabilities
        client_caps = params.get("capabilities", {})
        self.client_capabilities = self._dict_to_capabilities(client_caps)

        # Return server info and capabilities
        return {
            "protocolVersion": self.protocol_version,
            "serverInfo": {"name": self.server_info.name, "version": self.server_info.version},
            "capabilities": self._capabilities_to_dict(self.capabilities),
        }

    async def _handle_resources_list(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle resources/list request"""
        if not self.resource_provider:
            return {"resources": []}

        resources = await self.resource_provider.list_resources()
        return {
            "resources": [
                {"uri": r.uri, "name": r.name, "description": r.description, "mimeType": r.mimeType} for r in resources
            ]
        }

    async def _handle_resources_read(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle resources/read request"""
        if not self.resource_provider:
            raise RuntimeError("No resource provider configured")

        params = message.params or {}
        uri = params.get("uri")
        if not uri:
            raise ValueError("URI parameter required")

        content = await self.resource_provider.read_resource(uri)
        return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": content}]}

    async def _handle_tools_list(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle tools/list request"""
        if not self.tool_provider:
            return {"tools": []}

        tools = await self.tool_provider.list_tools()
        return {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tools]}

    async def _handle_tools_call(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle tools/call request"""
        if not self.tool_provider:
            raise RuntimeError("No tool provider configured")

        params = message.params or {}
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("Tool name parameter required")

        result = await self.tool_provider.call_tool(name, arguments)
        return {"content": result.content, "isError": result.isError}

    async def _handle_prompts_list(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle prompts/list request"""
        if not self.prompt_provider:
            return {"prompts": []}

        prompts = await self.prompt_provider.list_prompts()
        return {
            "prompts": [{"name": p.name, "description": p.description, "arguments": p.arguments or []} for p in prompts]
        }

    async def _handle_prompts_get(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle prompts/get request"""
        if not self.prompt_provider:
            raise RuntimeError("No prompt provider configured")

        params = message.params or {}
        name = params.get("name")
        arguments = params.get("arguments")

        if not name:
            raise ValueError("Prompt name parameter required")

        content = await self.prompt_provider.get_prompt(name, arguments)
        return {"messages": [{"role": "user", "content": {"type": "text", "text": content}}]}

    async def _handle_ping(self, message: MCPMessage) -> Dict[str, Any]:
        """Handle ping request"""
        return {}

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

    async def notify_resources_updated(self) -> None:
        """Notify clients that resources have been updated"""
        if not self.transport or not self._initialized:
            return

        notification = MCPNotification(method="resources/updated")
        await self.transport.send_message(notification)

    async def notify_tools_updated(self) -> None:
        """Notify clients that tools have been updated"""
        if not self.transport or not self._initialized:
            return

        notification = MCPNotification(method="tools/updated")
        await self.transport.send_message(notification)

    async def notify_prompts_updated(self) -> None:
        """Notify clients that prompts have been updated"""
        if not self.transport or not self._initialized:
            return

        notification = MCPNotification(method="prompts/updated")
        await self.transport.send_message(notification)

    async def close(self) -> None:
        """Close the server"""
        self._running = False

        if self.transport:
            await self.transport.close()

        logger.info("MCP server closed")

    @property
    def is_running(self) -> bool:
        """Check if server is running"""
        return self._running and self._initialized
