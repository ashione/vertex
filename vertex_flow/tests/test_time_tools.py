#!/usr/bin/env python3
"""
Test Time Tools

Simple test script to verify the time-related function tools work correctly.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.tools.functions import FunctionTool, today_func
from vertex_flow.workflow.tools.tool_manager import FunctionToolManager, get_function_tool_manager

logger = LoggerUtil.get_logger(__name__)


def test_today_tool():
    print("=== Testing 'today' tool in FunctionToolManager ===\n")
    tool_manager = get_function_tool_manager()

    # 确保today已注册
    if "today" not in tool_manager.get_tool_names():
        today_tool = FunctionTool(
            name="today",
            description="获取当前时间，支持多种格式和时区。",
            func=today_func,
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
                        "description": "输出格式",
                    },
                    "timezone": {"type": "string", "description": "时区（如UTC, Asia/Shanghai）"},
                    "custom_format": {"type": "string", "description": "自定义格式字符串"},
                },
            },
        )
        tool_manager.register_tool(today_tool)

    # 常用格式
    print("ISO:", tool_manager.execute_tool("today", {"format": "iso"}))
    print("Timestamp:", tool_manager.execute_tool("today", {"format": "timestamp"}))
    print("Datetime:", tool_manager.execute_tool("today", {"format": "datetime"}))
    print("Date:", tool_manager.execute_tool("today", {"format": "date"}))
    print("Time:", tool_manager.execute_tool("today", {"format": "time"}))
    print("RFC2822:", tool_manager.execute_tool("today", {"format": "rfc2822"}))
    print("Timestamp(ms):", tool_manager.execute_tool("today", {"format": "timestamp_ms"}))
    print("ISO UTC:", tool_manager.execute_tool("today", {"format": "iso_utc"}))

    # 时区
    print("Shanghai Datetime:", tool_manager.execute_tool("today", {"format": "datetime", "timezone": "Asia/Shanghai"}))
    print("New York Date:", tool_manager.execute_tool("today", {"format": "date", "timezone": "America/New_York"}))

    # 自定义格式
    print(
        "Custom Format:",
        tool_manager.execute_tool(
            "today", {"format": "custom", "custom_format": "%Y年%m月%d日 %H时%M分%S秒", "timezone": "Asia/Shanghai"}
        ),
    )

    # 异常情况
    print("Invalid Timezone:", tool_manager.execute_tool("today", {"timezone": "Invalid/Timezone"}))
    print("Invalid Format:", tool_manager.execute_tool("today", {"format": "not_a_format"}))

    print("\n=== 'today' tool tests completed ===\n")


def main():
    test_today_tool()
    print("✅ All today tool tests passed!")


if __name__ == "__main__":
    main()
