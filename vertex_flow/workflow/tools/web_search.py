import json
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.tools.functions import FunctionTool

logging = LoggerUtil.get_logger()


def _is_valid_date_format(freshness: str) -> bool:
    """验证日期格式是否有效

    Args:
        freshness: 日期字符串

    Returns:
        bool: 是否为有效的日期格式
    """
    # 匹配 YYYY-MM-DD 格式
    single_date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    # 匹配 YYYY-MM-DD..YYYY-MM-DD 格式
    date_range_pattern = r"^\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2}$"

    return bool(re.match(single_date_pattern, freshness) or re.match(date_range_pattern, freshness))


class BochaWebSearch:
    """博查Web搜索API客户端"""

    def __init__(self, api_key: str):
        """初始化博查搜索客户端

        Args:
            api_key: 博查API密钥
        """
        self.api_key = api_key
        self.base_url = "https://api.bochaai.com/v1"
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def search(
        self, query: str, count: int = 8, freshness: str = "noLimit", summary: bool = True, search_type: str = "web"
    ) -> Dict[str, Any]:
        """执行Web搜索

        Args:
            query: 搜索查询字符串
            count: 返回结果数量，默认8个
            freshness: 搜索结果时效性，可选值:
                - noLimit: 不限（默认，推荐使用）
                - oneDay: 一天内
                - oneWeek: 一周内
                - oneMonth: 一个月内
                - oneYear: 一年内
                - YYYY-MM-DD..YYYY-MM-DD: 搜索日期范围
                - YYYY-MM-DD: 搜索指定日期
            summary: 是否返回AI总结，默认True
            search_type: 搜索类型，默认"web"

        Returns:
            搜索结果字典
        """
        url = f"{self.base_url}/web-search"

        payload = {"query": query, "count": count, "freshness": freshness, "summary": summary}

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            # 博查API响应格式: result.data.webPages
            data = result.get("data", {})
            logging.info(f"博查搜索成功，查询: {query}, 返回结果数: {len(data.get('webPages', {}).get('value', []))}")
            return data

        except requests.exceptions.RequestException as e:
            logging.error(f"博查搜索请求失败: {e}, {response}")
            return {"error": f"搜索请求失败: {str(e)}", "webPages": {"value": []}}
        except json.JSONDecodeError as e:
            logging.error(f"博查搜索响应解析失败: {e}")
            return {"error": f"响应解析失败: {str(e)}", "webPages": {"value": []}}


def web_search_function(inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Web搜索工具函数

    这是一个可用于function calling的Web搜索工具，基于博查AI搜索API实现。
    支持从配置文件自动加载API密钥，提供高质量的搜索结果和AI总结。

    博查AI API响应格式:
    {
        "data": {
            "webPages": {
                "value": [...],
                "totalEstimatedMatches": 123
            },
            "summary": {
                "content": "AI总结内容"
            }
        }
    }

    Args:
        inputs: 输入参数字典，包含以下字段:
            - query (str): 必需，搜索查询字符串
            - count (int): 可选，返回结果数量，默认8
            - freshness (str): 可选，搜索结果时效性，默认"noLimit"，可选值:
                * noLimit: 不限（默认，推荐使用）
                * oneDay: 一天内
                * oneWeek: 一周内
                * oneMonth: 一个月内
                * oneYear: 一年内
                * YYYY-MM-DD..YYYY-MM-DD: 搜索日期范围
                * YYYY-MM-DD: 搜索指定日期
            - summary (bool): 可选，是否返回AI总结，默认True
        context: 上下文对象（可选）

    Returns:
        搜索结果字典，包含以下字段:
            - success (bool): 搜索是否成功
            - query (str): 原始查询字符串
            - summary (str): AI生成的搜索结果总结（如果启用）
            - results (List[Dict]): 搜索结果列表
            - total_count (int): 总结果数量
            - error (str): 错误信息（如果有）

    Example:
        >>> inputs = {
        ...     "query": "人工智能最新发展趋势",
        ...     "count": 5,
        ...     "summary": True
        ... }
        >>> result = web_search_function(inputs)
        >>> print(result['summary'])  # AI总结
        >>> for item in result['results']:  # 搜索结果
        ...     print(f"{item['title']}: {item['url']}")
    """
    # 参数验证
    if not inputs.get("query"):
        return {"success": False, "error": "查询参数不能为空", "data": None}

    # 获取配置
    try:
        from vertex_flow.workflow.service import VertexFlowService

        service = VertexFlowService.get_instance()
        config = service.get_web_search_config("bocha")

        if not config.get("enabled", False):
            return {"success": False, "error": "博查搜索服务未启用，请检查配置文件", "data": None}

        if not config.get("api_key"):
            return {"success": False, "error": "博查搜索API密钥未配置，请检查配置文件", "data": None}

        api_key = config["api_key"]
    except Exception as e:
        return {"success": False, "error": f"获取配置失败: {str(e)}", "data": None}

    query = inputs.get("query")
    count = inputs.get("count", 8)
    freshness = inputs.get("freshness", "noLimit")
    summary = inputs.get("summary", True)

    # 参数类型验证
    if not isinstance(count, int) or count <= 0:
        count = 8
    # freshness参数验证：支持预定义值和日期格式
    valid_freshness = ["noLimit", "oneDay", "oneWeek", "oneMonth", "oneYear"]
    if not isinstance(freshness, str) or (freshness not in valid_freshness and not _is_valid_date_format(freshness)):
        freshness = "noLimit"
    if not isinstance(summary, bool):
        summary = True

    try:

        # 执行搜索
        search_client = BochaWebSearch(api_key)
        search_result = search_client.search(query=query, count=count, freshness=freshness, summary=summary)

        # 处理搜索结果
        if "error" in search_result:
            return {
                "success": False,
                "error": search_result["error"],
                "query": query,
                "summary": "",
                "results": [],
                "total_count": 0,
            }

        # 提取结果 (API响应格式: result.data.webPages)
        web_pages = search_result.get("webPages", {})
        results = web_pages.get("value", [])
        total_count = web_pages.get("totalEstimatedMatches", len(results))

        # 格式化结果
        formatted_results = []
        for item in results:
            formatted_results.append(
                {
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "site_name": item.get("siteName", ""),
                    "site_icon": item.get("siteIcon", ""),
                }
            )

        # 提取AI总结
        ai_summary = search_result.get("summary", {}).get("content", "") if summary else ""

        return {
            "success": True,
            "query": query,
            "summary": ai_summary,
            "results": formatted_results,
            "total_count": total_count,
            "error": "",
        }

    except Exception as e:
        logging.error(f"Web搜索执行失败: {e}")
        return {
            "success": False,
            "error": f"搜索执行失败: {str(e)}",
            "query": query,
            "summary": "",
            "results": [],
            "total_count": 0,
        }


def create_web_search_tool() -> FunctionTool:
    """创建Web搜索工具实例

    Returns:
        配置好的FunctionTool实例，可直接用于function calling
    """
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索查询字符串，描述要搜索的内容"},
            "count": {
                "type": "integer",
                "description": "返回结果数量，默认8个，范围1-20",
                "minimum": 1,
                "maximum": 20,
                "default": 8,
            },
            "freshness": {
                "type": "string",
                "description": "搜索结果时效性。可选值：noLimit（不限，默认推荐）、oneDay（一天内）、oneWeek（一周内）、oneMonth（一个月内）、oneYear（一年内）、YYYY-MM-DD..YYYY-MM-DD（日期范围）、YYYY-MM-DD（指定日期）",
                "default": "noLimit",
            },
            "summary": {"type": "boolean", "description": "是否返回AI生成的搜索结果总结", "default": True},
        },
        "required": ["query"],
    }

    return FunctionTool(
        name="web_search",
        description="基于博查AI的Web搜索工具。可以搜索最新的网络信息，支持新闻、百科、学术等多种内容源，并提供AI总结。适用于获取实时信息、研究资料收集、事实核查等场景。",
        func=web_search_function,
        schema=schema,
        id="web_search_bocha",
    )


# 便捷的工具实例
web_search_tool = create_web_search_tool()
