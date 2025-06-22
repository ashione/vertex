#!/usr/bin/env python3
"""
MCP Manager for Vertex Flow

Manages MCP client connections and provides unified access to MCP resources, tools, and prompts.
"""

import asyncio
import atexit
import signal
import sys
import threading
from typing import Any, Dict, List, Optional, Set

from vertex_flow.utils.logger import LoggerUtil

logger = LoggerUtil.get_logger(__name__)

# MCP support
try:
    from vertex_flow.mcp.types import MCPPrompt, MCPResource, MCPTool, MCPToolResult
    from vertex_flow.mcp.vertex_integration import MCPVertexFlowClient

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP functionality not available")


class MCPManager:
    """MCP Manager for handling multiple MCP clients with thread safety"""

    def __init__(self):
        self.clients: Dict[str, MCPVertexFlowClient] = {}
        self.client_configs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._initialized = False
        # 为每个线程缓存客户端实例
        self._thread_clients: Dict[int, Dict[str, MCPVertexFlowClient]] = {}

    async def initialize(self, mcp_config: Dict[str, Any]):
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
            client = MCPVertexFlowClient(client_name, "1.0.0")

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

            with self._lock:
                self.clients[client_name] = client
                self.client_configs[client_name] = client_config

            logger.info(f"Successfully initialized MCP client: {client_name}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP client {client_name}: {e}")

    async def _ensure_initialized(self):
        """Ensure the manager is initialized"""
        if not self._initialized:
            logger.warning("MCP Manager not initialized")
            return False
        return True

    async def _get_thread_client(self, client_name: str) -> Optional[MCPVertexFlowClient]:
        """获取当前线程的客户端实例，如果不存在则创建"""
        thread_id = threading.get_ident()

        with self._lock:
            # 检查当前线程是否有客户端缓存
            if thread_id not in self._thread_clients:
                self._thread_clients[thread_id] = {}

            thread_clients = self._thread_clients[thread_id]

            # 如果当前线程没有这个客户端，创建一个新的
            if client_name not in thread_clients:
                if client_name not in self.client_configs:
                    return None

                try:
                    # 创建新的客户端实例
                    client_config = self.client_configs[client_name]
                    client = MCPVertexFlowClient(f"{client_name}_thread_{thread_id}", "1.0.0")

                    transport = client_config.get("transport", "stdio")
                    if transport == "stdio":
                        command = client_config.get("command", "")
                        args = client_config.get("args", [])
                        await client.connect_stdio(command, *args)
                    elif transport == "http":
                        base_url = client_config.get("base_url", "")
                        await client.connect_http(base_url)

                    thread_clients[client_name] = client
                    logger.debug(f"Created thread-local client {client_name} for thread {thread_id}")

                except Exception as e:
                    logger.error(f"Failed to create thread-local client {client_name}: {e}")
                    return None

            return thread_clients[client_name]

    async def get_all_resources(self) -> List[MCPResource]:
        """Get all resources from all connected MCP clients with thread-local clients"""
        if not MCP_AVAILABLE:
            return []

        if not await self._ensure_initialized():
            return []

        all_resources = []

        # 获取客户端配置副本
        with self._lock:
            client_names = list(self.client_configs.keys())

        # 使用线程本地客户端
        for client_name in client_names:
            try:
                client = await self._get_thread_client(client_name)
                if not client or not client.is_connected:
                    logger.debug(f"Client {client_name} not available, skipping")
                    continue

                logger.debug(f"Getting resources from thread-local client {client_name}")

                # 增加超时时间，适应多线程环境
                resources = await asyncio.wait_for(client.list_resources(), timeout=20.0)
                logger.info(f"Got {len(resources)} resources from client {client_name}")

                # Add client name prefix to avoid conflicts
                for resource in resources:
                    resource.name = f"{client_name}_{resource.name}"
                    if resource.description:
                        resource.description = f"[{client_name}] {resource.description}"

                all_resources.extend(resources)

                # 在客户端之间添加小延迟，减少冲突
                if len(client_names) > 1:
                    await asyncio.sleep(0.3)

            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting resources from client {client_name}")
                continue
            except Exception as e:
                logger.error(f"Error processing client {client_name}: {e}")
                continue

        logger.info(f"Total resources collected: {len(all_resources)}")
        return all_resources

    async def get_all_tools(self) -> List[MCPTool]:
        """Get all tools from all connected MCP clients with thread-local clients"""
        if not MCP_AVAILABLE:
            return []

        if not await self._ensure_initialized():
            return []

        all_tools = []

        # 获取客户端配置副本
        with self._lock:
            client_names = list(self.client_configs.keys())

        # 使用线程本地客户端
        for client_name in client_names:
            try:
                client = await self._get_thread_client(client_name)
                if not client or not client.is_connected:
                    logger.debug(f"Client {client_name} not available, skipping")
                    continue

                logger.debug(f"Getting tools from thread-local client {client_name}")

                # 增加超时时间，适应多线程环境
                tools = await asyncio.wait_for(client.list_tools(), timeout=20.0)
                logger.info(f"Got {len(tools)} tools from client {client_name}")

                # Add client name prefix to avoid conflicts
                for tool in tools:
                    tool.name = f"{client_name}_{tool.name}"
                    tool.description = f"[{client_name}] {tool.description or ''}"

                all_tools.extend(tools)

                # 在客户端之间添加小延迟，减少冲突
                if len(client_names) > 1:
                    await asyncio.sleep(0.5)

            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting tools from client {client_name}")
                continue
            except Exception as e:
                logger.error(f"Error processing client {client_name}: {e}")
                continue

        logger.info(f"Total tools collected: {len(all_tools)}")
        return all_tools

    async def get_all_prompts(self) -> List[MCPPrompt]:
        """Get all prompts from all connected MCP clients"""
        if not MCP_AVAILABLE:
            return []

        if not await self._ensure_initialized():
            return []

        all_prompts = []

        with self._lock:
            clients_copy = list(self.clients.items())

        for client_name, client in clients_copy:
            try:
                if client.is_connected:
                    prompts = await client.get_prompts()
                    # Add client name prefix to avoid conflicts
                    for prompt in prompts:
                        prompt.name = f"{client_name}:{prompt.name}"
                        prompt.description = f"[{client_name}] {prompt.description or ''}"
                    all_prompts.extend(prompts)

                    # Small delay between clients to avoid conflicts
                    await asyncio.sleep(0.2)
            except Exception as e:
                logger.error(f"Failed to get prompts from client {client_name}: {e}")

        return all_prompts

    async def read_resource(self, resource_uri: str) -> Optional[str]:
        """Read a resource by URI from appropriate MCP client"""
        if not MCP_AVAILABLE:
            return None

        if not await self._ensure_initialized():
            return None

        with self._lock:
            clients_copy = list(self.clients.items())

        for client_name, client in clients_copy:
            try:
                if client.is_connected:
                    content = await client.read_resource(resource_uri)
                    return content
            except Exception as e:
                logger.debug(f"Client {client_name} cannot read resource {resource_uri}: {e}")
                continue

        logger.warning(f"No client can read resource: {resource_uri}")
        return None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[MCPToolResult]:
        """Call a tool from appropriate MCP client"""
        if not MCP_AVAILABLE:
            return None

        if not await self._ensure_initialized():
            return None

        # Parse tool name to get client and original tool name (使用下划线分隔)
        if "_" in tool_name and (tool_name.startswith("filesystem_") or tool_name.startswith("everything_")):
            parts = tool_name.split("_", 1)
            if len(parts) == 2:
                client_name, original_tool_name = parts
            else:
                logger.warning(f"Invalid tool name format: {tool_name}")
                return None
        else:
            # Try all clients if no prefix
            thread_id = threading.get_ident()
            with self._lock:
                client_names = list(self.client_configs.keys())

            for client_name in client_names:
                try:
                    client = await self._get_thread_client(client_name)
                    if client and client.is_connected:
                        result = await client.call_tool(tool_name, arguments)
                        return result
                except Exception as e:
                    logger.error(f"Client {client_name} cannot call tool {tool_name}: {e}")
                    continue
            logger.warning(f"No client can call tool: {tool_name}")
            return None

        # Call tool from specific client using thread-local client
        try:
            client = await self._get_thread_client(client_name)
            if client and client.is_connected:
                result = await client.call_tool(original_tool_name, arguments)
                return result
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")

        logger.warning(f"Client {client_name} not connected or not available")
        return None

    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get a prompt from appropriate MCP client"""
        if not MCP_AVAILABLE:
            return None

        if not await self._ensure_initialized():
            return None

        # Parse prompt name to get client and original prompt name
        if ":" in prompt_name:
            client_name, original_prompt_name = prompt_name.split(":", 1)
        else:
            # Try all clients if no prefix
            with self._lock:
                clients_copy = list(self.clients.items())

            for client_name, client in clients_copy:
                try:
                    if client.is_connected:
                        content = await client.get_prompt(prompt_name, arguments)
                        return content
                except Exception as e:
                    logger.debug(f"Client {client_name} cannot get prompt {prompt_name}: {e}")
                    continue
            logger.warning(f"No client can get prompt: {prompt_name}")
            return None

        # Get prompt from specific client
        with self._lock:
            if client_name not in self.clients:
                logger.warning(f"Client {client_name} not found")
                return None
            client = self.clients[client_name]

        try:
            if client.is_connected:
                content = await client.get_prompt(original_prompt_name, arguments)
                return content
        except Exception as e:
            logger.error(f"Failed to get prompt {prompt_name}: {e}")

        logger.warning(f"Client {client_name} not connected")
        return None

    def get_connected_clients(self) -> List[str]:
        """Get list of connected client names"""
        if not MCP_AVAILABLE:
            return []

        with self._lock:
            return [name for name, client in self.clients.items() if client.is_connected]

    def get_client_info(self, client_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific client"""
        if not MCP_AVAILABLE:
            return None

        with self._lock:
            if client_name not in self.clients:
                return None

            client = self.clients[client_name]
            config = self.client_configs[client_name]
            return {
                "name": client_name,
                "connected": client.is_connected,
                "transport": config.get("transport"),
                "description": config.get("description", ""),
            }

    async def close_all(self):
        """Close all MCP client connections"""
        logger.info("Closing all MCP client connections")

        with self._lock:
            clients_copy = list(self.clients.items())
            self.clients.clear()
            self.client_configs.clear()
            self._initialized = False

        for client_name, client in clients_copy:
            try:
                await client.close()
                logger.debug(f"Closed MCP client: {client_name}")
            except Exception as e:
                logger.error(f"Error closing MCP client {client_name}: {e}")

    async def refresh_client(self, client_name: str):
        """Refresh a specific MCP client connection"""
        with self._lock:
            if client_name not in self.client_configs:
                raise ValueError(f"Client {client_name} not configured")

            # Close existing client
            if client_name in self.clients:
                try:
                    await self.clients[client_name].close()
                except Exception as e:
                    logger.warning(f"Error closing client {client_name}: {e}")

            client_config = self.client_configs[client_name]

        # Recreate client
        try:
            await self._create_client(client_name, client_config)
            logger.info(f"Successfully refreshed MCP client: {client_name}")
        except Exception as e:
            logger.error(f"Failed to refresh MCP client {client_name}: {e}")
            raise


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
            logger.info("Cleaned up MCP server processes")
        except Exception as e:
            logger.warning(f"Error during MCP cleanup: {e}")


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
