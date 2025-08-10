# MCP (Model Context Protocol) Integration

## Overview

Vertex Flow now supports the Model Context Protocol (MCP), an open protocol that enables seamless integration between LLM applications and external data sources and tools. MCP provides a standardized way to connect LLMs with the context they need.

## What is MCP?

The Model Context Protocol (MCP) is an open standard that allows AI applications to securely connect to external data sources and tools. It provides:

- **Resources**: Context and data for AI models to use
- **Tools**: Functions for AI models to execute
- **Prompts**: Templated messages and workflows for users
- **Sampling**: Server-initiated agentic behaviors

## Architecture

MCP uses a client-server architecture where:

- **Hosts**: LLM applications (like Vertex Flow) that initiate connections
- **Clients**: Connectors within the host application
- **Servers**: Services that provide context and capabilities

Vertex Flow can act as both an MCP client (consuming external MCP servers) and an MCP server (exposing its own capabilities).

## Configuration

### Basic Configuration

Create or modify `vertex_flow/config/mcp.yml`:

```yaml
mcp:
  enabled: true
  
  clients:
    filesystem:
      enabled: true
      transport: "stdio"
      command: "npx"
      args: ["@modelcontextprotocol/server-filesystem", "/path/to/data"]
  
  server:
    enabled: true
    name: "VertexFlow"
    version: "1.0.0"
```

### Client Configuration

Configure MCP clients to connect to external servers:

```yaml
clients:
  # Filesystem access
  filesystem:
    enabled: true
    transport: "stdio"
    command: "npx"
    args: ["@modelcontextprotocol/server-filesystem", "/data"]
    description: "Access filesystem resources"
  
  # GitHub integration
  github:
    enabled: true
    transport: "stdio"
    command: "npx"
    args: ["@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "your-token"
    description: "Access GitHub repositories"
  
  # Database access
  database:
    enabled: true
    transport: "stdio"
    command: "python"
    args: ["-m", "mcp_server_database", "--connection-string", "sqlite:///data.db"]
    description: "Database operations"
```

### Server Configuration

Configure Vertex Flow as an MCP server:

```yaml
server:
  enabled: true
  name: "VertexFlow"
  version: "1.0.0"
  
  transport:
    stdio:
      enabled: true
    http:
      enabled: false
      host: "localhost"
      port: 8080
  
  resources:
    enabled: true
    workflows:
      enabled: true
      path: "vertex_flow/workflow"
      pattern: "*.py"
  
  tools:
    enabled: true
    function_tools:
      enabled: true
      auto_discover: true
  
  prompts:
    enabled: true
    custom_prompts:
      - name: "code_review"
        template: "Review this code: {code}"
        description: "Code review prompt"
```

## Usage Examples

### Using MCP Clients

```python
from vertex_flow.mcp.vertex_integration import MCPVertexFlowClient

# Create and connect client
client = MCPVertexFlowClient("MyClient", "1.0.0")
await client.connect_stdio("npx", "@modelcontextprotocol/server-filesystem", "/data")

# List available resources
resources = await client.get_resources()
print(f"Available resources: {[r.name for r in resources]}")

# Read a resource
content = await client.read_resource("file:///data/example.txt")
print(f"Content: {content}")

# List available tools
tools = await client.get_tools()
print(f"Available tools: {[t.name for t in tools]}")

# Call a tool
result = await client.call_tool("search_files", {"pattern": "*.py"})
print(f"Search result: {result.content}")
```

### Running MCP Server

```python
from vertex_flow.mcp.vertex_integration import MCPVertexFlowServer
from vertex_flow.workflow.tools.functions import FunctionTool

# Create server
server = MCPVertexFlowServer("VertexFlow", "1.0.0")

# Add resources
server.add_resource(
    "workflow://config",
    "workflow_config", 
    "workflow configuration content"
)

# Add tools
def my_function(text: str) -> str:
    return f"Processed: {text}"

tool = FunctionTool(
    name="process_text",
    description="Process text input",
    func=my_function
)
server.add_function_tool(tool)

# Add prompts
server.add_prompt(
    "summarize",
    "Summarize this text: {text}",
    "Text summarization prompt"
)

# Run server
await server.run_stdio()
```

### LLM Vertex with MCP Integration

```python
from vertex_flow.mcp.vertex_integration import MCPLLMVertex, MCPVertexFlowClient

# Create MCP-enabled LLM vertex
llm_vertex = MCPLLMVertex("llm_with_mcp", model=my_model)

# Add MCP clients
filesystem_client = MCPVertexFlowClient("filesystem", "1.0.0")
await filesystem_client.connect_stdio("npx", "@modelcontextprotocol/server-filesystem", "/data")
await llm_vertex.add_mcp_client("filesystem", filesystem_client)

# Process with MCP context
result = llm_vertex.process(
    {"input": "Analyze the data files"},
    {"workflow_context": context}
)
```

## Transport Mechanisms

### Standard Input/Output (stdio)

The most common transport mechanism where the MCP server runs as a child process:

```yaml
transport: "stdio"
command: "npx"
args: ["@modelcontextprotocol/server-filesystem", "/data"]
```

### HTTP Transport

For servers that support HTTP connections:

```yaml
transport: "http"
base_url: "http://localhost:8080"
```

## Available MCP Servers

### Official MCP Servers

- **Filesystem**: `@modelcontextprotocol/server-filesystem`
- **GitHub**: `@modelcontextprotocol/server-github`
- **GitLab**: `@modelcontextprotocol/server-gitlab`
- **Google Drive**: `@modelcontextprotocol/server-gdrive`
- **Slack**: `@modelcontextprotocol/server-slack`
- **PostgreSQL**: `@modelcontextprotocol/server-postgres`
- **SQLite**: `@modelcontextprotocol/server-sqlite`

### Third-Party Servers

- **Puppeteer**: Web automation and scraping
- **Brave Search**: Web search capabilities
- **AWS**: AWS services integration
- **Docker**: Container management

### Installation

Install MCP servers using npm:

```bash
# Install filesystem server
npm install -g @modelcontextprotocol/server-filesystem

# Install GitHub server
npm install -g @modelcontextprotocol/server-github

# Install database servers
npm install -g @modelcontextprotocol/server-postgres
npm install -g @modelcontextprotocol/server-sqlite
```

## Security Considerations

### Resource Access Control

Configure allowed and blocked resource patterns:

```yaml
security:
  allowed_resources:
    - "file://*"
    - "workflow://*"
    - "config://*"
  
  blocked_resources:
    - "file:///etc/*"
    - "file:///root/*"
```

### Tool Execution Limits

Set limits on tool execution:

```yaml
tool_limits:
  max_execution_time: 60  # seconds
  max_memory_usage: 100   # MB
```

### Approval Requirements

Require explicit approval for sensitive operations:

```yaml
security:
  require_approval: true
```

## Error Handling

MCP operations include comprehensive error handling:

```python
try:
    result = await client.call_tool("risky_operation", {"param": "value"})
    if result.isError:
        print(f"Tool execution failed: {result.content}")
    else:
        print(f"Success: {result.content}")
except Exception as e:
    print(f"MCP operation failed: {e}")
```

## Logging and Debugging

Enable detailed logging for MCP operations:

```yaml
integration:
  logging:
    level: "DEBUG"
    log_mcp_messages: true
    log_tool_calls: true
```

## Performance Optimization

### Connection Pooling

Reuse MCP connections where possible:

```python
# Keep clients connected for multiple operations
client = MCPVertexFlowClient("persistent", "1.0.0")
await client.connect_stdio("server-command")

# Perform multiple operations
resources = await client.get_resources()
for resource in resources:
    content = await client.read_resource(resource.uri)
    # Process content...

# Close when done
await client.close()
```

### Caching

Cache frequently accessed resources:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
async def get_cached_resource(uri: str) -> str:
    return await client.read_resource(uri)
```

## Troubleshooting

### Common Issues

1. **Server Not Found**: Ensure MCP server is installed and accessible
2. **Permission Denied**: Check file/directory permissions
3. **Connection Timeout**: Increase timeout settings
4. **Protocol Version Mismatch**: Ensure compatible MCP versions

### Debug Mode

Enable debug mode for detailed error information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# MCP operations will now show detailed logs
```

### Testing Connections

Test MCP server connectivity:

```bash
# Test filesystem server
echo '{"jsonrpc": "2.0", "id": 1, "method": "ping"}' | npx @modelcontextprotocol/server-filesystem /data
```

## Best Practices

1. **Resource Management**: Always close MCP clients when done
2. **Error Handling**: Implement comprehensive error handling
3. **Security**: Follow principle of least privilege
4. **Performance**: Cache frequently accessed resources
5. **Monitoring**: Log MCP operations for debugging
6. **Configuration**: Use environment variables for sensitive data

## API Reference

### MCPClient

- `connect_stdio(command, *args)`: Connect via stdio
- `connect_http(base_url)`: Connect via HTTP
- `list_resources()`: List available resources
- `read_resource(uri)`: Read resource content
- `list_tools()`: List available tools
- `call_tool(name, args)`: Execute a tool
- `list_prompts()`: List available prompts
- `get_prompt(name, args)`: Get prompt content

### MCPServer

- `set_resource_provider(provider)`: Set resource provider
- `set_tool_provider(provider)`: Set tool provider
- `set_prompt_provider(provider)`: Set prompt provider
- `run_stdio()`: Run server on stdio
- `run_http(host, port)`: Run HTTP server

### MCPVertexFlowServer

- `add_resource(uri, name, content)`: Add resource
- `add_function_tool(tool)`: Add function tool
- `add_prompt(name, template, desc)`: Add prompt template

## Examples Repository

Find more examples in the `vertex_flow/examples/` directory:

- `mcp_example.py`: Basic MCP usage
- `mcp_filesystem_example.py`: Filesystem integration
- `mcp_workflow_example.py`: Workflow integration
- `mcp_server_example.py`: Custom MCP server

## Contributing

To contribute MCP integrations:

1. Follow the MCP specification
2. Add comprehensive tests
3. Update documentation
4. Consider security implications
5. Provide usage examples 