#!/usr/bin/env python3
"""
调试MCP工具调用问题
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.mcp_manager import get_mcp_manager

logger = LoggerUtil.get_logger(__name__)


def test_mcp_manager():
    """测试MCP管理器的基本功能"""
    try:
        logger.info("Creating MCP Manager...")
        manager = get_mcp_manager()
        logger.info("MCP Manager created successfully")

        # 初始化MCP配置
        mcp_config = {
            "enabled": True,
            "clients": {
                "everything": {
                    "enabled": True,
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-everything"],
                }
            },
        }

        logger.info("Initializing MCP Manager with config...")
        manager.initialize(mcp_config)
        logger.info("MCP Manager initialized successfully")

        # 测试获取工具列表
        logger.info("Getting all tools...")
        tools = manager.get_all_tools()
        logger.info(f"Found {len(tools)} tools: {[tool.name for tool in tools]}")

        # 如果有工具，尝试调用一个简单的工具
        if tools:
            tool = tools[0]
            logger.info(f"Testing tool: {tool.name}")
            try:
                # 为echo工具提供必需的参数
                if tool.name == "everything_echo":
                    args = {"message": "Hello from MCP test!"}
                else:
                    args = {}

                result = manager.call_tool(tool.name, args)
                logger.info(f"Tool call result: {result}")

                if result:
                    logger.info(f"Tool executed successfully: {result.content}")
                else:
                    logger.warning("Tool returned None result")

            except Exception as e:
                logger.error(f"Error calling tool {tool.name}: {e}")
                import traceback

                traceback.print_exc()

    except Exception as e:
        logger.error(f"Error in test_mcp_manager: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_mcp_manager()
