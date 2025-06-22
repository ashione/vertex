"""
MCP Protocol Type Definitions

Defines the core types and data structures for the Model Context Protocol.
Based on the MCP specification version 2024-11-05.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union


class MCPMessageType(Enum):
    """MCP message types"""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPMethod(Enum):
    """Standard MCP methods"""

    # Lifecycle
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"

    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Sampling
    SAMPLING_CREATE_MESSAGE = "sampling/createMessage"

    # Logging
    LOGGING_SET_LEVEL = "logging/setLevel"

    # Utilities
    PING = "ping"
    CANCEL = "cancel"
    PROGRESS = "progress"


@dataclass
class MCPServerInfo:
    """Information about an MCP server"""

    name: str
    version: str


@dataclass
class MCPClientInfo:
    """Information about an MCP client"""

    name: str
    version: str


@dataclass
class MCPCapabilities:
    """MCP capabilities for client or server"""

    # Server capabilities
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None

    # Client capabilities
    roots: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None

    # Experimental features
    experimental: Optional[Dict[str, Any]] = None


@dataclass
class MCPMessage:
    """Base MCP message"""

    jsonrpc: str = "2.0"
    method: Optional[str] = None
    id: Optional[Union[str, int]] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data: Dict[str, Any] = {"jsonrpc": self.jsonrpc}

        if self.method is not None:
            data["method"] = self.method
        if self.id is not None:
            data["id"] = self.id
        if self.params is not None:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error

        return data

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """Create from dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method"),
            id=data.get("id"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MCPMessage":
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class MCPRequest(MCPMessage):
    """MCP request message"""

    def __init__(self, method: str, id: Union[str, int], params: Optional[Dict[str, Any]] = None):
        super().__init__(jsonrpc="2.0", method=method, id=id, params=params, result=None, error=None)


class MCPResponse(MCPMessage):
    """MCP response message"""

    def __init__(self, id: Union[str, int], result: Optional[Any] = None, error: Optional[Dict[str, Any]] = None):
        super().__init__(jsonrpc="2.0", method=None, id=id, params=None, result=result, error=error)


class MCPNotification(MCPMessage):
    """MCP notification message"""

    def __init__(self, method: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(jsonrpc="2.0", method=method, id=None, params=params, result=None, error=None)


@dataclass
class MCPError:
    """MCP error structure"""

    code: int
    message: str
    data: Optional[Any] = None


@dataclass
class MCPPrompt:
    """MCP prompt definition"""

    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


@dataclass
class MCPResource:
    """MCP resource definition"""

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


@dataclass
class MCPTool:
    """MCP tool definition"""

    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class MCPToolCall:
    """MCP tool call request"""

    name: str
    arguments: Dict[str, Any]


@dataclass
class MCPToolResult:
    """MCP tool call result"""

    content: List[Dict[str, Any]]
    isError: bool = False


# Standard error codes
class MCPErrorCode:
    """Standard MCP error codes"""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific errors
    RESOURCE_NOT_FOUND = -32001
    TOOL_NOT_FOUND = -32002
    PROMPT_NOT_FOUND = -32003
    INVALID_TOOL_INPUT = -32004
