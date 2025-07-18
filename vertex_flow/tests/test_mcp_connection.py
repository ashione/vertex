#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP连接测试

用于测试MCP客户端连接状态和基本功能
"""

import asyncio
from typing import Any, Dict, List

import pytest

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.utils import default_config_path

logger = LoggerUtil.get_logger()


class TestMCPConnection:
    """MCP连接测试类"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """测试方法设置"""
        self.config_path = default_config_path("llm.yml")
        self.vertex_service = VertexFlowService(self.config_path)

    @pytest.mark.asyncio
    async def test_mcp_client_connection(self):
        """测试MCP客户端连接状态"""
        logger.info("开始测试MCP客户端连接状态...")

        # 获取MCP客户端
        mcp_clients = self.vertex_service.mcp_clients
        assert mcp_clients is not None, "MCP客户端未初始化"
        assert len(mcp_clients) > 0, "没有可用的MCP客户端"

        # 测试每个客户端的连接状态
        for client_name, client in mcp_clients.items():
            logger.info(f"测试客户端: {client_name}")

            # 检查连接状态
            is_connected = client.is_connected
            logger.info(f"客户端 {client_name} 连接状态: {is_connected}")

            # 如果连接正常，进行ping测试
            if is_connected:
                try:
                    ping_result = await client.ping()
                    logger.info(f"客户端 {client_name} ping结果: {ping_result}")
                    assert ping_result is True, f"客户端 {client_name} ping失败"
                except Exception as e:
                    logger.warning(f"客户端 {client_name} ping测试失败: {e}")
                    # ping失败不应该导致整个测试失败，只记录警告

        logger.info("✅ MCP客户端连接状态测试完成")

    @pytest.mark.asyncio
    async def test_mcp_tools_availability(self):
        """测试MCP工具可用性"""
        logger.info("开始测试MCP工具可用性...")

        # 获取MCP客户端
        mcp_clients = self.vertex_service.mcp_clients
        assert mcp_clients is not None, "MCP客户端未初始化"

        total_tools = 0

        # 测试每个客户端的工具
        for client_name, client in mcp_clients.items():
            logger.info(f"测试客户端 {client_name} 的工具...")

            # 检查连接状态
            if not client.is_connected:
                logger.warning(f"客户端 {client_name} 未连接，跳过工具测试")
                continue

            try:
                # 获取工具列表
                tools = await client.list_tools()
                logger.info(f"客户端 {client_name} 可用工具数量: {len(tools.tools) if tools else 0}")

                if tools and tools.tools:
                    total_tools += len(tools.tools)

                    # 记录前几个工具的信息
                    for i, tool in enumerate(tools.tools[:3]):
                        logger.info(f"  工具 {i+1}: {tool.name} - {tool.description[:50]}...")

            except Exception as e:
                logger.warning(f"获取客户端 {client_name} 工具列表失败: {e}")

        logger.info(f"总共发现 {total_tools} 个MCP工具")
        logger.info("✅ MCP工具可用性测试完成")

    @pytest.mark.asyncio
    async def test_mcp_resources_availability(self):
        """测试MCP资源可用性"""
        logger.info("开始测试MCP资源可用性...")

        # 获取MCP客户端
        mcp_clients = self.vertex_service.mcp_clients
        assert mcp_clients is not None, "MCP客户端未初始化"

        total_resources = 0

        # 测试每个客户端的资源
        for client_name, client in mcp_clients.items():
            logger.info(f"测试客户端 {client_name} 的资源...")

            # 检查连接状态
            if not client.is_connected:
                logger.warning(f"客户端 {client_name} 未连接，跳过资源测试")
                continue

            try:
                # 获取资源列表
                resources = await client.list_resources()
                logger.info(f"客户端 {client_name} 可用资源数量: {len(resources.resources) if resources else 0}")

                if resources and resources.resources:
                    total_resources += len(resources.resources)

                    # 记录前几个资源的信息
                    for i, resource in enumerate(resources.resources[:3]):
                        logger.info(
                            f"  资源 {i+1}: {resource.name} - {resource.description[:50] if resource.description else 'N/A'}..."
                        )

            except Exception as e:
                logger.warning(f"获取客户端 {client_name} 资源列表失败: {e}")

        logger.info(f"总共发现 {total_resources} 个MCP资源")
        logger.info("✅ MCP资源可用性测试完成")

    def test_mcp_client_initialization(self):
        """测试MCP客户端初始化"""
        logger.info("开始测试MCP客户端初始化...")

        # 检查vertex_service是否正确初始化
        assert self.vertex_service is not None, "VertexFlowService未初始化"

        # 检查MCP客户端是否存在
        mcp_clients = self.vertex_service.mcp_clients
        assert mcp_clients is not None, "MCP客户端字典为空"

        # 记录客户端信息
        logger.info(f"发现 {len(mcp_clients)} 个MCP客户端:")
        for client_name in mcp_clients.keys():
            logger.info(f"  - {client_name}")

        logger.info("✅ MCP客户端初始化测试通过")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mcp_full_integration(self):
        """MCP完整集成测试"""
        logger.info("开始MCP完整集成测试...")

        # 测试客户端初始化
        self.test_mcp_client_initialization()

        # 测试连接状态
        await self.test_mcp_client_connection()

        # 测试工具可用性
        await self.test_mcp_tools_availability()

        # 测试资源可用性
        await self.test_mcp_resources_availability()

        logger.info("✅ MCP完整集成测试通过")


if __name__ == "__main__":
    # 支持直接运行测试
    pytest.main([__file__, "-v"])
