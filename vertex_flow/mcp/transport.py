"""
MCP Transport Layer

Implements different transport mechanisms for MCP communication:
- stdio: Standard input/output transport
- HTTP: HTTP-based Server-Sent Events (SSE) transport
"""

import asyncio
import json
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Callable, Dict, Optional

import aiohttp
from aiohttp import web

from vertex_flow.utils.logger import LoggerUtil

from .types import MCPMessage, MCPNotification, MCPRequest, MCPResponse

logger = LoggerUtil.get_logger(__name__)


class MCPTransport(ABC):
    """Abstract base class for MCP transport mechanisms"""

    @abstractmethod
    async def send_message(self, message: MCPMessage) -> None:
        """Send a message through the transport"""
        pass

    @abstractmethod
    async def receive_message(self) -> MCPMessage:
        """Receive a message from the transport"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport connection"""
        pass


class StdioTransport(MCPTransport):
    """Standard input/output transport for MCP

    Used when the MCP server runs as a child process and communicates
    via stdin/stdout.
    """

    def __init__(self, process: Optional[subprocess.Popen] = None):
        self.process = process
        self._stdin_writer: Optional[asyncio.StreamWriter] = None
        self._stdout_reader: Optional[asyncio.StreamReader] = None
        self._stderr_reader: Optional[asyncio.StreamReader] = None
        self._closed = False

    async def start_server(self, command: str, *args: str) -> None:
        """Start an MCP server as a child process"""
        try:
            # Create subprocess with pipes
            self.process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Get stream readers/writers
            self._stdin_writer = self.process.stdin
            self._stdout_reader = self.process.stdout
            self._stderr_reader = self.process.stderr

            # Start stderr monitoring task
            asyncio.create_task(self._monitor_stderr())

            logger.info(f"Started MCP server: {command} {' '.join(args)}")

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def connect_to_stdio(self) -> None:
        """Connect to existing stdio streams (for server mode)"""
        self._stdout_reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self._stdout_reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        transport, protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        self._stdin_writer = asyncio.StreamWriter(transport, protocol, None, asyncio.get_event_loop())

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message via stdout"""
        if self._closed or not self._stdin_writer:
            raise RuntimeError("Transport is closed or not initialized")

        try:
            json_str = message.to_json()
            line = json_str + "\n"

            self._stdin_writer.write(line.encode("utf-8"))
            await self._stdin_writer.drain()

            logger.debug(f"Sent message: {json_str}")

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def receive_message(self) -> MCPMessage:
        """Receive a message via stdin"""
        if self._closed or not self._stdout_reader:
            raise RuntimeError("Transport is closed or not initialized")

        try:
            line = await self._stdout_reader.readline()
            if not line:
                raise EOFError("Connection closed")

            json_str = line.decode("utf-8").strip()
            if not json_str:
                # Empty line, try again
                return await self.receive_message()

            message = MCPMessage.from_json(json_str)
            logger.debug(f"Received message: {json_str}")

            return message

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to receive message: {e}")
            raise

    async def _monitor_stderr(self) -> None:
        """Monitor stderr for logging output"""
        if not self._stderr_reader:
            return

        try:
            while not self._closed:
                line = await self._stderr_reader.readline()
                if not line:
                    break

                stderr_msg = line.decode("utf-8").strip()
                if stderr_msg:
                    logger.info(f"Server stderr: {stderr_msg}")

        except Exception as e:
            logger.debug(f"Stderr monitoring stopped: {e}")

    async def close(self) -> None:
        """Close the transport and terminate the process"""
        if self._closed:
            return

        self._closed = True

        try:
            if self._stdin_writer:
                self._stdin_writer.close()
                await self._stdin_writer.wait_closed()

            if self.process:
                # Terminate the process gracefully
                self.process.terminate()
                try:
                    # Wait for process to terminate
                    await asyncio.get_event_loop().run_in_executor(None, self.process.wait)
                except asyncio.TimeoutError:
                    # Force kill if graceful termination fails
                    self.process.kill()
                    await asyncio.get_event_loop().run_in_executor(None, self.process.wait)

                # Additional cleanup for npx processes
                try:
                    import subprocess

                    import psutil

                    # Get all child processes
                    parent = psutil.Process(self.process.pid)
                    children = parent.children(recursive=True)

                    # Terminate all child processes
                    for child in children:
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass

                    # Wait for children to terminate
                    gone, alive = psutil.wait_procs(children, timeout=3)

                    # Force kill any remaining children
                    for child in alive:
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass

                except ImportError:
                    # psutil not available, use basic cleanup
                    logger.debug("psutil not available, using basic process cleanup")
                except Exception as e:
                    logger.debug(f"Error during child process cleanup: {e}")

                logger.info("MCP server process terminated")

        except Exception as e:
            logger.error(f"Error closing transport: {e}")


class HTTPTransport(MCPTransport):
    """HTTP-based Server-Sent Events transport for MCP

    Used for HTTP-based MCP servers that support multiple client connections.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.sse_task: Optional[asyncio.Task] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.post_endpoint: Optional[str] = None
        self._closed = False

    async def connect(self) -> None:
        """Connect to the HTTP MCP server"""
        if self._closed:
            raise RuntimeError("Transport is closed")

        self.session = aiohttp.ClientSession()

        # Start SSE connection
        self.sse_task = asyncio.create_task(self._sse_listener())

        # Wait for endpoint discovery
        await asyncio.sleep(0.1)  # Give SSE time to connect

        logger.info(f"Connected to HTTP MCP server: {self.base_url}")

    async def _sse_listener(self) -> None:
        """Listen for Server-Sent Events"""
        if not self.session:
            return

        sse_url = f"{self.base_url}/sse"

        try:
            async with self.session.get(sse_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"SSE connection failed: {response.status}")

                async for line in response.content:
                    if self._closed:
                        break

                    line_str = line.decode("utf-8").strip()
                    if not line_str or line_str.startswith(":"):
                        continue

                    # Parse SSE format
                    if line_str.startswith("event: "):
                        event_type = line_str[7:]
                        continue
                    elif line_str.startswith("data: "):
                        data = line_str[6:]

                        if event_type == "endpoint":
                            # Server sending POST endpoint
                            endpoint_data = json.loads(data)
                            self.post_endpoint = endpoint_data.get("uri")
                            logger.debug(f"Received POST endpoint: {self.post_endpoint}")
                        elif event_type == "message":
                            # Server sending MCP message
                            message = MCPMessage.from_json(data)
                            await self.message_queue.put(message)

        except Exception as e:
            if not self._closed:
                logger.error(f"SSE listener error: {e}")
                await self.message_queue.put(e)

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message via HTTP POST"""
        if self._closed or not self.session:
            raise RuntimeError("Transport is closed or not connected")

        if not self.post_endpoint:
            raise RuntimeError("POST endpoint not discovered yet")

        try:
            json_data = message.to_dict()

            async with self.session.post(
                self.post_endpoint, json=json_data, headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP request failed: {response.status}")

            logger.debug(f"Sent HTTP message: {message.to_json()}")

        except Exception as e:
            logger.error(f"Failed to send HTTP message: {e}")
            raise

    async def receive_message(self) -> MCPMessage:
        """Receive a message from the message queue"""
        if self._closed:
            raise RuntimeError("Transport is closed")

        try:
            item = await self.message_queue.get()

            if isinstance(item, Exception):
                raise item

            return item

        except Exception as e:
            logger.error(f"Failed to receive HTTP message: {e}")
            raise

    async def close(self) -> None:
        """Close the HTTP transport"""
        if self._closed:
            return

        self._closed = True

        try:
            if self.sse_task:
                self.sse_task.cancel()
                try:
                    await self.sse_task
                except asyncio.CancelledError:
                    pass

            if self.session:
                await self.session.close()

            logger.info("HTTP transport closed")

        except Exception as e:
            logger.error(f"Error closing HTTP transport: {e}")


class HTTPServer:
    """HTTP server for MCP (server-side implementation)"""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.clients: Dict[str, web.StreamResponse] = {}
        self.message_handler: Optional[Callable[[MCPMessage], MCPMessage]] = None

        # Setup routes
        self.app.router.add_get("/sse", self._sse_handler)
        self.app.router.add_post("/messages", self._message_handler)

    def set_message_handler(self, handler: Callable[[MCPMessage], MCPMessage]) -> None:
        """Set the message handler function"""
        self.message_handler = handler

    async def _sse_handler(self, request: web.Request) -> web.StreamResponse:
        """Handle SSE connections"""
        response = web.StreamResponse()
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"

        await response.prepare(request)

        # Send endpoint discovery
        client_id = id(response)
        self.clients[str(client_id)] = response

        endpoint_data = {"uri": f"http://{self.host}:{self.port}/messages"}

        await self._send_sse_event(response, "endpoint", endpoint_data)

        # Keep connection alive
        try:
            while True:
                await asyncio.sleep(1)
                await response.write(b": keepalive\n\n")
        except Exception:
            # Client disconnected
            if str(client_id) in self.clients:
                del self.clients[str(client_id)]

        return response

    async def _message_handler(self, request: web.Request) -> web.Response:
        """Handle incoming MCP messages"""
        try:
            data = await request.json()
            message = MCPMessage.from_dict(data)

            if self.message_handler:
                response_message = self.message_handler(message)
                if response_message:
                    # Broadcast response to all connected clients
                    await self._broadcast_message(response_message)

            return web.Response(status=200)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return web.Response(status=500, text=str(e))

    async def _send_sse_event(self, response: web.StreamResponse, event_type: str, data: Any) -> None:
        """Send an SSE event"""
        event_data = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        await response.write(event_data.encode("utf-8"))

    async def _broadcast_message(self, message: MCPMessage) -> None:
        """Broadcast a message to all connected clients"""
        if not self.clients:
            return

        disconnected = []

        for client_id, response in self.clients.items():
            try:
                await self._send_sse_event(response, "message", message.to_dict())
            except Exception:
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            if client_id in self.clients:
                del self.clients[client_id]

    async def start(self) -> None:
        """Start the HTTP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"MCP HTTP server started on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the HTTP server"""
        # Close all client connections
        for response in self.clients.values():
            try:
                await response.write_eof()
            except Exception:
                pass

        self.clients.clear()
        logger.info("MCP HTTP server stopped")
