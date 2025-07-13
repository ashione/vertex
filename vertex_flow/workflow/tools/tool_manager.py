#!/usr/bin/env python3
"""
Function Tool Manager for Vertex Flow

Manages all available function tools and provides unified access.
"""

import datetime
from typing import Any, Dict, List, Optional

import pytz

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
                web_tool.description = f"Web search using {provider} - {
                    web_tool.description}"
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

        # Register time tools
        try:
            self.register_time_tools()
            registered_count += 3  # today, time_convert, time_diff
        except Exception as e:
            logger.warning(f"Failed to register time tools: {e}")

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

    def create_time_tools(self) -> List[FunctionTool]:
        """Create time-related tools"""
        tools = []

        # Today tool - get current time in various formats
        def get_today(inputs: dict, context=None):
            """Get current date and time in various formats"""
            format_type = inputs.get("format", "iso")
            timezone_str = inputs.get("timezone", "UTC")
            custom_format = inputs.get("custom_format", "%Y-%m-%d %H:%M:%S")
            include_tz_info = inputs.get("include_timezone_info", True)

            try:
                # Get timezone
                if timezone_str.upper() == "UTC":
                    tz = pytz.UTC
                else:
                    tz = pytz.timezone(timezone_str)

                # Get current time in specified timezone
                now = datetime.datetime.now(tz)

                # Format the time based on requested format
                if format_type == "timestamp":
                    result = str(int(now.timestamp()))
                elif format_type == "timestamp_ms":
                    result = str(int(now.timestamp() * 1000))
                elif format_type == "iso":
                    result = now.isoformat()
                elif format_type == "iso_utc":
                    result = now.astimezone(pytz.UTC).isoformat()
                elif format_type == "date":
                    result = now.strftime("%Y-%m-%d")
                elif format_type == "time":
                    result = now.strftime("%H:%M:%S")
                elif format_type == "datetime":
                    result = now.strftime("%Y-%m-%d %H:%M:%S")
                elif format_type == "rfc2822":
                    result = now.strftime("%a, %d %b %Y %H:%M:%S %z")
                elif format_type == "custom":
                    result = now.strftime(custom_format)
                else:
                    return {"error": f"Unknown format: {format_type}"}

                # Add timezone information if requested
                if include_tz_info:
                    tz_info = f" (Timezone: {timezone_str})"
                    result += tz_info

                return {"result": result, "format": format_type, "timezone": timezone_str}

            except Exception as e:
                return {"error": f"Error getting today's time: {str(e)}"}

        today_tool = FunctionTool(
            name="today",
            description="Get current date and time information in various formats and timezones",
            func=get_today,
            schema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": [
                            "timestamp",
                            "timestamp_ms",
                            "iso",
                            "iso_utc",
                            "date",
                            "time",
                            "datetime",
                            "rfc2822",
                            "custom",
                        ],
                        "description": "Output format for the time information",
                        "default": "iso",
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for the output (e.g., 'UTC', 'Asia/Shanghai', 'America/New_York')",
                        "default": "UTC",
                    },
                    "custom_format": {
                        "type": "string",
                        "description": "Custom format string (used when format is 'custom')",
                        "default": "%Y-%m-%d %H:%M:%S",
                    },
                    "include_timezone_info": {
                        "type": "boolean",
                        "description": "Whether to include timezone information in the output",
                        "default": True,
                    },
                },
                "required": [],
            },
        )
        tools.append(today_tool)

        # Time convert tool
        def convert_time(inputs: dict, context=None):
            """Convert time between different formats and timezones"""
            input_time = inputs.get("input_time")
            input_format = inputs.get("input_format", "iso")
            input_timezone = inputs.get("input_timezone", "UTC")
            output_format = inputs.get("output_format", "iso")
            output_timezone = inputs.get("output_timezone", "UTC")
            custom_format = inputs.get("custom_format", "%Y-%m-%d %H:%M:%S")

            try:
                # Parse input time
                if input_format == "timestamp":
                    dt = datetime.datetime.fromtimestamp(float(input_time), pytz.UTC)
                elif input_format == "timestamp_ms":
                    dt = datetime.datetime.fromtimestamp(float(input_time) / 1000, pytz.UTC)
                elif input_format == "iso":
                    dt = datetime.datetime.fromisoformat(input_time.replace("Z", "+00:00"))
                else:
                    # Try to parse with custom format
                    input_tz = pytz.timezone(input_timezone) if input_timezone != "UTC" else pytz.UTC
                    dt = datetime.datetime.strptime(input_time, custom_format)
                    dt = input_tz.localize(dt)

                # Convert to output timezone
                output_tz = pytz.timezone(output_timezone) if output_timezone != "UTC" else pytz.UTC
                dt = dt.astimezone(output_tz)

                # Format output
                if output_format == "timestamp":
                    result = str(int(dt.timestamp()))
                elif output_format == "timestamp_ms":
                    result = str(int(dt.timestamp() * 1000))
                elif output_format == "iso":
                    result = dt.isoformat()
                elif output_format == "iso_utc":
                    result = dt.astimezone(pytz.UTC).isoformat()
                elif output_format == "date":
                    result = dt.strftime("%Y-%m-%d")
                elif output_format == "time":
                    result = dt.strftime("%H:%M:%S")
                elif output_format == "datetime":
                    result = dt.strftime("%Y-%m-%d %H:%M:%S")
                elif output_format == "rfc2822":
                    result = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
                elif output_format == "custom":
                    result = dt.strftime(custom_format)
                else:
                    return {"error": f"Unknown output format: {output_format}"}

                return {
                    "result": result,
                    "input_time": input_time,
                    "output_format": output_format,
                    "output_timezone": output_timezone,
                }

            except Exception as e:
                return {"error": f"Error converting time: {str(e)}"}

        convert_tool = FunctionTool(
            name="time_convert",
            description="Convert time between different formats and timezones",
            func=convert_time,
            schema={
                "type": "object",
                "properties": {
                    "input_time": {"type": "string", "description": "Input time string or timestamp"},
                    "input_format": {
                        "type": "string",
                        "description": "Format of input time (timestamp, iso, custom)",
                        "default": "iso",
                    },
                    "input_timezone": {"type": "string", "description": "Timezone of input time", "default": "UTC"},
                    "output_format": {
                        "type": "string",
                        "enum": [
                            "timestamp",
                            "timestamp_ms",
                            "iso",
                            "iso_utc",
                            "date",
                            "time",
                            "datetime",
                            "rfc2822",
                            "custom",
                        ],
                        "description": "Desired output format",
                        "default": "iso",
                    },
                    "output_timezone": {"type": "string", "description": "Desired output timezone", "default": "UTC"},
                    "custom_format": {
                        "type": "string",
                        "description": "Custom format string for output",
                        "default": "%Y-%m-%d %H:%M:%S",
                    },
                },
                "required": ["input_time"],
            },
        )
        tools.append(convert_tool)

        # Time difference tool
        def time_difference(inputs: dict, context=None):
            """Calculate time difference between two times"""
            time1 = inputs.get("time1")
            time2 = inputs.get("time2")
            time1_format = inputs.get("time1_format", "iso")
            time2_format = inputs.get("time2_format", "iso")
            time1_timezone = inputs.get("time1_timezone", "UTC")
            time2_timezone = inputs.get("time2_timezone", "UTC")
            output_unit = inputs.get("output_unit", "seconds")

            try:
                # Parse first time
                def parse_time(time_str: str, format_type: str, timezone_str: str) -> datetime.datetime:
                    if format_type == "timestamp":
                        dt = datetime.datetime.fromtimestamp(float(time_str), pytz.UTC)
                    elif format_type == "timestamp_ms":
                        dt = datetime.datetime.fromtimestamp(float(time_str) / 1000, pytz.UTC)
                    elif format_type == "iso":
                        dt = datetime.datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    else:
                        # Try to parse with custom format
                        tz = pytz.timezone(timezone_str) if timezone_str != "UTC" else pytz.UTC
                        dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                        dt = tz.localize(dt)
                    return dt

                dt1 = parse_time(time1, time1_format, time1_timezone)
                dt2 = parse_time(time2, time2_format, time2_timezone)

                # Calculate difference
                diff = abs((dt2 - dt1).total_seconds())

                # Convert to requested unit
                if output_unit == "seconds":
                    result = str(int(diff))
                elif output_unit == "minutes":
                    result = str(round(diff / 60, 2))
                elif output_unit == "hours":
                    result = str(round(diff / 3600, 2))
                elif output_unit == "days":
                    result = str(round(diff / 86400, 2))
                else:
                    return {"error": f"Unknown output unit: {output_unit}"}

                return {"result": f"{result} {output_unit}", "time1": time1, "time2": time2, "difference_seconds": diff}

            except Exception as e:
                return {"error": f"Error calculating time difference: {str(e)}"}

        diff_tool = FunctionTool(
            name="time_diff",
            description="Calculate time difference between two times",
            func=time_difference,
            schema={
                "type": "object",
                "properties": {
                    "time1": {"type": "string", "description": "First time string or timestamp"},
                    "time2": {"type": "string", "description": "Second time string or timestamp"},
                    "time1_format": {"type": "string", "description": "Format of first time", "default": "iso"},
                    "time2_format": {"type": "string", "description": "Format of second time", "default": "iso"},
                    "time1_timezone": {"type": "string", "description": "Timezone of first time", "default": "UTC"},
                    "time2_timezone": {"type": "string", "description": "Timezone of second time", "default": "UTC"},
                    "output_unit": {
                        "type": "string",
                        "enum": ["seconds", "minutes", "hours", "days"],
                        "description": "Unit for the difference output",
                        "default": "seconds",
                    },
                },
                "required": ["time1", "time2"],
            },
        )
        tools.append(diff_tool)

        return tools

    def register_custom_tools(self):
        """Register custom example tools"""
        custom_tools = self.create_custom_tools()
        for tool in custom_tools:
            self.register_tool(tool)
        logger.info(f"Registered {len(custom_tools)} custom tools")

    def register_time_tools(self):
        """Register time-related tools"""
        time_tools = self.create_time_tools()
        for tool in time_tools:
            self.register_tool(tool)
        logger.info(f"Registered {len(time_tools)} time tools")


# Global function tool manager instance
_function_tool_manager: Optional[FunctionToolManager] = None


def get_function_tool_manager() -> FunctionToolManager:
    """Get the global function tool manager instance"""
    global _function_tool_manager
    if _function_tool_manager is None:
        _function_tool_manager = FunctionToolManager()
    return _function_tool_manager
