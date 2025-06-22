"""
Model Context Protocol (MCP) Support for Vertex Flow

This module provides MCP client and server implementations for integrating
with external data sources and tools using the Model Context Protocol.

MCP enables seamless integration between LLM applications and external
data sources and tools through a standardized protocol.
"""

try:
    from .client import MCPClient
    from .server import MCPServer
    from .transport import HTTPTransport, StdioTransport
    from .types import (
        MCPCapabilities,
        MCPClientInfo,
        MCPMessage,
        MCPNotification,
        MCPRequest,
        MCPResponse,
        MCPServerInfo,
    )
except ImportError as e:
    # Handle import errors gracefully during development
    import warnings

    warnings.warn(f"MCP module import error: {e}. MCP functionality may be limited.")

__version__ = "1.0.0"

__all__ = [
    "MCPClient",
    "MCPServer",
    "StdioTransport",
    "HTTPTransport",
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "MCPCapabilities",
    "MCPServerInfo",
    "MCPClientInfo",
]
