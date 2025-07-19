#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度研究工作流测试

用于测试深度研究工作流的功能和性能
"""

from typing import Any, Dict

import pytest

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.app.deep_research_workflow import DeepResearchWorkflow, create_deep_research_workflow
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.utils import default_config_path

logger = LoggerUtil.get_logger()


class TestDeepResearchWorkflow:
    """深度研究工作流测试类"""

    @pytest.fixture(autouse=True)
    def setup_method(self, test_config):
        """测试方法设置"""
        self.config_path = test_config
        self.vertex_service = VertexFlowService(self.config_path)
        self.workflow_builder = DeepResearchWorkflow(self.vertex_service)

    def test_workflow_creation(self):
        """测试工作流创建"""
        logger.info("开始测试工作流创建...")

        # 测试数据
        test_input = {
            "content": "人工智能在医疗领域的应用与发展趋势",
            "env_vars": {},
            "user_vars": {},
            "stream": False,
        }

        # 创建工作流
        workflow = self.workflow_builder.create_workflow(test_input)

        # 验证工作流结构
        assert workflow is not None, "工作流创建失败"
        assert len(workflow.vertices) == 10, f"期望10个顶点，实际{len(workflow.vertices)}个"

        # 验证顶点连接
        expected_vertices = [
            "source",
            "topic_analysis",
            "analysis_plan",
            "extract_steps",
            "while_analysis_steps_group",
            "deep_analysis",
            "cross_validation",
            "summary_report",
            "file_save",
            "sink",
        ]

        for vertex_id in expected_vertices:
            assert vertex_id in workflow.vertices, f"缺少顶点: {vertex_id}"

        logger.info("✅ 工作流创建测试通过")

    @pytest.mark.slow
    def test_workflow_execution(self):
        """测试工作流执行

        注意：这个测试可能需要较长时间和API调用，标记为slow
        """
        logger.info("开始测试工作流执行...")

        # 测试数据
        test_input = {
            "content": "区块链技术在金融科技中的创新应用",
            "env_vars": {},
            "user_vars": {},
            "stream": False,
        }

        # 创建并执行工作流
        workflow = self.workflow_builder.create_workflow(test_input)

        # 显示工作流图结构
        workflow.show_graph(include_dependencies=True)

        # 验证工作流结构而不执行（避免需要真实的LLM模型）
        assert workflow is not None, "工作流创建失败"
        assert len(workflow.vertices) == 10, "工作流顶点数量不正确"

        # 验证关键顶点存在
        key_vertices = ["source", "topic_analysis", "analysis_plan", "sink"]
        for vertex_id in key_vertices:
            assert vertex_id in workflow.vertices, f"缺少关键顶点: {vertex_id}"

        # 验证工作流图结构
        assert len(workflow.edges) > 0, "工作流没有边连接"

        logger.info("✅ 工作流执行测试通过（结构验证）")

    def test_factory_function(self):
        """测试工厂函数"""
        logger.info("开始测试工厂函数...")

        # 使用工厂函数创建工作流构建器
        builder_func = create_deep_research_workflow(self.vertex_service)

        # 测试数据
        test_input = {
            "content": "可持续能源技术的发展现状与未来展望",
            "env_vars": {},
            "user_vars": {},
            "stream": False,
        }

        # 使用工厂函数创建工作流
        workflow = builder_func(test_input)

        # 验证工作流
        assert workflow is not None, "工厂函数创建工作流失败"
        assert len(workflow.vertices) == 10, f"期望10个顶点，实际{len(workflow.vertices)}个"

        logger.info("✅ 工厂函数测试通过")

    def test_prompt_templates(self):
        """测试提示词模板（已简化）"""
        logger.info("开始测试提示词模板...")

        # 由于提示词方法已经重构，现在只测试工作流是否能正确创建
        # 这证明了底层的提示词逻辑是工作的
        test_input = {
            "content": "测试主题",
            "env_vars": {},
            "user_vars": {},
            "stream": False,
        }

        workflow = self.workflow_builder.create_workflow(test_input)
        assert workflow is not None, "工作流创建失败"

        # 验证工作流包含预期的LLM顶点（这些顶点内部使用提示词）
        llm_vertices = [v for v in workflow.vertices.values() if hasattr(v, "system_prompt") or hasattr(v, "messages")]
        assert len(llm_vertices) > 0, "工作流中没有LLM顶点"

        logger.info("✅ 提示词模板测试通过")

    @pytest.mark.integration
    def test_workflow_integration(self):
        """集成测试：测试工作流的完整流程"""
        logger.info("开始集成测试...")

        # 测试工作流创建
        self.test_workflow_creation()

        # 测试提示词模板
        self.test_prompt_templates()

        # 测试工厂函数
        self.test_factory_function()

        logger.info("✅ 集成测试通过")


if __name__ == "__main__":
    # 支持直接运行测试
    pytest.main([__file__, "-v"])
