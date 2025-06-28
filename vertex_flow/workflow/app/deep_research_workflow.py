#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度研究工作流模块

本模块实现了一个完整的自动化深度研究分析工作流，包含六个主要阶段：
1. 主题分析：对研究主题进行深入分析，确定研究范围和关键问题
2. 分析框架制定：为自动化研究流程制定分析框架和策略
3. 信息收集与初步分析：使用Web搜索工具收集信息并进行初步分析
4. 深度分析：对收集的信息进行深入分析和处理
5. 交叉验证：验证分析结果的准确性和可靠性
6. 综合分析报告：生成完整的综合分析报告并保存为文件

工作流特点：
- 专注于自动化分析而非人工操作指导
- 每个阶段都有专门的系统提示词和用户提示词
- 支持流式输出，实时显示分析进展
- 集成Web搜索工具，获取最新信息
- 可配置保存每个阶段的中间结果和最终报告
- 包含时间信息，确保分析的时效性
- 使用LLMVertex的postprocess机制保存中间结果
- 使用常量替代魔法字符串，提高代码可维护性
- 支持用户自定义是否保存中间文档和最终报告文档
- 生成的是分析洞察而非操作计划
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import (
    ENABLE_SEARCH_KEY,
    ENABLE_STREAM,
    LOCAL_VAR,
    POSTPROCESS,
    SOURCE_SCOPE,
    SOURCE_VAR,
    STAGE_CROSS_VALIDATION,
    STAGE_DEEP_ANALYSIS,
    STAGE_INFORMATION_COLLECTION,
    STAGE_RESEARCH_PLANNING,
    STAGE_TOPIC_ANALYSIS,
    SYSTEM,
    USER,
)
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.workflow import FunctionVertex, LLMVertex, SinkVertex, SourceVertex, Workflow

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
                - content: 研究主题
                - stream: 是否启用流式输出
                - save_intermediate: 是否保存中间文档，默认True
                - save_final_report: 是否保存最终报告文档，默认True

        Returns:
            Workflow: 配置好的工作流实例
        """
        logger.info(f"开始创建深度研究工作流, {input_data}...")
        # 创建工作流上下文
        context = WorkflowContext(
            env_parameters=input_data.get("env_vars", {}), user_parameters=input_data.get("user_vars", {})
        )

        # 创建工作流
        workflow = Workflow(context)

        # 获取研究主题和配置参数
        research_topic = input_data.get("content", "")
        stream_mode = input_data.get("stream", False)
        save_intermediate = input_data.get("save_intermediate", True)
        save_final_report = input_data.get("save_final_report", True)

        logger.info(f"开始深度研究，研究主题：{research_topic}")
        logger.info(
            f"配置参数 - stream mode {stream_mode}, 保存中间文档：{save_intermediate}，保存最终报告：{save_final_report}"
        )

        # 创建源顶点
        source = SourceVertex(
            id="source",
            task=lambda inputs, context: {
                "research_topic": inputs.get("content", research_topic),
                "message": f"开始深度研究：{inputs.get('content', research_topic)}",
            },
        )

        # 1. 主题分析顶点
        topic_analysis_params = {
            "model": self.vertex_service.get_chatmodel(),
            SYSTEM: self._get_topic_analysis_system_prompt(),
            USER: [self._get_topic_analysis_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.8,  # 提高创造性，获得更丰富的分析
            "max_tokens": 8192,  # 增加输出长度限制
        }
        if save_intermediate:
            topic_analysis_params[POSTPROCESS] = lambda content, inputs, context: self._postprocess_with_save(
                content, inputs, context, STAGE_TOPIC_ANALYSIS
            )

        topic_analysis = LLMVertex(
            id="topic_analysis",
            params=topic_analysis_params,
        )

        # 2. 研究规划顶点
        research_planning_params = {
            "model": self.vertex_service.get_chatmodel(),
            SYSTEM: self._get_research_planning_system_prompt(),
            USER: [self._get_research_planning_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.7,  # 平衡创造性和准确性
            "max_tokens": 6144,  # 增加输出长度
        }
        if save_intermediate:
            research_planning_params[POSTPROCESS] = lambda content, inputs, context: self._postprocess_with_save(
                content, inputs, context, STAGE_RESEARCH_PLANNING
            )

        research_planning = LLMVertex(
            id="research_planning",
            params=research_planning_params,
        )

        # 3. 信息收集顶点（集成Web搜索工具）
        information_collection_params = {
            "model": self.vertex_service.get_chatmodel(),
            SYSTEM: self._get_information_collection_system_prompt(),
            USER: [self._get_information_collection_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.6,  # 保持准确性，适度创新
            "max_tokens": 8192,  # 信息收集需要更多空间
            ENABLE_SEARCH_KEY: True,
        }
        if save_intermediate:
            information_collection_params[POSTPROCESS] = lambda content, inputs, context: self._postprocess_with_save(
                content, inputs, context, STAGE_INFORMATION_COLLECTION
            )

        information_collection = LLMVertex(
            id="information_collection",
            params=information_collection_params,
            # - - 贵，有选择使用。
            # tools= [self.vertex_service.get_web_search_tool()]
            tools=[self.vertex_service.get_finance_tool()],
        )

        # 4. 深度分析顶点
        deep_analysis_params = {
            "model": self.vertex_service.get_chatmodel(),
            SYSTEM: self._get_deep_analysis_system_prompt(),
            USER: [self._get_deep_analysis_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.8,  # 提高创造性，深度分析需要更多洞察
            "max_tokens": 8192,  # 深度分析需要最多的输出空间
        }
        if save_intermediate:
            deep_analysis_params[POSTPROCESS] = lambda content, inputs, context: self._postprocess_with_save(
                content, inputs, context, STAGE_DEEP_ANALYSIS
            )

        deep_analysis = LLMVertex(
            id="deep_analysis",
            params=deep_analysis_params,
        )

        # 5. 交叉验证顶点
        cross_validation_params = {
            "model": self.vertex_service.get_chatmodel(),
            SYSTEM: self._get_cross_validation_system_prompt(),
            USER: [self._get_cross_validation_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.5,  # 验证阶段需要更严谨
            "max_tokens": 8192,  # 验证报告需要详细说明
        }
        if save_intermediate:
            cross_validation_params[POSTPROCESS] = lambda content, inputs, context: self._postprocess_with_save(
                content, inputs, context, STAGE_CROSS_VALIDATION
            )

        cross_validation = LLMVertex(
            id="cross_validation",
            params=cross_validation_params,
        )

        # 6. 总结报告顶点
        summary_report = LLMVertex(
            id="summary_report",
            params={
                "model": self.vertex_service.get_chatmodel(),
                SYSTEM: self._get_summary_report_system_prompt(),
                USER: [self._get_summary_report_user_prompt()],
                ENABLE_STREAM: stream_mode,
                "temperature": 0.7,  # 平衡创造性和准确性
                "max_tokens": 8192,  # 最终报告需要最大的输出空间
            },
        )

        # 配置summary_report顶点的变量依赖关系
        summary_report.add_variables(
            [
                {
                    SOURCE_SCOPE: "topic_analysis",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "topic_analysis",
                },
                {
                    SOURCE_SCOPE: "research_planning",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "research_planning",
                },
                {
                    SOURCE_SCOPE: "information_collection",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "information_collection",
                },
                {
                    SOURCE_SCOPE: "deep_analysis",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "deep_analysis",
                },
                {
                    SOURCE_SCOPE: "cross_validation",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "cross_validation",
                },
            ]
        )

        # 7. 文件保存顶点（可选）
        file_save = None
        if save_final_report:
            file_save = FunctionVertex(
                id="file_save",
                task=self._save_report_to_file,
                variables=[
                    {
                        SOURCE_SCOPE: "summary_report",
                        SOURCE_VAR: None,
                        LOCAL_VAR: "summary_report",
                    }
                ],
            )

        # 创建汇聚顶点
        if save_final_report:
            sink = SinkVertex(
                id="sink",
                task=lambda inputs, context: {
                    "final_report": inputs.get("summary_report", ""),
                    "file_path": inputs.get("file_path", ""),
                    "message": "深度研究工作流执行完成，报告已保存到文件",
                    "research_topic": research_topic,
                },
            )
        else:
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
        if save_final_report and file_save:
            workflow.add_vertex(file_save)
        workflow.add_vertex(sink)

        # 连接顶点形成工作流管道
        source | topic_analysis
        topic_analysis | research_planning
        research_planning | information_collection
        information_collection | deep_analysis
        deep_analysis | cross_validation
        cross_validation | summary_report

        # 根据配置决定最后的连接
        if save_final_report and file_save:
            summary_report | file_save
            file_save | sink
        else:
            summary_report | sink

        logger.info(f"深度研究工作流创建完成，研究主题：{research_topic}")
        return workflow

    def _get_topic_analysis_system_prompt(self) -> str:
        """主题分析阶段的系统提示词"""
        current_date = datetime.now().strftime("%Y年%m月%d日")
        return f"""
你是一位专业的研究分析师。你的任务是对用户提供的研究主题进行深入分析，确定研究范围、关键问题和研究方向。

**重要信息：今天是{current_date}**

请按照以下结构进行分析：
1. 主题概述：简要描述研究主题的核心内容
2. 研究范围：明确研究的边界和重点领域
3. 关键问题：列出3-5个需要深入探讨的核心问题
4. 研究维度：从技术、商业、社会、伦理等多个角度分析
5. 预期挑战：识别研究过程中可能遇到的困难
6. 时效性考虑：考虑当前时间点对研究主题的影响和意义

请提供详细、专业的分析报告，特别关注当前时间背景下的研究价值和紧迫性。
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
        current_date = datetime.now().strftime("%Y年%m月%d日")
        return f"""
你是一位经验丰富的研究分析专家。基于前面的主题分析，你需要为后续的自动化研究流程制定分析框架和研究策略。

**重要信息：今天是{current_date}**

请按照以下结构制定研究分析框架：
1. 研究目标：明确本次自动化研究要达成的具体分析目标
2. 分析维度：确定需要从哪些角度进行深入分析（技术、市场、趋势、影响等）
3. 关键信息点：列出需要重点收集和分析的核心信息类型
4. 搜索策略：制定web搜索的关键词策略和信息筛选标准
5. 分析方法：确定适用的分析方法和评估框架
6. 验证要点：明确需要交叉验证的关键结论和数据
7. 时效性重点：确定需要特别关注的时间敏感信息，重点关注{current_date}前后的最新发展

请提供完整的自动化研究分析框架，为后续的信息收集、深度分析和交叉验证阶段提供明确的指导方向。
        """.strip()

    def _get_research_planning_user_prompt(self) -> str:
        """研究规划阶段的用户提示词"""
        return """
基于以下主题分析结果，请制定详细的自动化研究分析框架：

{{topic_analysis}}

请提供完整的研究分析框架，为后续的自动化分析流程提供指导。
        """.strip()

    def _get_information_collection_system_prompt(self) -> str:
        """信息收集阶段的系统提示词"""
        current_date = datetime.now().strftime("%Y年%m月%d日")
        return f"""
你是一位专业的信息收集和初步分析专家。你需要根据研究分析框架，系统性地收集相关信息并进行初步分析。

**重要信息：今天是{current_date}**

**信息收集要求：请提供详细、全面、深入的信息收集报告，每个部分都要有充实的内容和具体的信息。**

请按照以下结构进行信息收集和初步分析，每个部分都要提供详细的信息：

## 1. 基础概念梳理（要求：至少800字）
- 明确核心概念、定义和范围边界
- 提供权威定义和多角度解释
- 分析概念的演进和发展
- 识别相关术语和概念体系

## 2. 历史发展脉络（要求：至少1000字）
- 梳理主题的发展历程和重要里程碑
- 识别发展规律和阶段特征
- 分析关键转折点和推动因素
- 构建完整的时间线和发展图谱

## 3. 现状全景分析（要求：至少1200字）
- 分析当前的发展状况、主要特点和关键参与者
- 提供具体的数据和统计信息
- 分析市场格局和竞争态势
- 识别主要玩家和利益相关者

## 4. 技术深度解析（要求：至少1000字）
- 深入了解相关技术原理、实现方式和技术趋势
- 分析技术架构和核心组件
- 对比不同技术路线的优劣
- 预测技术发展方向

## 5. 市场生态分析（要求：至少1000字）
- 分析市场规模、竞争格局、商业模式和价值链
- 提供具体的市场数据和预测
- 分析商业模式的创新和演进
- 识别价值链的关键环节

## 6. 典型案例研究（要求：至少1000字）
- 收集和分析典型案例、成功实践和失败教训
- 提供详细的案例分析和经验总结
- 识别成功因素和失败原因
- 提取可复制的经验和教训

## 7. 专家观点汇总（要求：至少800字）
- 整理行业专家、学者和意见领袖的观点和预测
- 分析不同观点的分歧和共识
- 识别权威声音和前沿观点
- 总结专家预测和建议

## 8. 最新动态追踪（要求：至少800字）
- 通过web搜索获取最新的相关新闻、研究成果和发展动态
- 特别关注{current_date}前后的最新信息
- 分析最新趋势和变化
- 识别重要事件和发展信号

**信息收集要求：**
1. 每个部分都必须有具体的信息和数据，不能只是概述
2. 主动使用web_search工具搜索相关关键词
3. 确保信息的时效性和全面性
4. 对收集到的信息进行分类、整理和关联分析
5. 总字数不少于6000字
6. 引用具体的来源和数据支撑

请提供详细、全面的信息收集和初步分析报告。
        """.strip()

    def _get_information_collection_user_prompt(self) -> str:
        """信息收集阶段的用户提示词"""
        return """
根据以下研究分析框架，请进行系统性的信息收集和初步分析：

{{research_planning}}

请提供详细的信息收集和初步分析报告。
        """.strip()

    def _get_deep_analysis_system_prompt(self) -> str:
        """深度分析阶段的系统提示词"""
        current_date = datetime.now().strftime("%Y年%m月%d日")
        return f"""
你是一位资深的分析专家。你需要对收集的信息进行深度分析，提供独到的洞察和见解。

**重要信息：今天是{current_date}**

**分析要求：请提供详细、具体、深入的分析，每个部分都要有充实的内容，避免空洞的概述。**

请按照以下结构进行深度分析，每个部分都要提供详细的分析内容：

## 1. 趋势分析（要求：至少1000字）
- 识别发展趋势和变化模式，特别关注当前时间点的趋势特征
- 提供具体的数据支撑和案例说明
- 分析短期、中期、长期趋势的不同特点
- 对比历史趋势与当前趋势的异同

## 2. 关联分析（要求：至少800字）
- 深入分析不同因素之间的关联关系
- 识别因果关系和相关性
- 分析内部因素和外部环境的相互影响
- 构建关联关系图谱

## 3. SWOT深度分析（要求：至少1200字）
- **优势(Strengths)**：详细分析内在优势，提供具体例证
- **劣势(Weaknesses)**：深入剖析内在劣势和不足
- **机会(Opportunities)**：识别外部机会，分析可行性
- **威胁(Threats)**：分析外部威胁和挑战，评估影响程度

## 4. 技术评估（要求：至少1000字）
- 评估技术成熟度和发展潜力
- 分析技术路线图和演进路径
- 对比不同技术方案的优劣
- 预测技术发展的关键节点

## 5. 风险评估（要求：至少800字）
- 识别潜在风险和挑战
- 评估风险发生概率和影响程度
- 提供风险应对策略和建议
- 分析风险的时间敏感性

## 6. 影响分析（要求：至少1000字）
- 分析对相关行业和社会的影响
- 量化影响程度和范围
- 分析正面影响和负面影响
- 预测长期影响和连锁反应

## 7. 创新机会（要求：至少800字）
- 识别创新点和发展机会
- 分析创新的可行性和价值
- 提供具体的创新建议
- 评估创新的风险和回报

## 8. 时间敏感性分析（要求：至少600字）
- 分析时间因素对主题发展的影响
- 识别关键时间窗口和节点
- 分析时机的重要性

## 9. 深层洞察（要求：至少1000字）
- 提供独特的分析视角和见解
- 挑战传统观点或提供新的理解框架
- 基于数据和事实的原创性思考
- 跨领域的关联分析和启发

**输出要求：**
1. 每个分析部分都必须有具体的内容，不能只是概述
2. 引用具体的数据、案例和专家观点来支撑分析
3. 保持逻辑清晰，论证充分
4. 总字数不少于8000字
5. 特别关注当前时间背景下的分析价值

请提供深入、详细、有价值的分析报告和洞察。
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
        current_date = datetime.now().strftime("%Y年%m月%d日")
        return f"""
你是一位严谨的验证专家。你需要对前面的分析结果进行交叉验证，确保结论的准确性和可靠性。

**重要信息：今天是{current_date}**

请按照以下结构进行交叉验证：
1. 事实核查：验证关键事实和数据的准确性，特别关注时效性
2. 逻辑检验：检查分析逻辑的合理性和一致性
3. 多角度验证：从不同角度验证结论的可靠性
4. 反驳论证：考虑可能的反驳观点和替代解释
5. 证据强度：评估支撑结论的证据强度
6. 时效性验证：验证信息的时效性和当前相关性
7. 不确定性：识别分析中的不确定性和局限性
8. 修正建议：提出需要修正或补充的内容

请提供严谨、客观的验证报告和修正建议，确保分析结果在当前时间背景下的准确性。
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
        current_date = datetime.now().strftime("%Y年%m月%d日")
        return f"""
你是一位专业的报告撰写专家。你需要整合前面所有的研究成果，撰写一份完整、专业的研究报告。

**重要信息：今天是{current_date}**

请按照以下结构撰写详细的研究报告：

## 1. 执行摘要
- 研究目的和背景
- 采用的研究方法
- 主要发现和核心结论
- 关键建议和行动要点

## 2. 研究背景与意义
- 研究主题的背景介绍
- 研究的重要性和必要性
- 当前时间点的研究价值
- 研究范围和边界

## 3. 研究方法与过程
- 详细说明采用的研究方法
- 信息收集的来源和渠道
- 分析框架和验证方法
- 研究过程中的关键步骤

## 4. 主要发现与分析
### 4.1 基础信息发现
- 从主题分析中得出的核心发现
- 关键概念和定义的澄清
- 研究范围内的重要事实

### 4.2 深度分析结果
- 趋势分析的主要发现
- SWOT分析结果
- 技术评估和风险评估结果
- 影响分析和创新机会识别

### 4.3 信息收集成果
- 从web搜索获得的最新信息
- 历史发展脉络梳理
- 现状分析和市场情况
- 专家观点和案例研究总结

## 5. 深度洞察与独特观点
- 基于综合分析的独特见解
- 跨领域的关联分析
- 未被广泛认知的重要发现
- 对传统观点的挑战或验证

## 6. 发展建议与策略方向
### 6.1 技术发展建议
### 6.2 市场策略建议
### 6.3 风险应对建议
### 6.4 创新机会建议

## 7. 风险分析与挑战识别
- 主要风险因素识别
- 风险等级评估
- 潜在挑战分析
- 风险影响评估

## 8. 未来发展趋势与机会
- 基于当前分析的趋势预测
- 潜在的发展机会
- 技术演进路径
- 市场发展前景

## 9. 研究局限性与改进方向
- 当前研究的局限性
- 数据和信息的不足之处
- 未来研究的改进方向
- 需要进一步验证的假设

## 10. 结论与总结
- 研究的核心结论
- 对原始研究问题的回答
- 研究成果的价值和意义
- 对相关领域的贡献

## 11. 附录
- 主要信息来源和参考资料
- 关键数据和图表
- 专业术语解释
- 相关链接和资源

**撰写要求：**
1. 充分利用前面各阶段的分析成果，确保内容的连贯性和完整性
2. 每个部分都要有具体的分析内容，避免空洞的概述
3. 引用具体的数据、案例和专家观点来支撑分析结论
4. 保持客观、专业的分析风格
5. 确保报告的分析深度和洞察价值
6. 特别关注时效性，体现{current_date}这个时间点的分析价值
7. **总字数要求不少于15000字，确保每个章节都有充实详细的内容**
8. **每个主要章节至少1000字，重要章节（如主要发现与分析）至少2000字**
9. **提供具体的数据、图表说明、案例分析和专家引用**
10. **确保分析的深度和广度，避免浅层次的描述**

请撰写详细、专业、有价值的综合分析报告，确保每个章节都有充实的分析内容。
        """.strip()

    def _save_intermediate_result(self, stage_name: str, content: str, research_topic: str = "") -> str:
        """保存中间结果到文件

        Args:
            stage_name: 阶段名称
            content: 内容
            research_topic: 研究主题

        Returns:
            str: 文件路径
        """
        try:
            # 生成文件名
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            if research_topic:
                clean_topic = re.sub(r'[<>:"/\\|?*]', "_", research_topic)
                clean_topic = clean_topic.strip()[:30]  # 限制长度
                filename = f"{stage_name}_{clean_topic}_{current_time}.md"
            else:
                filename = f"{stage_name}_{current_time}.md"

            # 确保中间结果目录存在
            intermediate_dir = "reports/intermediate"
            if not os.path.exists(intermediate_dir):
                os.makedirs(intermediate_dir)

            # 完整文件路径
            file_path = os.path.join(intermediate_dir, filename)

            # 准备markdown内容
            markdown_content = f"""# {stage_name}阶段结果

**研究主题**: {research_topic if research_topic else '未指定'}
**生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**阶段**: {stage_name}

---

{content}

---

*本结果由VertexFlow深度研究工作流自动生成*
"""

            # 保存文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            logger.info(f"{stage_name}阶段结果已保存到文件: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"保存{stage_name}阶段结果时发生错误: {str(e)}")
            return ""

    def _postprocess_with_save(
        self, content: str, inputs: Dict[str, Any], context: WorkflowContext, stage_name: str
    ) -> str:
        """LLMVertex的postprocess函数，保存中间结果并返回原始内容

        Args:
            content: LLM生成的内容
            inputs: 输入数据
            context: 工作流上下文
            stage_name: 阶段名称

        Returns:
            str: 原始内容（不修改）
        """
        try:
            # 获取研究主题
            research_topic = ""
            if hasattr(context, "outputs") and "source" in context.outputs:
                source_data = context.outputs["source"]
                if isinstance(source_data, dict):
                    research_topic = source_data.get("research_topic", "")

            # 保存中间结果
            self._save_intermediate_result(stage_name, content, research_topic)

            # 返回原始内容，不做任何修改
            return content

        except Exception as e:
            logger.error(f"保存{stage_name}阶段结果时发生错误: {str(e)}")
            # 即使保存失败，也要返回原始内容
            return content

    def _save_report_to_file(self, inputs: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        """保存研究报告到markdown文件

        Args:
            inputs: 输入数据，包含summary_report
            context: 工作流上下文

        Returns:
            Dict: 包含文件路径和保存状态的结果
        """
        try:
            # 获取报告内容
            report_content = inputs.get("summary_report", "")
            if not report_content:
                logger.warning("报告内容为空，无法保存文件")
                return {"file_path": "", "success": False, "message": "报告内容为空"}

            # 从源数据获取研究主题
            research_topic = ""
            if hasattr(context, "outputs") and "source" in context.outputs:
                source_data = context.outputs["source"]
                if isinstance(source_data, dict):
                    research_topic = source_data.get("research_topic", "")

            # 生成文件名（清理特殊字符）
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            if research_topic:
                # 清理文件名中的特殊字符
                clean_topic = re.sub(r'[<>:"/\\|?*]', "_", research_topic)
                clean_topic = clean_topic.strip()[:50]  # 限制长度
                filename = f"深度研究报告_{clean_topic}_{current_time}.md"
            else:
                filename = f"深度研究报告_{current_time}.md"

            # 确保reports目录存在
            reports_dir = "reports"
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)

            # 完整文件路径
            file_path = os.path.join(reports_dir, filename)

            # 准备markdown内容
            markdown_content = f"""# 深度研究报告

**研究主题**: {research_topic if research_topic else '未指定'}
**生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

---

{report_content}

---

*本报告由VertexFlow深度研究工作流自动生成*
"""

            # 保存文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            logger.info(f"研究报告已保存到文件: {file_path}")

            return {
                "file_path": file_path,
                "success": True,
                "message": f"报告已成功保存到 {file_path}",
                "summary_report": report_content,  # 传递报告内容给下一个节点
            }

        except Exception as e:
            logger.error(f"保存报告文件时发生错误: {str(e)}")
            return {
                "file_path": "",
                "success": False,
                "message": f"保存文件失败: {str(e)}",
                # 即使保存失败也传递报告内容
                "summary_report": inputs.get("summary_report", ""),
            }

    def _get_summary_report_user_prompt(self) -> str:
        """总结报告阶段的用户提示词"""
        return """
请基于以下所有分析成果，撰写完整的综合分析报告：

原始主题：{{source.research_topic}}

主题分析：{{topic_analysis}}

分析框架：{{research_planning}}

信息收集与初步分析：{{information_collection}}

深度分析：{{deep_analysis}}

交叉验证：{{cross_validation}}

请提供专业、完整的综合分析报告。
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
