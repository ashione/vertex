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
    def setup_method(self):
        """测试方法设置"""
        self.config_path = default_config_path("llm.yml")
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
        assert len(workflow.vertices) == 8, f"期望8个顶点，实际{len(workflow.vertices)}个"

        # 验证顶点连接
        expected_vertices = [
            "topic_analysis",
            "analysis_plan",
            "step_execution",
            "deep_analysis",
            "cross_validation",
            "summary_report",
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

        # 执行工作流
        logger.info("开始执行工作流...")
        workflow.execute_workflow(test_input, stream=False)

        # 获取结果
        results = workflow.result()
        status = workflow.status()

        # 验证结果
        assert results is not None, "工作流结果为空"
        assert len(results) > 0, "工作流没有产生结果"

        logger.info(f"✅ 工作流执行测试通过")
        logger.info(f"工作流状态: {status}")
        logger.info(f"最终结果: {results.get('sink', '无结果')}")

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
        assert len(workflow.vertices) == 8, f"期望8个顶点，实际{len(workflow.vertices)}个"

        logger.info("✅ 工厂函数测试通过")

    def test_prompt_templates(self):
        """测试提示词模板"""
        logger.info("开始测试提示词模板...")

        # 测试所有提示词方法
        prompt_methods = [
            "_get_topic_analysis_system_prompt",
            "_get_topic_analysis_user_prompt",
            "_get_analysis_plan_system_prompt",
            "_get_analysis_plan_user_prompt",
            "_get_step_analysis_system_prompt",
            "_get_step_analysis_user_prompt",
            "_get_deep_analysis_system_prompt",
            "_get_deep_analysis_user_prompt",
            "_get_cross_validation_system_prompt",
            "_get_cross_validation_user_prompt",
            "_get_summary_report_system_prompt",
            "_get_summary_report_user_prompt",
        ]

        for method_name in prompt_methods:
            method = getattr(self.workflow_builder, method_name)
            prompt = method()
            assert isinstance(prompt, str), f"{method_name} 返回的不是字符串"
            assert len(prompt.strip()) > 0, f"{method_name} 返回空提示词"
            logger.debug(f"✓ {method_name}: {len(prompt)} 字符")

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
