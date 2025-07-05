#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度研究工作流模块

本模块实现了一个完整的自动化深度研究分析工作流，包含五个主要阶段：
1. 主题分析：对研究主题进行深入分析，确定研究范围和关键问题
2. 分析框架制定：为自动化研究流程制定分析框架和策略
3. 步骤化分析执行：根据分析计划循环执行各个分析步骤（包含信息收集）
4. 深度分析：对收集的信息进行深入分析和处理
5. 交叉验证：验证分析结果的准确性和可靠性
6. 综合分析报告：生成完整的综合分析报告并保存为文件

工作流特点：
- 专注于自动化分析而非人工操作指导
- 每个阶段都有专门的系统提示词和用户提示词
- 支持流式输出，实时显示分析进展
- 信息收集功能集成在步骤循环中，支持Web搜索工具
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

from vertex_flow.prompts.deep_research import DeepResearchPrompts
from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.app.analysis_plan_parser import parse_analysis_plan
from vertex_flow.workflow.constants import (
    ENABLE_SEARCH_KEY,
    ENABLE_STREAM,
    ITERATION_INDEX_KEY,
    LOCAL_VAR,
    POSTPROCESS,
    SOURCE_SCOPE,
    SOURCE_VAR,
    STAGE_CROSS_VALIDATION,
    STAGE_DEEP_ANALYSIS,
    STAGE_TOPIC_ANALYSIS,
    SUBGRAPH_SOURCE,
    SYSTEM,
    USER,
)
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex import WhileVertex, WhileVertexGroup
from vertex_flow.workflow.workflow import FunctionVertex, LLMVertex, SinkVertex, SourceVertex, Workflow

logger = LoggerUtil.get_logger()


class DeepResearchWorkflow:
    """深度研究工作流类"""

    def __init__(self, vertex_service, model=None, language="en"):
        self.vertex_service = vertex_service
        self.model = model  # 添加模型参数
        self.language = language  # 添加语言参数
        self.workflow_name = "deep-research"
        self.description = "Deep Research Workflow for comprehensive topic analysis and investigation"
        self.prompts = DeepResearchPrompts(language=language)  # 传入语言参数

    def create_workflow(self, input_data: Dict[str, Any]) -> Workflow:
        """创建深度研究工作流

        Args:
            input_data: 包含研究主题和其他参数的输入数据
                - content: 研究主题
                - stream: 是否启用流式输出
                - save_intermediate: 是否保存中间文档，默认True
                - save_final_report: 是否保存最终报告文档，默认True
                - language: 语言选择，"en"为英文，"zh"为中文，默认"en"

        Returns:
            Workflow: 配置好的工作流实例
        """
        logger.info(f"开始创建深度研究工作流, {input_data}...")

        # 获取语言设置，优先使用输入数据中的语言，否则使用实例默认语言
        language = input_data.get("language", self.language)
        self.prompts.set_language(language)  # 更新提示词语言

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
            f"配置参数 - stream mode {stream_mode}, 保存中间文档：{save_intermediate}，保存最终报告：{save_final_report}，语言：{language}"
        )

        # 获取要使用的模型，优先使用传入的模型，否则使用服务默认模型
        model_to_use = self.model if self.model else self.vertex_service.get_chatmodel()
        logger.info(f"使用模型: {model_to_use}")

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
            "model": model_to_use,  # 使用指定的模型
            SYSTEM: self.prompts.get_topic_analysis_system_prompt(),
            USER: [self.prompts.get_topic_analysis_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.8,  # 提高创造性，获得更丰富的分析
            "max_tokens": 8192,  # 增加输出长度限制
            ENABLE_SEARCH_KEY: True,
        }
        if save_intermediate:
            topic_analysis_params[POSTPROCESS] = lambda content, inputs, context: self._postprocess_with_save(
                content, inputs, context, STAGE_TOPIC_ANALYSIS
            )

        topic_analysis = LLMVertex(
            id="topic_analysis",
            task=None,
            params=topic_analysis_params,
            variables=[
                {SOURCE_SCOPE: "source", SOURCE_VAR: "research_topic", LOCAL_VAR: "research_topic"},
            ],
        )

        # 2. 分析计划顶点（输出JSON分析计划）
        analysis_plan_params = {
            "model": model_to_use,
            SYSTEM: self.prompts.get_analysis_plan_system_prompt(),
            USER: [self.prompts.get_analysis_plan_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.7,
            "max_tokens": 2048,
            ENABLE_SEARCH_KEY: False,
        }
        analysis_plan = LLMVertex(
            id="analysis_plan",
            task=None,
            params=analysis_plan_params,
            variables=[
                {SOURCE_SCOPE: "source", SOURCE_VAR: "research_topic", LOCAL_VAR: "research_topic"},
            ],
        )

        # 3. 分析计划解析器（提取steps）
        def extract_steps_task(inputs, context):
            plan_json = inputs.get("analysis_plan", "")
            logger.info(f"收到分析计划数据: {type(plan_json)}, 长度: {len(str(plan_json))}")
            try:
                # 尝试解析JSON格式的分析计划
                steps = parse_analysis_plan(plan_json)
                logger.info(f"成功解析分析计划，提取到 {len(steps)} 个步骤, 类型: {type(steps)}")
                # 确保steps为list，否则强制转为list
                if not isinstance(steps, list):
                    logger.warning(f"parse_analysis_plan返回的steps不是list，实际类型: {type(steps)}，尝试强制转换")
                    steps = list(steps) if isinstance(steps, (tuple, set)) else [steps]
                return {"steps": steps, "step_index": 0}
            except Exception as e:
                logger.warning(f"解析分析计划JSON失败: {e}")
                # 如果JSON解析失败，使用默认分析计划
                research_topic = context.get_variable("research_topic", "未知主题")
                logger.info(f"为研究主题 '{research_topic}' 创建默认分析计划")
                from vertex_flow.workflow.app.analysis_plan_parser import create_default_analysis_plan

                default_steps = create_default_analysis_plan(research_topic)
                logger.info(f"使用默认分析计划，steps类型: {type(default_steps)}")
                return {"steps": default_steps, "step_index": 0}

        extract_steps = FunctionVertex(
            id="extract_steps",
            task=extract_steps_task,
            variables=[{SOURCE_SCOPE: "analysis_plan", SOURCE_VAR: None, LOCAL_VAR: "analysis_plan"}],
        )

        # 4. WhileVertexGroup循环执行每个step（包含复杂子图）
        # 创建步骤执行子图中的顶点

        # 4.1 步骤准备顶点：准备当前步骤的上下文
        def step_prepare_task(inputs, context):
            # 从inputs获取steps和自动注入的iteration_index
            steps = inputs.get("steps", [])
            step_index = inputs.get(ITERATION_INDEX_KEY, 0)  # 使用自动注入的循环索引

            # 防护逻辑：检查索引是否超出范围
            # 这种情况可能在WhileVertexGroup的条件检查时机问题中出现
            if step_index >= len(steps):
                logger.warning(f"步骤索引超出范围: {step_index} >= {len(steps)}，跳过执行")
                # 返回一个标记，表示应该停止循环
                return {
                    "current_step": None,
                    "step_index": step_index,
                    "total_steps": len(steps),
                    "should_stop": True,  # 添加停止标记
                    "error": "索引超出范围",
                }

            current_step = steps[step_index]
            # 显示正确的进度（确保不超出范围）
            progress_current = min(step_index + 1, len(steps))
            logger.info(f"准备执行步骤 {progress_current}/{len(steps)}: {current_step.get('step_name', '未知步骤')}")

            return {
                "current_step": current_step,
                "step_index": step_index,
                "total_steps": len(steps),
                "step_id": current_step.get("step_id", ""),
                "step_name": current_step.get("step_name", ""),
                "step_description": current_step.get("description", ""),
                "step_method": current_step.get("method", ""),
                "should_stop": False,  # 正常情况下不停止
            }

        step_prepare = FunctionVertex(
            id="step_prepare",
            task=step_prepare_task,
            variables=[
                {SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "steps", LOCAL_VAR: "steps"},
                # iteration_index 会被 WhileVertexGroup 自动注入，无需手动配置
            ],
        )

        # 4.2 步骤分析顶点：执行具体的分析工作
        step_analysis_params = {
            "model": model_to_use,
            SYSTEM: self.prompts.get_step_analysis_system_prompt(),
            USER: [self.prompts.get_step_analysis_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.7,
            "max_tokens": 4096,
            ENABLE_SEARCH_KEY: True,
        }

        step_analysis = LLMVertex(
            id="step_analysis",
            task=None,
            params=step_analysis_params,
            variables=[
                {SOURCE_SCOPE: "step_prepare", SOURCE_VAR: "current_step", LOCAL_VAR: "current_step"},
                {SOURCE_SCOPE: "step_prepare", SOURCE_VAR: "step_index", LOCAL_VAR: "step_index"},
                {SOURCE_SCOPE: "step_prepare", SOURCE_VAR: "total_steps", LOCAL_VAR: "total_steps"},
                {SOURCE_SCOPE: "step_prepare", SOURCE_VAR: "step_id", LOCAL_VAR: "step_id"},
                {SOURCE_SCOPE: "step_prepare", SOURCE_VAR: "step_name", LOCAL_VAR: "step_name"},
                {SOURCE_SCOPE: "step_prepare", SOURCE_VAR: "step_description", LOCAL_VAR: "step_description"},
                {SOURCE_SCOPE: "step_prepare", SOURCE_VAR: "step_method", LOCAL_VAR: "step_method"},
                {SOURCE_SCOPE: "topic_analysis", SOURCE_VAR: None, LOCAL_VAR: "topic_analysis"},
                {SOURCE_SCOPE: "source", SOURCE_VAR: "research_topic", LOCAL_VAR: "research_topic"},
            ],
        )

        # 4.3 步骤后处理顶点：保存结果并累积所有步骤的分析结果
        def step_postprocess_task(inputs, context):
            # 从inputs或context中获取或初始化累积的步骤结果
            accumulated_results = inputs.get("accumulated_step_results")
            if accumulated_results is None:
                accumulated_results = context.get_output("accumulated_step_results") or []

            # 从上游获取数据
            step_prepare_output = inputs.get("step_prepare_output", {})
            step_analysis_output = inputs.get("step_analysis_output", {})
            steps = inputs.get("steps", [])
            step_index = inputs.get(ITERATION_INDEX_KEY, 0)  # 使用自动注入的循环索引
            total_steps = len(steps)

            # 检查是否有停止标记
            should_stop = step_prepare_output.get("should_stop", False)
            if should_stop:
                logger.warning(f"检测到停止标记，步骤执行异常终止")
            else:
                logger.info(f"步骤 {step_index + 1}/{total_steps} 执行完成")

            # 添加当前步骤的结果
            if not should_stop:
                current_result = {
                    "step_index": step_index,
                    "step_info": step_prepare_output.get("current_step", {}),
                    "analysis_result": step_analysis_output,
                    "completed_at": step_index + 1,
                }
                accumulated_results.append(current_result)

            # 更新context中的累积结果
            context.store_output("accumulated_step_results", accumulated_results)

            return {
                "steps": steps,
                "completed_step": step_prepare_output.get("current_step", {}),
                "step_result": step_analysis_output,
                "accumulated_step_results": accumulated_results,  # 新增：累积的所有步骤结果
                "should_stop": should_stop,  # 传递停止标记
            }

        step_postprocess = FunctionVertex(
            id="step_postprocess",
            task=step_postprocess_task,
            variables=[
                {SOURCE_SCOPE: "step_prepare", SOURCE_VAR: None, LOCAL_VAR: "step_prepare_output"},
                {SOURCE_SCOPE: "step_analysis", SOURCE_VAR: None, LOCAL_VAR: "step_analysis_output"},
                {SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "steps", LOCAL_VAR: "steps"},
                # 添加对之前累积结果的依赖
                {
                    SOURCE_SCOPE: SUBGRAPH_SOURCE,
                    SOURCE_VAR: "accumulated_step_results",
                    LOCAL_VAR: "accumulated_step_results",
                },
                # iteration_index 会被 WhileVertexGroup 自动注入，无需手动配置
            ],
        )

        # 创建子图边
        from vertex_flow.workflow.edge import Always, Edge

        step_edge1 = Edge(step_prepare, step_analysis, Always())
        step_edge2 = Edge(step_analysis, step_postprocess, Always())

        # 创建循环条件函数
        def step_condition_task(inputs, context):
            # 使用自动注入的iteration_index来判断循环条件
            logger.info(f"步骤循环条件检查: {inputs}")
            steps = inputs.get("steps", [])
            step_index = inputs.get(ITERATION_INDEX_KEY, 0)  # 使用自动注入的循环索引

            # 检查是否有停止标记（来自step_postprocess的输出）
            should_stop = inputs.get("should_stop", False)
            if should_stop:
                logger.info(f"检测到停止标记，终止循环")
                return False

            # 正常的循环条件检查
            should_continue = step_index < len(steps)
            logger.info(f"步骤循环条件检查: 当前索引={step_index}, 总步骤数={len(steps)}, 继续循环={should_continue}")
            return should_continue

        # 创建WhileVertexGroup（使用新的循环索引增强功能）
        while_vertex_group = WhileVertexGroup(
            id="while_analysis_steps_group",
            name="分析步骤循环执行组",
            subgraph_vertices=[step_prepare, step_analysis, step_postprocess],
            subgraph_edges=[step_edge1, step_edge2],
            condition_task=step_condition_task,
            variables=[
                {SOURCE_SCOPE: "extract_steps", SOURCE_VAR: "steps", LOCAL_VAR: "steps"},
                {SOURCE_SCOPE: "topic_analysis", SOURCE_VAR: "topic_analysis", LOCAL_VAR: "topic_analysis"},
                {SOURCE_SCOPE: "source", SOURCE_VAR: "research_topic", LOCAL_VAR: "research_topic"},
                # 添加累积结果的传递，确保在循环中能正确传递
                {
                    SOURCE_SCOPE: SUBGRAPH_SOURCE,
                    SOURCE_VAR: "accumulated_step_results",
                    LOCAL_VAR: "accumulated_step_results",
                },
            ],
            exposed_variables=[
                {SOURCE_SCOPE: SUBGRAPH_SOURCE, SOURCE_VAR: "steps", LOCAL_VAR: "steps"},
                {
                    SOURCE_SCOPE: "step_postprocess",
                    SOURCE_VAR: "accumulated_step_results",
                    LOCAL_VAR: "step_analysis_results",
                },
                {SOURCE_SCOPE: "step_postprocess", SOURCE_VAR: "should_stop", LOCAL_VAR: "should_stop"},
                {SOURCE_SCOPE: "topic_analysis", SOURCE_VAR: "topic_analysis", LOCAL_VAR: "topic_analysis"},
                {SOURCE_SCOPE: "source", SOURCE_VAR: "research_topic", LOCAL_VAR: "research_topic"},
                # iteration_index 会被自动暴露，无需手动配置
            ],
        )

        # 3. 信息收集阶段已集成到步骤循环中，此处删除独立的信息收集顶点

        # 4. 深度分析顶点
        deep_analysis_params = {
            "model": model_to_use,  # 使用指定的模型
            SYSTEM: self.prompts.get_deep_analysis_system_prompt(),
            USER: [self.prompts.get_deep_analysis_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.8,  # 提高创造性，深度分析需要更多洞察
            "max_tokens": 8192,  # 深度分析需要最多的输出空间
            ENABLE_SEARCH_KEY: True,
        }
        if save_intermediate:
            deep_analysis_params[POSTPROCESS] = lambda content, inputs, context: self._postprocess_with_save(
                content, inputs, context, STAGE_DEEP_ANALYSIS
            )

        deep_analysis = LLMVertex(
            id="deep_analysis",
            task=None,
            params=deep_analysis_params,
            variables=[
                {
                    SOURCE_SCOPE: "while_analysis_steps_group",
                    SOURCE_VAR: "step_analysis_results",
                    LOCAL_VAR: "step_analysis_results",
                },
                {SOURCE_SCOPE: "topic_analysis", SOURCE_VAR: None, LOCAL_VAR: "topic_analysis"},
                {SOURCE_SCOPE: "analysis_plan", SOURCE_VAR: None, LOCAL_VAR: "analysis_plan"},
                {SOURCE_SCOPE: "source", SOURCE_VAR: "research_topic", LOCAL_VAR: "research_topic"},
            ],
        )

        # 5. 交叉验证顶点
        cross_validation_params = {
            "model": model_to_use,  # 使用指定的模型
            SYSTEM: self.prompts.get_cross_validation_system_prompt(),
            USER: [self.prompts.get_cross_validation_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.5,  # 验证阶段需要更严谨
            "max_tokens": 8192,  # 验证报告需要详细说明
            ENABLE_SEARCH_KEY: True,
        }
        if save_intermediate:
            cross_validation_params[POSTPROCESS] = lambda content, inputs, context: self._postprocess_with_save(
                content, inputs, context, STAGE_CROSS_VALIDATION
            )

        cross_validation = LLMVertex(
            id="cross_validation",
            task=None,
            params=cross_validation_params,
            variables=[
                {SOURCE_SCOPE: "deep_analysis", SOURCE_VAR: None, LOCAL_VAR: "deep_analysis"},
                {SOURCE_SCOPE: "topic_analysis", SOURCE_VAR: None, LOCAL_VAR: "topic_analysis"},
                {SOURCE_SCOPE: "analysis_plan", SOURCE_VAR: None, LOCAL_VAR: "analysis_plan"},
                {
                    SOURCE_SCOPE: "while_analysis_steps_group",
                    SOURCE_VAR: "step_analysis_results",
                    LOCAL_VAR: "step_analysis_results",
                },
                {SOURCE_SCOPE: "source", SOURCE_VAR: "research_topic", LOCAL_VAR: "research_topic"},
            ],
        )

        # 6. 总结报告顶点
        summary_report = LLMVertex(
            id="summary_report",
            task=None,
            params={
                "model": model_to_use,  # 使用指定的模型
                SYSTEM: self.prompts.get_summary_report_system_prompt(),
                USER: [self.prompts.get_summary_report_user_prompt()],
                ENABLE_STREAM: stream_mode,
                "temperature": 0.7,  # 平衡创造性和准确性
                "max_tokens": 8192,  # 最终报告需要最大的输出空间
            },
        )

        # 配置summary_report顶点的变量依赖关系
        summary_report.add_variables(
            [
                {
                    SOURCE_SCOPE: "cross_validation",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "cross_validation",
                },
                {
                    SOURCE_SCOPE: "topic_analysis",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "topic_analysis",
                },
                {
                    SOURCE_SCOPE: "analysis_plan",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "analysis_plan",
                },
                {
                    SOURCE_SCOPE: "deep_analysis",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "deep_analysis",
                },
                {
                    SOURCE_SCOPE: "while_analysis_steps_group",
                    SOURCE_VAR: "step_analysis_results",
                    LOCAL_VAR: "step_analysis_results",
                },
                {
                    SOURCE_SCOPE: "source",
                    SOURCE_VAR: "research_topic",
                    LOCAL_VAR: "research_topic",
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
                    },
                    {
                        SOURCE_SCOPE: "source",
                        SOURCE_VAR: "research_topic",
                        LOCAL_VAR: "research_topic",
                    },
                ],
            )

        # 创建汇聚顶点
        if save_final_report:

            def sink_task(inputs, context):
                context.set_output("final_report", inputs.get("summary_report", ""))
                context.set_output("file_path", inputs.get("file_path", ""))
                context.set_output("message", "深度研究工作流执行完成，报告已保存到文件")
                context.set_output("research_topic", inputs.get("research_topic", ""))
                return None

            sink = SinkVertex(
                id="sink",
                task=sink_task,
                variables=[
                    {
                        SOURCE_SCOPE: "summary_report",
                        SOURCE_VAR: None,
                        LOCAL_VAR: "summary_report",
                    },
                    {
                        SOURCE_SCOPE: "file_save",
                        SOURCE_VAR: "file_path",
                        LOCAL_VAR: "file_path",
                    },
                    {
                        SOURCE_SCOPE: "source",
                        SOURCE_VAR: "research_topic",
                        LOCAL_VAR: "research_topic",
                    },
                ],
            )
        else:

            def sink_task(inputs, context):
                context.set_output("final_report", inputs.get("summary_report", ""))
                context.set_output("message", "深度研究工作流执行完成")
                context.set_output("research_topic", inputs.get("research_topic", ""))
                return None

            sink = SinkVertex(
                id="sink",
                task=sink_task,
                variables=[
                    {
                        SOURCE_SCOPE: "summary_report",
                        SOURCE_VAR: None,
                        LOCAL_VAR: "summary_report",
                    },
                    {
                        SOURCE_SCOPE: "source",
                        SOURCE_VAR: "research_topic",
                        LOCAL_VAR: "research_topic",
                    },
                ],
            )

        # 添加所有顶点到工作流
        workflow.add_vertex(source)
        workflow.add_vertex(topic_analysis)
        workflow.add_vertex(analysis_plan)
        workflow.add_vertex(extract_steps)
        workflow.add_vertex(while_vertex_group)
        workflow.add_vertex(deep_analysis)
        workflow.add_vertex(cross_validation)
        workflow.add_vertex(summary_report)
        if save_final_report and file_save:
            workflow.add_vertex(file_save)
        workflow.add_vertex(sink)

        # 连接顶点形成工作流管道
        source | topic_analysis
        topic_analysis | analysis_plan
        analysis_plan | extract_steps
        extract_steps | while_vertex_group
        while_vertex_group | deep_analysis
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
            # 从输入数据获取研究主题
            research_topic = inputs.get("research_topic", "")

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

            # 从输入数据获取研究主题
            research_topic = inputs.get("research_topic", "")

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
