#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度研究工作流 - 使用代码构建的多阶段研究分析工作流

该工作流包含以下六个阶段：
1. 主题分析 - 分析研究主题，确定研究范围和关键问题
2. 研究规划 - 制定详细的研究计划和方法论
3. 信息收集 - 系统性地收集和整理相关信息资料
4. 深度分析 - 对收集的信息进行深度分析和洞察
5. 交叉验证 - 验证分析结果的准确性和可靠性
6. 总结报告 - 生成完整的研究总结报告
"""

from typing import Any, Dict

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import ENABLE_STREAM, SYSTEM, USER
from vertex_flow.workflow.workflow import (
    LLMVertex,
    SinkVertex,
    SourceVertex,
    Workflow,
    WorkflowContext,
)

logger = LoggerUtil.get_logger()


class DeepResearchWorkflow:
    """深度研究工作流类"""

    def __init__(self, vertex_service):
        self.vertex_service = vertex_service
        self.workflow_name = "deep-research"
        self.description = "Deep Research Workflow for comprehensive topic analysis and investigation"

    def create_workflow(self, input_data: Dict[str, Any]) -> Workflow:
        """创建深度研究工作流

        Args:
            input_data: 包含研究主题和其他参数的输入数据

        Returns:
            Workflow: 配置好的工作流实例
        """
        # 创建工作流上下文
        context = WorkflowContext(
            env_parameters=input_data.get("env_vars", {}), user_parameters=input_data.get("user_vars", {})
        )

        # 创建工作流
        workflow = Workflow(context)

        # 获取研究主题
        research_topic = input_data.get("content", "")
        logger.info(f"开始深度研究，研究主题：{research_topic}")
        stream_mode = input_data.get("stream", False)

        # 创建源顶点
        source = SourceVertex(
            id="source",
            task=lambda inputs, context: {
                "research_topic": inputs.get("content", research_topic),
                "message": f"开始深度研究：{inputs.get('content', research_topic)}",
            },
        )

        # 1. 主题分析顶点
        topic_analysis = LLMVertex(
            id="topic_analysis",
            params={
                "model": self.vertex_service.get_chatmodel(),
                SYSTEM: self._get_topic_analysis_system_prompt(),
                USER: [self._get_topic_analysis_user_prompt()],
                ENABLE_STREAM: stream_mode,
            },
        )

        # 2. 研究规划顶点
        research_planning = LLMVertex(
            id="research_planning",
            params={
                "model": self.vertex_service.get_chatmodel(),
                SYSTEM: self._get_research_planning_system_prompt(),
                USER: [self._get_research_planning_user_prompt()],
                ENABLE_STREAM: stream_mode,
            },
        )

        # 3. 信息收集顶点
        information_collection = LLMVertex(
            id="information_collection",
            params={
                "model": self.vertex_service.get_chatmodel(),
                SYSTEM: self._get_information_collection_system_prompt(),
                USER: [self._get_information_collection_user_prompt()],
                ENABLE_STREAM: stream_mode,
            },
        )

        # 4. 深度分析顶点
        deep_analysis = LLMVertex(
            id="deep_analysis",
            params={
                "model": self.vertex_service.get_chatmodel(),
                SYSTEM: self._get_deep_analysis_system_prompt(),
                USER: [self._get_deep_analysis_user_prompt()],
                ENABLE_STREAM: stream_mode,
            },
        )

        # 5. 交叉验证顶点
        cross_validation = LLMVertex(
            id="cross_validation",
            params={
                "model": self.vertex_service.get_chatmodel(),
                SYSTEM: self._get_cross_validation_system_prompt(),
                USER: [self._get_cross_validation_user_prompt()],
                ENABLE_STREAM: stream_mode,
            },
        )

        # 6. 总结报告顶点
        summary_report = LLMVertex(
            id="summary_report",
            params={
                "model": self.vertex_service.get_chatmodel(),
                SYSTEM: self._get_summary_report_system_prompt(),
                USER: [self._get_summary_report_user_prompt()],
                ENABLE_STREAM: stream_mode,
            },
        )

        # 创建汇聚顶点
        sink = SinkVertex(
            id="sink",
            task=lambda inputs, context: {
                "final_report": inputs.get("summary_report", ""),
                "message": "深度研究工作流执行完成",
                "research_topic": research_topic,
            },
        )

        # 添加所有顶点到工作流
        workflow.add_vertex(source)
        workflow.add_vertex(topic_analysis)
        workflow.add_vertex(research_planning)
        workflow.add_vertex(information_collection)
        workflow.add_vertex(deep_analysis)
        workflow.add_vertex(cross_validation)
        workflow.add_vertex(summary_report)
        workflow.add_vertex(sink)

        # 连接顶点形成工作流管道
        source | topic_analysis
        topic_analysis | research_planning
        research_planning | information_collection
        information_collection | deep_analysis
        deep_analysis | cross_validation
        cross_validation | summary_report
        summary_report | sink

        logger.info(f"深度研究工作流创建完成，研究主题：{research_topic}")
        return workflow

    def _get_topic_analysis_system_prompt(self) -> str:
        """主题分析阶段的系统提示词"""
        return """
你是一位专业的研究分析师。你的任务是对用户提供的研究主题进行深入分析，确定研究范围、关键问题和研究方向。

请按照以下结构进行分析：
1. 主题概述：简要描述研究主题的核心内容
2. 研究范围：明确研究的边界和重点领域
3. 关键问题：列出3-5个需要深入探讨的核心问题
4. 研究维度：从技术、商业、社会、伦理等多个角度分析
5. 预期挑战：识别研究过程中可能遇到的困难

请提供详细、专业的分析报告。
        """.strip()

    def _get_topic_analysis_user_prompt(self) -> str:
        """主题分析阶段的用户提示词"""
        return """
请对以下研究主题进行深入分析：

研究主题：{{source.research_topic}}

请提供详细的主题分析报告。
        """.strip()

    def _get_research_planning_system_prompt(self) -> str:
        """研究规划阶段的系统提示词"""
        return """
你是一位经验丰富的研究方法专家。基于前面的主题分析，你需要制定一个详细的研究计划。

请按照以下结构制定研究计划：
1. 研究目标：明确具体的研究目标和预期成果
2. 研究方法：选择合适的研究方法和工具
3. 信息来源：确定可靠的信息来源和数据渠道
4. 研究步骤：制定详细的研究执行步骤
5. 时间安排：估算各阶段所需时间
6. 质量控制：确保研究质量的措施

请提供完整、可执行的研究计划方案。
        """.strip()

    def _get_research_planning_user_prompt(self) -> str:
        """研究规划阶段的用户提示词"""
        return """
基于以下主题分析结果，请制定详细的研究计划：

{{topic_analysis}}

请提供完整的研究计划方案。
        """.strip()

    def _get_information_collection_system_prompt(self) -> str:
        """信息收集阶段的系统提示词"""
        return """
你是一位专业的信息收集专家。你需要根据研究计划，系统性地收集和整理相关信息。

请按照以下结构进行信息收集：
1. 基础信息：收集主题的基本概念、定义和背景
2. 历史发展：梳理主题的发展历程和重要里程碑
3. 现状分析：分析当前的发展状况和主要特点
4. 技术细节：深入了解相关技术原理和实现方式
5. 市场情况：分析市场规模、竞争格局和商业模式
6. 案例研究：收集典型案例和成功实践
7. 专家观点：整理行业专家和学者的观点

请提供详细、全面的信息收集报告。
        """.strip()

    def _get_information_collection_user_prompt(self) -> str:
        """信息收集阶段的用户提示词"""
        return """
根据以下研究计划，请进行系统性的信息收集：

{{research_planning}}

请提供详细的信息收集报告。
        """.strip()

    def _get_deep_analysis_system_prompt(self) -> str:
        """深度分析阶段的系统提示词"""
        return """
你是一位资深的分析专家。你需要对收集的信息进行深度分析，提供独到的洞察和见解。

请按照以下结构进行深度分析：
1. 趋势分析：识别发展趋势和变化模式
2. 关联分析：分析不同因素之间的关联关系
3. 优势劣势：分析主题的优势、劣势、机会和威胁
4. 技术评估：评估技术成熟度和发展潜力
5. 风险评估：识别潜在风险和挑战
6. 影响分析：分析对相关行业和社会的影响
7. 创新机会：识别创新点和发展机会
8. 深层洞察：提供独特的分析视角和见解

请提供深入、有价值的分析报告和洞察。
        """.strip()

    def _get_deep_analysis_user_prompt(self) -> str:
        """深度分析阶段的用户提示词"""
        return """
基于以下收集的信息，请进行深度分析：

{{information_collection}}

请提供深入的分析报告和洞察。
        """.strip()

    def _get_cross_validation_system_prompt(self) -> str:
        """交叉验证阶段的系统提示词"""
        return """
你是一位严谨的验证专家。你需要对前面的分析结果进行交叉验证，确保结论的准确性和可靠性。

请按照以下结构进行交叉验证：
1. 事实核查：验证关键事实和数据的准确性
2. 逻辑检验：检查分析逻辑的合理性和一致性
3. 多角度验证：从不同角度验证结论的可靠性
4. 反驳论证：考虑可能的反驳观点和替代解释
5. 证据强度：评估支撑结论的证据强度
6. 不确定性：识别分析中的不确定性和局限性
7. 修正建议：提出需要修正或补充的内容

请提供严谨、客观的验证报告和修正建议。
        """.strip()

    def _get_cross_validation_user_prompt(self) -> str:
        """交叉验证阶段的用户提示词"""
        return """
请对以下深度分析结果进行交叉验证：

{{deep_analysis}}

请提供验证报告和修正建议。
        """.strip()

    def _get_summary_report_system_prompt(self) -> str:
        """总结报告阶段的系统提示词"""
        return """
你是一位专业的报告撰写专家。你需要整合前面所有的研究成果，撰写一份完整、专业的研究总结报告。

请按照以下结构撰写报告：
1. 执行摘要：简要概述研究目的、方法和主要发现
2. 研究背景：介绍研究主题的背景和重要性
3. 研究方法：说明采用的研究方法和过程
4. 主要发现：详细阐述研究的主要发现和结论
5. 深度洞察：提供独特的分析视角和见解
6. 实践建议：基于研究结果提出实用的建议
7. 风险提示：指出潜在的风险和注意事项
8. 未来展望：预测未来的发展趋势和机会
9. 研究局限：说明研究的局限性和改进方向
10. 参考资料：列出主要的信息来源和参考资料

请撰写专业、完整、有价值的研究总结报告。
        """.strip()

    def _get_summary_report_user_prompt(self) -> str:
        """总结报告阶段的用户提示词"""
        return """
请基于以下所有研究成果，撰写完整的研究总结报告：

原始主题：{{source.research_topic}}

主题分析：{{topic_analysis}}

研究规划：{{research_planning}}

信息收集：{{information_collection}}

深度分析：{{deep_analysis}}

交叉验证：{{cross_validation}}

请提供专业、完整的研究总结报告。
        """.strip()


def create_deep_research_workflow(vertex_service):
    """创建深度研究工作流的工厂函数

    Args:
        vertex_service: VertexFlow服务实例

    Returns:
        function: 返回工作流构建函数
    """
    workflow_builder = DeepResearchWorkflow(vertex_service)

    def build_workflow(input_data: Dict[str, Any]) -> Workflow:
        """构建工作流的函数

        Args:
            input_data: 输入数据，包含研究主题等信息

        Returns:
            Workflow: 配置好的深度研究工作流
        """
        return workflow_builder.create_workflow(input_data)

    return build_workflow


# 导出主要类和函数
__all__ = [
    "DeepResearchWorkflow",
    "create_deep_research_workflow",
]
