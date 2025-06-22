"""
MCP (Model Context Protocol) Example for Vertex Flow

This example demonstrates how to use MCP with Vertex Flow to:
1. Create an MCP server that exposes resources, tools, and prompts
2. Create an MCP client that connects to servers
3. Integrate MCP with Vertex Flow workflows
"""

import asyncio
from typing import Any, Dict, List

from vertex_flow.mcp import (
    HTTPTransport,
    MCPCapabilities,
    MCPClient,
    MCPClientInfo,
    MCPPrompt,
    MCPResource,
    MCPServer,
    MCPServerInfo,
    MCPTool,
    MCPToolResult,
    StdioTransport,
)
from vertex_flow.mcp.server import MCPPromptProvider, MCPResourceProvider, MCPToolProvider
from vertex_flow.mcp.vertex_integration import (
    MCPVertexFlowClient,
    MCPVertexFlowServer,
    VertexFlowMCPPromptProvider,
    VertexFlowMCPResourceProvider,
    VertexFlowMCPToolProvider,
)
from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.tools.functions import FunctionTool

logger = LoggerUtil.get_logger(__name__)


class ExampleResourceProvider(MCPResourceProvider):
    """Example resource provider"""

    def __init__(self):
        self.resources = {
            "file://example.txt": "This is example content from a file resource.",
            "file://data.json": '{"key": "value", "number": 42}',
            "file://config.yaml": "setting1: value1\nsetting2: value2\n",
        }

    async def list_resources(self) -> List[MCPResource]:
        """List available resources"""
        resources = []
        for uri, content in self.resources.items():
            filename = uri.split("/")[-1]
            resource = MCPResource(
                uri=uri, name=filename, description=f"Example resource: {filename}", mimeType="text/plain"
            )
            resources.append(resource)
        return resources

    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI"""
        if uri not in self.resources:
            raise ValueError(f"Resource not found: {uri}")
        return self.resources[uri]


class ExampleToolProvider(MCPToolProvider):
    """Example tool provider"""

    async def list_tools(self) -> List[MCPTool]:
        """List available tools"""
        return [
            MCPTool(
                name="calculate",
                description="Perform basic arithmetic calculations",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                    },
                    "required": ["expression"],
                },
            ),
            MCPTool(
                name="reverse_text",
                description="Reverse the given text",
                inputSchema={
                    "type": "object",
                    "properties": {"text": {"type": "string", "description": "Text to reverse"}},
                    "required": ["text"],
                },
            ),
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool"""
        try:
            if name == "calculate":
                expression = arguments.get("expression", "")
                # Simple evaluation (in production, use a safer evaluator)
                result = eval(expression)
                return MCPToolResult(content=[{"type": "text", "text": f"Result: {result}"}], isError=False)

            elif name == "reverse_text":
                text = arguments.get("text", "")
                reversed_text = text[::-1]
                return MCPToolResult(content=[{"type": "text", "text": reversed_text}], isError=False)

            else:
                return MCPToolResult(content=[{"type": "text", "text": f"Unknown tool: {name}"}], isError=True)

        except Exception as e:
            return MCPToolResult(content=[{"type": "text", "text": f"Error: {str(e)}"}], isError=True)


class ExamplePromptProvider(MCPPromptProvider):
    """Example prompt provider"""

    def __init__(self):
        self.prompts = {
            "summarize": {
                "template": "Please summarize the following text in {max_words} words or less:\n\n{text}",
                "description": "Summarize text with a word limit",
                "arguments": [
                    {"name": "text", "description": "Text to summarize", "required": True},
                    {"name": "max_words", "description": "Maximum number of words", "required": False},
                ],
            },
            "translate": {
                "template": "Translate the following text from {source_lang} to {target_lang}:\n\n{text}",
                "description": "Translate text between languages",
                "arguments": [
                    {"name": "text", "description": "Text to translate", "required": True},
                    {"name": "source_lang", "description": "Source language", "required": True},
                    {"name": "target_lang", "description": "Target language", "required": True},
                ],
            },
        }

    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompts"""
        prompts = []
        for name, data in self.prompts.items():
            prompt = MCPPrompt(name=name, description=data["description"], arguments=data["arguments"])
            prompts.append(prompt)
        return prompts

    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> str:
        """Get a prompt by name"""
        if name not in self.prompts:
            raise ValueError(f"Prompt not found: {name}")

        template = self.prompts[name]["template"]

        # Simple template substitution
        if arguments:
            for key, value in arguments.items():
                template = template.replace(f"{{{key}}}", str(value))

        return template


async def run_mcp_server_example():
    """Run an MCP server example"""
    logger.info("Starting MCP Server Example")

    # Create server
    server_info = MCPServerInfo(name="ExampleServer", version="1.0.0")
    capabilities = MCPCapabilities(
        resources={"subscribe": True, "listChanged": True},
        tools={"listChanged": True},
        prompts={"listChanged": True},
        logging={},
    )

    server = MCPServer(server_info, capabilities)

    # Set providers
    server.set_resource_provider(ExampleResourceProvider())
    server.set_tool_provider(ExampleToolProvider())
    server.set_prompt_provider(ExamplePromptProvider())

    # Run server (this will block)
    logger.info("MCP server running on stdio...")
    await server.run_stdio()


async def run_mcp_client_example():
    """Run an MCP client example"""
    logger.info("Starting MCP Client Example")

    # Create client
    client_info = MCPClientInfo(name="ExampleClient", version="1.0.0")
    client = MCPClient(client_info)

    try:
        # Connect to server (replace with actual server command)
        # await client.connect_stdio("python", "mcp_server.py")

        # For this example, we'll simulate the connection
        logger.info("Connecting to MCP server...")

        # List resources
        resources = await client.list_resources()
        logger.info(f"Available resources: {[r.name for r in resources]}")

        # Read a resource
        if resources:
            content = await client.read_resource(resources[0].uri)
            logger.info(f"Resource content: {content}")

        # List tools
        tools = await client.list_tools()
        logger.info(f"Available tools: {[t.name for t in tools]}")

        # Call a tool
        if tools:
            result = await client.call_tool("calculate", {"expression": "2 + 3 * 4"})
            logger.info(f"Tool result: {result.content}")

        # List prompts
        prompts = await client.list_prompts()
        logger.info(f"Available prompts: {[p.name for p in prompts]}")

        # Get a prompt
        if prompts:
            prompt_text = await client.get_prompt(
                "summarize", {"text": "This is a long text that needs to be summarized.", "max_words": "10"}
            )
            logger.info(f"Prompt: {prompt_text}")

    finally:
        await client.close()


async def run_vertex_flow_mcp_integration():
    """Run Vertex Flow MCP integration example"""
    logger.info("Starting Vertex Flow MCP Integration Example")

    # Create Vertex Flow MCP Server
    vf_server = MCPVertexFlowServer("VertexFlowServer", "1.0.0")

    # Add resources
    vf_server.add_resource(
        "workflow://config", "workflow_config", "workflow_name: example\nsteps: [step1, step2, step3]"
    )

    # Add function tools
    def example_function(text: str, count: int = 1) -> str:
        """Example function that repeats text"""
        return (text + " ") * count

    function_tool = FunctionTool(
        name="repeat_text", description="Repeat text multiple times", function=example_function
    )
    vf_server.add_function_tool(function_tool)

    # Add prompts
    vf_server.add_prompt(
        "code_review",
        "Please review the following code and provide feedback:\n\n{code}\n\nFocus on: {focus_areas}",
        "Code review prompt",
        [
            {"name": "code", "description": "Code to review", "required": True},
            {"name": "focus_areas", "description": "Areas to focus on", "required": False},
        ],
    )

    logger.info("Vertex Flow MCP Server configured")

    # Create client
    vf_client = MCPVertexFlowClient("VertexFlowClient", "1.0.0")

    # In a real scenario, you would connect to the server
    # await vf_client.connect_stdio("python", "vertex_flow_mcp_server.py")

    logger.info("Vertex Flow MCP integration example completed")


async def main():
    """Main function to run examples"""
    print("MCP (Model Context Protocol) Examples for Vertex Flow")
    print("=" * 50)

    print("\n1. Basic MCP Server/Client Example")
    print("2. Vertex Flow MCP Integration Example")

    choice = input("\nSelect example to run (1 or 2): ").strip()

    if choice == "1":
        server_or_client = input("Run as (s)erver or (c)lient? ").strip().lower()
        if server_or_client == "s":
            await run_mcp_server_example()
        elif server_or_client == "c":
            await run_mcp_client_example()
        else:
            print("Invalid choice")
    elif choice == "2":
        await run_vertex_flow_mcp_integration()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
