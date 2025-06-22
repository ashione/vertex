#!/usr/bin/env python3
"""
Function Tool Manager for Vertex Flow

Manages all available function tools and provides unified access.
"""

from typing import Any, Dict, List, Optional

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.tools.functions import FunctionTool

logger = LoggerUtil.get_logger(__name__)


class FunctionToolManager:
    """Manager for all function tools in Vertex Flow"""

    def __init__(self):
        self._tools: Dict[str, FunctionTool] = {}
        self._service = None

    def set_service(self, service):
        """Set the VertexFlowService instance for tool creation"""
        self._service = service

    def register_tool(self, tool: FunctionTool):
        """Register a function tool"""
        self._tools[tool.name] = tool
        logger.debug(f"Registered function tool: {tool.name}")

    def unregister_tool(self, tool_name: str):
        """Unregister a function tool"""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.debug(f"Unregistered function tool: {tool_name}")

    def get_tool(self, tool_name: str) -> Optional[FunctionTool]:
        """Get a specific function tool"""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[FunctionTool]:
        """List all registered function tools"""
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools"""
        return list(self._tools.keys())

    def execute_tool(self, tool_name: str, inputs: dict, context: Optional[dict] = None) -> Any:
        """Execute a function tool"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        return tool.execute(inputs, context)

    def get_tools_as_openai_format(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI function calling format"""
        return [tool.to_dict() for tool in self._tools.values()]

    def auto_register_builtin_tools(self):
        """Auto-register all built-in tools from service"""
        if not self._service:
            logger.warning("Service not set, cannot auto-register tools")
            return

        registered_count = 0

        # Register command line tool
        try:
            cmd_tool = self._service.get_command_line_tool()
            self.register_tool(cmd_tool)
            registered_count += 1
        except Exception as e:
            logger.warning(f"Failed to register command line tool: {e}")

        # Register web search tools
        web_search_providers = ["bocha", "duckduckgo", "serpapi", "searchapi", "bing"]
        for provider in web_search_providers:
            try:
                web_tool = self._service.get_web_search_tool(provider)
                # Create unique name for each provider
                web_tool.name = f"web_search_{provider}"
                web_tool.description = f"Web search using {provider} - {web_tool.description}"
                self.register_tool(web_tool)
                registered_count += 1
                break  # Only register the first working provider
            except Exception as e:
                logger.debug(f"Failed to register {provider} web search tool: {e}")
                continue

        # Register finance tool
        try:
            finance_tool = self._service.get_finance_tool()
            self.register_tool(finance_tool)
            registered_count += 1
        except Exception as e:
            logger.warning(f"Failed to register finance tool: {e}")

        logger.info(f"Auto-registered {registered_count} built-in function tools")

    def create_custom_tools(self) -> List[FunctionTool]:
        """Create some custom example tools"""
        tools = []

        # Math calculator tool
        def calculate(inputs: dict, context=None):
            """Simple calculator"""
            expression = inputs.get("expression", "")
            try:
                # Safe evaluation - only allow basic math operations
                allowed_chars = set("0123456789+-*/.() ")
                if not all(c in allowed_chars for c in expression):
                    return {"error": "Invalid characters in expression"}

                result = eval(expression)
                return {"result": result, "expression": expression}
            except Exception as e:
                return {"error": str(e)}

        calc_tool = FunctionTool(
            name="calculate",
            description="Perform basic mathematical calculations",
            func=calculate,
            schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2+2', '10*5/2')",
                    }
                },
                "required": ["expression"],
            },
        )
        tools.append(calc_tool)

        # Text processing tool
        def process_text(inputs: dict, context=None):
            """Process text with various operations"""
            text = inputs.get("text", "")
            operation = inputs.get("operation", "count_words")

            if operation == "count_words":
                return {"result": len(text.split()), "operation": operation}
            elif operation == "count_chars":
                return {"result": len(text), "operation": operation}
            elif operation == "uppercase":
                return {"result": text.upper(), "operation": operation}
            elif operation == "lowercase":
                return {"result": text.lower(), "operation": operation}
            elif operation == "reverse":
                return {"result": text[::-1], "operation": operation}
            else:
                return {"error": f"Unknown operation: {operation}"}

        text_tool = FunctionTool(
            name="process_text",
            description="Process text with various operations",
            func=process_text,
            schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to process"},
                    "operation": {
                        "type": "string",
                        "enum": ["count_words", "count_chars", "uppercase", "lowercase", "reverse"],
                        "description": "Operation to perform on the text",
                    },
                },
                "required": ["text", "operation"],
            },
        )
        tools.append(text_tool)

        return tools

    def register_custom_tools(self):
        """Register custom example tools"""
        custom_tools = self.create_custom_tools()
        for tool in custom_tools:
            self.register_tool(tool)
        logger.info(f"Registered {len(custom_tools)} custom tools")


# Global function tool manager instance
_function_tool_manager: Optional[FunctionToolManager] = None


def get_function_tool_manager() -> FunctionToolManager:
    """Get the global function tool manager instance"""
    global _function_tool_manager
    if _function_tool_manager is None:
        _function_tool_manager = FunctionToolManager()
    return _function_tool_manager
