#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度研究工作流测试脚本

用于测试深度研究工作流的功能和性能
"""

import asyncio
import os
import sys
from typing import Any, Dict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.app.deep_research_workflow import DeepResearchWorkflow, create_deep_research_workflow
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.utils import default_config_path

logger = LoggerUtil.get_logger()


class DeepResearchWorkflowTester:
    """深度研究工作流测试类"""

    def __init__(self, config_path: str = None):
        """初始化测试器

        Args:
            config_path: 配置文件路径，默认使用llm.yml
        """
        self.config_path = config_path or default_config_path("llm.yml")
        self.vertex_service = VertexFlowService(self.config_path)
        self.workflow_builder = DeepResearchWorkflow(self.vertex_service)

    def test_workflow_creation(self) -> bool:
        """测试工作流创建

        Returns:
            bool: 测试是否成功
        """
        try:
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
                "source",
                "topic_analysis",
                "research_planning",
                "information_collection",
                "deep_analysis",
                "cross_validation",
                "summary_report",
                "sink",
            ]

            for vertex_id in expected_vertices:
                assert vertex_id in workflow.vertices, f"缺少顶点: {vertex_id}"

            logger.info("✅ 工作流创建测试通过")
            return True

        except Exception as e:
            logger.error(f"❌ 工作流创建测试失败: {e}")
            return False

    def test_workflow_execution(self) -> bool:
        """测试工作流执行

        Returns:
            bool: 测试是否成功
        """
        try:
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

            return True

        except Exception as e:
            logger.error(f"❌ 工作流执行测试失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_factory_function(self) -> bool:
        """测试工厂函数

        Returns:
            bool: 测试是否成功
        """
        try:
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
            return True

        except Exception as e:
            logger.error(f"❌ 工厂函数测试失败: {e}")
            return False

    def test_prompt_templates(self) -> bool:
        """测试提示词模板

        Returns:
            bool: 测试是否成功
        """
        try:
            logger.info("开始测试提示词模板...")

            # 测试所有提示词方法
            prompt_methods = [
                "_get_topic_analysis_system_prompt",
                "_get_topic_analysis_user_prompt",
                "_get_research_planning_system_prompt",
                "_get_research_planning_user_prompt",
                "_get_information_collection_system_prompt",
                "_get_information_collection_user_prompt",
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
            return True

        except Exception as e:
            logger.error(f"❌ 提示词模板测试失败: {e}")
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试

        Returns:
            Dict[str, bool]: 测试结果字典
        """
        logger.info("🚀 开始运行深度研究工作流全套测试...")

        test_results = {
            "workflow_creation": self.test_workflow_creation(),
            "prompt_templates": self.test_prompt_templates(),
            "factory_function": self.test_factory_function(),
            # "workflow_execution": self.test_workflow_execution(),  # 注释掉执行测试，避免消耗API调用
        }

        # 统计结果
        passed = sum(test_results.values())
        total = len(test_results)

        logger.info(f"\n📊 测试结果汇总:")
        for test_name, result in test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"  {test_name}: {status}")

        logger.info(f"\n🎯 总体结果: {passed}/{total} 测试通过")

        if passed == total:
            logger.info("🎉 所有测试都通过了！深度研究工作流准备就绪。")
        else:
            logger.warning(f"⚠️  有 {total - passed} 个测试失败，请检查相关问题。")

        return test_results


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="深度研究工作流测试")
    parser.add_argument("--config", default=None, help="指定配置文件路径")
    parser.add_argument(
        "--test",
        choices=["creation", "execution", "factory", "prompts", "all"],
        default="all",
        help="指定要运行的测试类型",
    )

    args = parser.parse_args()

    try:
        # 创建测试器
        tester = DeepResearchWorkflowTester(args.config)

        # 运行指定测试
        if args.test == "creation":
            tester.test_workflow_creation()
        elif args.test == "execution":
            tester.test_workflow_execution()
        elif args.test == "factory":
            tester.test_factory_function()
        elif args.test == "prompts":
            tester.test_prompt_templates()
        else:
            tester.run_all_tests()

    except Exception as e:
        logger.error(f"测试运行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
