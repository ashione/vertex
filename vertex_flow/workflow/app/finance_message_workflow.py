import json
from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar, cast

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import (
    ENABLE_STREAM,
    LOCAL_VAR,
    SOURCE_SCOPE,
    SOURCE_VAR,
    SYSTEM,
    USER,
)
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.tools.finance import create_finance_tool
from vertex_flow.workflow.workflow import LLMVertex, SinkVertex, SourceVertex, Workflow

logger = LoggerUtil.get_logger()


class FinanceMessageWorkflow:
    """金融消息智能分析工作流"""

    def __init__(self, vertex_service):
        self.vertex_service = vertex_service
        self.workflow_name = "finance-message"
        self.description = "Finance Message Intelligence Workflow: detect, classify, and analyze financial messages."
        self.finance_tool = create_finance_tool()

    def create_workflow(self, input_data: Dict[str, Any]) -> Workflow:
        """
        Args:
            input_data: 包含消息内容、流式参数等
                - content: 消息内容
                - stream: 是否流式
        Returns:
            Workflow: 配置好的工作流实例
        """
        logger.info(f"创建金融消息智能分析工作流, {input_data}...")
        context = WorkflowContext(
            env_parameters=input_data.get("env_vars", {}), user_parameters=input_data.get("user_vars", {})
        )
        workflow = Workflow(context)

        message = input_data.get("content", "")
        stream_mode = input_data.get("stream", False)

        # 源顶点
        source = SourceVertex(
            id="source",
            task=lambda inputs, context: {"message": inputs.get("content", message)},
        )

        # LLM1：判断是否金融相关及可信度
        llm_detect_params = {
            "model": self.vertex_service.get_chatmodel(),
            SYSTEM: self._get_detect_system_prompt(),
            USER: [self._get_detect_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        llm_detect = LLMVertex(
            id="llm_detect",
            params=llm_detect_params,
        )

        # LLM2：识别资产、板块、情感分析、并行调用function tool
        llm_asset_params = {
            "model": self.vertex_service.get_chatmodel(),
            SYSTEM: self._get_asset_system_prompt(),
            USER: [self._get_asset_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.3,
            "max_tokens": 2048,
            "tools_parallel": True,
        }
        llm_asset = LLMVertex(
            id="llm_asset",
            params=llm_asset_params,
            # tools=[self.finance_tool],
        )

        # LLM3：消息总结和新闻可信度判断
        llm_summary_params = {
            "model": self.vertex_service.get_chatmodel(),
            SYSTEM: self._get_summary_system_prompt(),
            USER: [self._get_summary_user_prompt()],
            ENABLE_STREAM: stream_mode,
            "temperature": 0.4,
            "max_tokens": 2048,
        }
        llm_summary = LLMVertex(
            id="llm_summary",
            params=llm_summary_params,
        )

        # 汇聚结果顶点
        def sink_task(inputs: Dict[str, Any], context: WorkflowContext) -> None:
            result = {}
            # 安全地获取和更新字典
            detect_result = inputs.get("detect_result", {})
            if isinstance(detect_result, dict):
                result.update(detect_result)

            asset_result = inputs.get("asset_result", {})
            if isinstance(asset_result, dict):
                result.update(asset_result)

            summary_result = inputs.get("summary_result", {})
            if isinstance(summary_result, dict):
                result.update(summary_result)

            context.outputs["result"] = result

        sink = SinkVertex(
            id="sink",
            task=sink_task,
        )
        # 添加变量选择器
        sink.add_variables(
            [
                {
                    SOURCE_SCOPE: "llm_detect",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "detect_result",
                },
                {
                    SOURCE_SCOPE: "llm_asset",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "asset_result",
                },
                {
                    SOURCE_SCOPE: "llm_summary",
                    SOURCE_VAR: None,
                    LOCAL_VAR: "summary_result",
                },
            ]
        )

        workflow.add_vertex(source)
        workflow.add_vertex(llm_detect)
        workflow.add_vertex(llm_asset)
        workflow.add_vertex(llm_summary)
        workflow.add_vertex(sink)
        source | llm_detect
        llm_detect | llm_asset
        llm_asset | llm_summary
        llm_summary | sink

        # 启用智能等待时间计算
        if stream_mode:
            workflow.enable_smart_wait_time()

        return workflow

    def _get_detect_system_prompt(self) -> str:
        today = datetime.now().strftime("%Y年%m月%d日")
        return (
            f"你是一个金融智能分析专家，擅长分析微博、twitter（中英文）及其它简短消息或新闻。\n"
            f"今天是{today}。请特别关注消息的时效性和与当前日期的相关性。\n"
            "你的任务：\n"
            "1. 判断消息是否与金融相关，输出is_financial（bool）和is_financial_confidence（0-1）。\n"
            "2. 对消息本身的真实性/可信度进行评估，输出confidence_score字段（0-1，越高越可信）。\n"
            "3. 只返回JSON，不要多余解释。"
        )

    def _get_detect_user_prompt(self) -> str:
        return "请判断以下消息是否与金融相关，并评估其可信度：\n" "{{source.message}}"

    def _get_asset_system_prompt(self) -> str:
        return (
            "你是一个金融智能分析专家。\n"
            "你的任务：\n"
            "1. 基于前序分析结果（is_financial, is_financial_confidence, confidence_score），如is_financial为True，则：\n"
            "2. 识别消息涉及的具体金融资产（如股票、货币、商品等），每个资产输出置信度。\n"
            "3. 对每个资产，识别其所属板块（如行业、主题等），输出置信度。\n"
            "4. 对消息整体进行情感分析（正面/中性/负面），输出置信度。\n"
            "5. 你可以调用finance工具查询股票、汇率、财经新闻等信息。如需查行情、新闻请直接调用工具，并可并行调用多个工具。\n"
            "6. 所有分析结果必须以结构化JSON返回，字段包括：assets（list，每项含name、confidence、sector、sector_confidence、realtime_info）、sentiment（str）、sentiment_confidence（float）等。\n"
            "7. 只返回JSON，不要多余解释。"
        )

    def _get_asset_user_prompt(self) -> str:
        return (
            "请基于以下前序分析结果，继续完成资产识别、板块分类、情感分析等任务：\n"
            "前序分析结果：{{llm_detect}}\n"
            "原始消息：{{source.message}}"
        )

    def _get_summary_system_prompt(self) -> str:
        today = datetime.now().strftime("%Y年%m月%d日")
        return (
            f"你是一个专业的金融新闻分析师。今天是{today}。\n"
            "你的任务：\n"
            "1. 对消息进行简洁的总结，突出关键信息。\n"
            "2. 基于前序分析结果和实时市场数据，判断消息的真实性和准确性。\n"
            "3. 分析消息可能对市场的影响。\n"
            "4. 输出JSON格式，包含以下字段：\n"
            "   - summary: 消息总结\n"
            "   - news_accuracy: 新闻准确性评分（0-1）\n"
            "   - accuracy_reason: 准确性判断理由\n"
            "   - market_impact: 市场影响分析\n"
            "   - impact_confidence: 影响判断置信度（0-1）\n"
            "5. 只返回JSON，不要多余解释。"
        )

    def _get_summary_user_prompt(self) -> str:
        return (
            "请基于以下信息，对消息进行总结并评估其准确性和市场影响：\n"
            "原始消息：{{source.message}}\n"
            "金融相关性分析：{{llm_detect}}\n"
            "资产和情感分析：{{llm_asset}}"
        )


def create_finance_message_workflow(vertex_service):
    workflow_builder = FinanceMessageWorkflow(vertex_service)

    def build_workflow(input_data: Dict[str, Any]) -> Workflow:
        return workflow_builder.create_workflow(input_data)

    return build_workflow


__all__ = [
    "FinanceMessageWorkflow",
    "create_finance_message_workflow",
]
