"""
MCP Integration with Vertex Flow

Provides integration between MCP (Model Context Protocol) and Vertex Flow workflow system.
This allows Vertex Flow to act as both MCP client and server.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union

from vertex_flow.utils.logger import LoggerUtil

from ..workflow.tools.functions import FunctionTool
from ..workflow.vertex.function_vertex import FunctionVertex
from ..workflow.vertex.llm_vertex import LLMVertex
from .client import MCPClient
from .server import MCPPromptProvider, MCPResourceProvider, MCPServer, MCPToolProvider
from .types import MCPCapabilities, MCPClientInfo, MCPPrompt, MCPResource, MCPServerInfo, MCPTool, MCPToolResult

logger = LoggerUtil.get_logger()


class VertexFlowMCPResourceProvider(MCPResourceProvider):
    """MCP Resource Provider for Vertex Flow"""

    def __init__(self):
        self.resources: Dict[str, str] = {}

    def add_resource(
        self, uri: str, name: str, content: str, description: Optional[str] = None, mime_type: str = "text/plain"
    ):
        """Add a resource"""
        self.resources[uri] = content

    async def list_resources(self) -> List[MCPResource]:
        """List available resources"""
        resources = []
        for uri, content in self.resources.items():
            resource = MCPResource(
                uri=uri,
                name=uri.split("/")[-1],  # Use filename as name
                description=f"Resource: {uri}",
                mimeType="text/plain",
            )
            resources.append(resource)
        return resources

    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI"""
        if uri not in self.resources:
            raise ValueError(f"Resource not found: {uri}")
        return self.resources[uri]


class VertexFlowMCPToolProvider(MCPToolProvider):
    """MCP Tool Provider for Vertex Flow"""

    def __init__(self, use_tool_manager: bool = True):
        self.function_tools: Dict[str, FunctionTool] = {}
        self.use_tool_manager = use_tool_manager
        self._tool_manager = None

        # Initialize tool manager if requested
        if self.use_tool_manager:
            try:
                from vertex_flow.workflow.tools.tool_manager import get_function_tool_manager

                self._tool_manager = get_function_tool_manager()
                logger.info("VertexFlowMCPToolProvider initialized with tool manager")
            except ImportError:
                logger.warning("Tool manager not available, using local tool storage")
                self.use_tool_manager = False

    def add_function_tool(self, tool: FunctionTool):
        """Add a function tool"""
        self.function_tools[tool.name] = tool

        # Also register with tool manager if available
        if self._tool_manager:
            self._tool_manager.register_tool(tool)

    def set_service(self, service):
        """Set the VertexFlowService instance and auto-register tools"""
        if self._tool_manager:
            self._tool_manager.set_service(service)
            self._tool_manager.auto_register_builtin_tools()
            self._tool_manager.register_custom_tools()
            logger.info("Auto-registered built-in and custom tools from service")

    async def list_tools(self) -> List[MCPTool]:
        """List available tools"""
        tools = []

        # Get tools from tool manager if available
        if self._tool_manager:
            for tool in self._tool_manager.list_tools():
                mcp_tool = MCPTool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=tool.schema.get("properties", {}) if tool.schema else {},
                )
                tools.append(mcp_tool)

        # Also include locally added tools
        for name, tool in self.function_tools.items():
            # Skip if already included from tool manager
            if self._tool_manager and self._tool_manager.get_tool(name):
                continue

            mcp_tool = MCPTool(
                name=name,
                description=tool.description,
                inputSchema=tool.schema.get("properties", {}) if tool.schema else {},
            )
            tools.append(mcp_tool)

        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool"""
        tool = None

        # Try to get tool from tool manager first
        if self._tool_manager:
            tool = self._tool_manager.get_tool(name)

        # Fall back to local tools
        if not tool:
            tool = self.function_tools.get(name)

        if not tool:
            return MCPToolResult(content=[{"type": "text", "text": f"Tool not found: {name}"}], isError=True)

        try:
            # Execute tool
            if self._tool_manager and self._tool_manager.get_tool(name):
                result = self._tool_manager.execute_tool(name, arguments)
            else:
                result = tool.execute(arguments)

            # Convert result to MCP format
            if isinstance(result, str):
                content = [{"type": "text", "text": result}]
            elif isinstance(result, dict):
                content = [{"type": "text", "text": str(result)}]
            else:
                content = [{"type": "text", "text": str(result)}]

            return MCPToolResult(content=content, isError=False)

        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return MCPToolResult(content=[{"type": "text", "text": f"Error: {str(e)}"}], isError=True)

    def get_available_tool_names(self) -> List[str]:
        """Get names of all available tools"""
        names = set()

        if self._tool_manager:
            names.update(self._tool_manager.get_tool_names())

        names.update(self.function_tools.keys())

        return list(names)


class VertexFlowMCPPromptProvider(MCPPromptProvider):
    """MCP Prompt Provider for Vertex Flow"""

    def __init__(self):
        self.prompts: Dict[str, Dict[str, Any]] = {}

    def add_prompt(
        self,
        name: str,
        template: str,
        description: Optional[str] = None,
        arguments: Optional[List[Dict[str, Any]]] = None,
    ):
        """Add a prompt template"""
        self.prompts[name] = {
            "template": template,
            "description": description or f"Prompt: {name}",
            "arguments": arguments or [],
        }

    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompts"""
        prompts = []
        for name, data in self.prompts.items():
            prompt = MCPPrompt(name=name, description=data["description"], arguments=data["arguments"])
            prompts.append(prompt)
        return prompts

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a prompt by name"""
        if name not in self.prompts:
            raise ValueError(f"Prompt not found: {name}")

        template = self.prompts[name]["template"]

        # Simple template substitution
        if arguments:
            for key, value in arguments.items():
                template = template.replace(f"{{{key}}}", str(value))

        return template


class MCPVertexFlowServer:
    """MCP Server for Vertex Flow"""

    def __init__(self, name: str = "VertexFlow", version: str = "1.0.0"):
        self.server_info = MCPServerInfo(name=name, version=version)
        self.capabilities = MCPCapabilities(
            resources={"subscribe": True, "listChanged": True},
            tools={"listChanged": True},
            prompts={"listChanged": True},
            logging={},
        )

        self.server = MCPServer(self.server_info, self.capabilities)

        # Providers
        self.resource_provider = VertexFlowMCPResourceProvider()
        self.tool_provider = VertexFlowMCPToolProvider(use_tool_manager=True)
        self.prompt_provider = VertexFlowMCPPromptProvider()

        # Set providers
        self.server.set_resource_provider(self.resource_provider)
        self.server.set_tool_provider(self.tool_provider)
        self.server.set_prompt_provider(self.prompt_provider)

    def add_resource(
        self, uri: str, name: str, content: str, description: Optional[str] = None, mime_type: str = "text/plain"
    ):
        """Add a resource to the server"""
        self.resource_provider.add_resource(uri, name, content, description, mime_type)

    def add_function_tool(self, tool: FunctionTool):
        """Add a function tool to the server"""
        self.tool_provider.add_function_tool(tool)

    def add_prompt(
        self,
        name: str,
        template: str,
        description: Optional[str] = None,
        arguments: Optional[List[Dict[str, Any]]] = None,
    ):
        """Add a prompt template to the server"""
        self.prompt_provider.add_prompt(name, template, description, arguments)

    def set_service(self, service):
        """Set the VertexFlowService instance for auto-registering tools"""
        self.tool_provider.set_service(service)

    async def run_stdio(self):
        """Run server using stdio"""
        await self.server.run_stdio()

    async def run_http(self, host: str = "localhost", port: int = 8080):
        """Run server using HTTP"""
        await self.server.run_http(host, port)

    async def close(self):
        """Close the server"""
        await self.server.close()


class MCPVertexFlowClient:
    """MCP Client for Vertex Flow"""

    def __init__(self, name: str = "VertexFlow-Client", version: str = "1.0.0"):
        self.client_info = MCPClientInfo(name=name, version=version)
        self.capabilities = MCPCapabilities(roots={"listChanged": True}, sampling={})

        self.client = MCPClient(self.client_info, self.capabilities)

    async def connect_stdio(self, command: str, *args: str):
        """Connect to MCP server via stdio"""
        await self.client.connect_stdio(command, *args)

    async def connect_http(self, base_url: str):
        """Connect to MCP server via HTTP"""
        await self.client.connect_http(base_url)

    async def get_resources(self) -> List[MCPResource]:
        """Get available resources"""
        return await self.client.list_resources()

    async def list_resources(self) -> List[MCPResource]:
        """Get available resources (alias for compatibility)"""
        return await self.get_resources()

    async def read_resource(self, uri: str) -> str:
        """Read a resource"""
        return await self.client.read_resource(uri)

    async def get_tools(self) -> List[MCPTool]:
        """Get available tools"""
        return await self.client.list_tools()

    async def list_tools(self) -> List[MCPTool]:
        """Get available tools (alias for compatibility)"""
        return await self.get_tools()

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool"""
        return await self.client.call_tool(name, arguments)

    async def get_prompts(self) -> List[MCPPrompt]:
        """Get available prompts"""
        return await self.client.list_prompts()

    async def list_prompts(self) -> List[MCPPrompt]:
        """Get available prompts (alias for compatibility)"""
        return await self.get_prompts()

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a prompt"""
        return await self.client.get_prompt(name, arguments)

    async def close(self):
        """Close the client"""
        await self.client.close()

    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.client.is_connected


class MCPLLMVertex(LLMVertex):
    """LLM Vertex with MCP integration"""

    def __init__(self, vertex_id: str, **kwargs):
        super().__init__(vertex_id, **kwargs)
        self.mcp_clients: Dict[str, MCPVertexFlowClient] = {}

    async def add_mcp_client(self, name: str, client: MCPVertexFlowClient):
        """Add an MCP client"""
        self.mcp_clients[name] = client

    async def _get_mcp_context(self) -> str:
        """Get context from all MCP clients"""
        context_parts = []

        for name, client in self.mcp_clients.items():
            if not client.is_connected:
                continue

            try:
                # Get resources
                resources = await client.get_resources()
                for resource in resources:
                    content = await client.read_resource(resource.uri)
                    context_parts.append(
                        f"Resource {
                            resource.name}:\n{content}\n"
                    )

                # Get prompts as context
                prompts = await client.get_prompts()
                for prompt in prompts:
                    prompt_content = await client.get_prompt(prompt.name)
                    context_parts.append(
                        f"Prompt {
                            prompt.name}:\n{prompt_content}\n"
                    )

            except Exception as e:
                logger.error(f"Error getting MCP context from {name}: {e}")

        return "\n".join(context_parts)

    async def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get tools from all MCP clients"""
        tools = []

        for name, client in self.mcp_clients.items():
            if not client.is_connected:
                continue

            try:
                mcp_tools = await client.get_tools()
                for tool in mcp_tools:
                    # Convert MCP tool to OpenAI tool format
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": f"mcp_{name}_{tool.name}",
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    }
                    tools.append(openai_tool)

            except Exception as e:
                logger.error(f"Error getting MCP tools from {name}: {e}")

        return tools

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call an MCP tool"""
        # Parse tool name to get client and original tool name
        if not tool_name.startswith("mcp_"):
            raise ValueError(f"Not an MCP tool: {tool_name}")

        parts = tool_name[4:].split("_", 1)  # Remove "mcp_" prefix
        if len(parts) != 2:
            raise ValueError(f"Invalid MCP tool name format: {tool_name}")

        client_name, original_tool_name = parts

        if client_name not in self.mcp_clients:
            raise ValueError(f"MCP client not found: {client_name}")

        client = self.mcp_clients[client_name]
        if not client.is_connected:
            raise RuntimeError(f"MCP client {client_name} not connected")

        result = await client.call_tool(original_tool_name, arguments)

        if result.isError:
            raise RuntimeError(f"MCP tool error: {result.content}")

        # Extract text content
        text_parts = []
        for content_item in result.content:
            if content_item.get("type") == "text":
                text_parts.append(content_item.get("text", ""))

        return "\n".join(text_parts)

    async def _process_with_mcp(self, inputs: Dict[str, Any], context: Dict[str, Any]):
        """Process with MCP integration"""
        # Add MCP context to the input
        mcp_context = await self._get_mcp_context()
        if mcp_context:
            current_input = inputs.get("input", "")
            inputs["input"] = f"{current_input}\n\nMCP Context:\n{mcp_context}"

        # Add MCP tools
        mcp_tools = await self._get_mcp_tools()
        if mcp_tools:
            # Merge with existing tools
            existing_tools = context.get("tools", [])
            context["tools"] = existing_tools + mcp_tools

            # Process normally using parent class method
        return self.chat(inputs, context)

    def process(self, inputs: Dict[str, Any], context: Dict[str, Any]):
        """Process with MCP integration"""
        try:
            # Run async processing in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._process_with_mcp(inputs, context))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in MCP processing: {e}")
            # Fallback to normal processing
            return self.chat(inputs, context)
