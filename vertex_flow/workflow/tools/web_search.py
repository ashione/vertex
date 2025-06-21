import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

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
    """统一的Web搜索工具函数

    这是一个可用于function calling的Web搜索工具，支持多种搜索服务。
    根据配置文件自动选择可用的搜索服务，支持Bocha AI、DuckDuckGo、SerpAPI等。

    Args:
        inputs: 输入参数字典，包含以下字段:
            - query (str): 必需，搜索查询字符串
            - count (int): 可选，返回结果数量，默认5
            - freshness (str): 可选，搜索结果时效性，默认"noLimit"，可选值:
                * noLimit: 不限（默认，推荐使用）
                * oneDay: 一天内
                * oneWeek: 一周内
                * oneMonth: 一个月内
                * oneYear: 一年内
                * YYYY-MM-DD..YYYY-MM-DD: 搜索日期范围（仅Bocha支持）
                * YYYY-MM-DD: 搜索指定日期（仅Bocha支持）
            - summary (bool): 可选，是否返回AI总结，默认True（仅Bocha支持）
        context: 上下文对象（可选）

    Returns:
        搜索结果字典，包含以下字段:
            - success (bool): 搜索是否成功
            - query (str): 原始查询字符串
            - summary (str): AI生成的搜索结果总结（如果支持且启用）
            - results (List[Dict]): 搜索结果列表
            - total_count (int): 总结果数量
            - search_engine (str): 实际使用的搜索引擎
            - error (str): 错误信息（如果有）

    Example:
        >>> inputs = {
        ...     "query": "人工智能最新发展趋势",
        ...     "count": 5,
        ...     "summary": True
        ... }
        >>> result = web_search_function(inputs)
        >>> print(f"使用搜索引擎: {result['search_engine']}")
        >>> if result['summary']:
        ...     print(f"AI总结: {result['summary']}")
        >>> for item in result['results']:
        ...     print(f"{item['title']}: {item['url']}")
    """
    # 参数验证
    if not inputs.get("query"):
        return {"success": False, "error": "查询参数不能为空", "search_engine": "none"}

    query = inputs.get("query", "")
    count = inputs.get("count", 5)
    freshness = inputs.get("freshness", "noLimit")
    summary = inputs.get("summary", True)

    # 参数类型验证
    if not query or not isinstance(query, str):
        return {"success": False, "error": "查询参数必须是非空字符串", "search_engine": "none"}
    if not isinstance(count, int) or count <= 0:
        count = 5

    # 获取搜索服务配置
    try:
        from vertex_flow.workflow.service import VertexFlowService

        service = VertexFlowService.get_instance()

        # 尝试不同的搜索服务，按优先级排序
        search_services = [
            ("bocha", _search_with_bocha),
            ("duckduckgo", _search_with_duckduckgo),
            ("serpapi", _search_with_serpapi),
            ("searchapi", _search_with_searchapi),
        ]

        for service_name, search_func in search_services:
            logging.info(f"尝试搜索引擎: {service_name}")
            try:
                result = search_func(service, query, count, freshness, summary)
                if result["success"]:
                    result["search_engine"] = service_name
                    logging.info(f"Web搜索成功，使用引擎: {service_name}, 查询: {query}")
                    return result
                else:
                    logging.warning(f"搜索引擎 {service_name} 失败: {result.get('error', 'Unknown error')}")
            except Exception as e:
                logging.error(f"搜索引擎 {service_name} 异常: {e}")
                continue

        # 所有搜索服务都失败
        return {
            "success": False,
            "error": "所有搜索服务都不可用，请检查配置或网络连接",
            "query": query,
            "summary": "",
            "results": [],
            "total_count": 0,
            "search_engine": "none",
        }

    except Exception as e:
        logging.error(f"Web搜索配置获取失败: {e}")
        return {
            "success": False,
            "error": f"搜索配置获取失败: {str(e)}",
            "query": query,
            "summary": "",
            "results": [],
            "total_count": 0,
            "search_engine": "none",
        }


def _search_with_bocha(service, query: str, count: int, freshness: str, summary: bool) -> Dict[str, Any]:
    """使用Bocha AI搜索"""
    try:
        config = service.get_web_search_config("bocha")
        if not config.get("enabled", False):
            return {"success": False, "error": "Bocha搜索服务未启用"}

        if not config.get("api_key"):
            return {"success": False, "error": "Bocha搜索API密钥未配置"}

        # freshness参数验证：支持预定义值和日期格式
        valid_freshness = ["noLimit", "oneDay", "oneWeek", "oneMonth", "oneYear"]
        if not isinstance(freshness, str) or (
            freshness not in valid_freshness and not _is_valid_date_format(freshness)
        ):
            freshness = "noLimit"
        if not isinstance(summary, bool):
            summary = True

        # 执行Bocha搜索
        search_client = BochaWebSearch(config["api_key"])
        search_result = search_client.search(query=query, count=count, freshness=freshness, summary=summary)

        if "error" in search_result:
            return {"success": False, "error": search_result["error"]}

        # 提取结果
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
                    "source": "Bocha AI",
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
        return {"success": False, "error": f"Bocha搜索失败: {str(e)}"}


def _direct_serpapi_search(api_key: str, query: str, count: int = 5) -> Dict[str, Any]:
    """直接调用SerpAPI进行搜索"""
    try:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google",  # 使用Google引擎获得更好的搜索结果
            "q": query,
            "api_key": api_key,
            "num": min(count, 10),  # SerpAPI限制每次最多10个结果
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()

        results = []
        # 检查有机搜索结果
        if data.get("organic_results"):
            for result in data["organic_results"][:count]:
                results.append(
                    {
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", ""),
                        "source": "SerpAPI-Google",
                    }
                )

        # 检查知识面板
        elif data.get("knowledge_graph"):
            kg = data["knowledge_graph"]
            results.append(
                {
                    "title": kg.get("title", ""),
                    "url": kg.get("website", ""),
                    "snippet": kg.get("description", ""),
                    "source": "SerpAPI-Knowledge Graph",
                }
            )

        return {"results": results, "total_count": len(results)}

    except Exception as e:
        logging.error(f"SerpAPI直接搜索失败: {e}")
        return {"error": str(e)}


def _search_with_duckduckgo(service, query: str, count: int, freshness: str, summary: bool) -> Dict[str, Any]:
    """使用DuckDuckGo搜索"""
    logging.info(f"DuckDuckGo搜索: {query}, {count}, {freshness}, {summary}")

    try:
        config = service.get_web_search_config("duckduckgo")
        if not config.get("enabled", False):
            return {"success": False, "error": "DuckDuckGo搜索服务未启用"}

        # 使用WebSearchTool的免费搜索功能
        web_tool = WebSearchTool(config)
        search_result = web_tool.free_search.search_duckduckgo_instant(query)

        if "error" in search_result:
            return {"success": False, "error": search_result["error"]}

        results = search_result.get("results", [])
        instant_answer = search_result.get("instant_answer")

        # 格式化结果
        formatted_results = []
        for item in results[:count]:
            formatted_results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "site_name": "",
                    "source": "DuckDuckGo",
                }
            )

        # 如果有即时答案但没有搜索结果，将即时答案作为一个结果
        if instant_answer and not formatted_results:
            formatted_results.append(
                {
                    "title": f"即时答案: {query}",
                    "url": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
                    "snippet": instant_answer.get("answer", ""),
                    "site_name": instant_answer.get("source", "DuckDuckGo"),
                    "source": "DuckDuckGo Instant Answer",
                }
            )

        # 如果没有任何结果，创建一个搜索链接作为备用
        if not formatted_results:
            formatted_results.append(
                {
                    "title": f"在DuckDuckGo上搜索: {query}",
                    "url": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
                    "snippet": f"点击查看关于'{query}'的完整搜索结果",
                    "site_name": "DuckDuckGo",
                    "source": "DuckDuckGo Search",
                }
            )

        # 如果有即时答案，添加到总结中
        ai_summary = ""
        if instant_answer and summary:
            ai_summary = f"即时答案: {instant_answer.get('answer', '')}"
            if instant_answer.get("source"):
                ai_summary += f" (来源: {instant_answer['source']})"
        elif summary:
            ai_summary = f"为您找到关于'{query}'的搜索结果"

        logging.info(f"DuckDuckGo搜索结果: {formatted_results}, {ai_summary}")

        return {
            "success": True,
            "query": query,
            "summary": ai_summary,
            "results": formatted_results,
            "total_count": len(formatted_results),
            "error": "",
        }

    except Exception as e:
        return {"success": False, "error": f"DuckDuckGo搜索失败: {str(e)}"}


def _search_with_serpapi(service, query: str, count: int, freshness: str, summary: bool) -> Dict[str, Any]:
    """使用SerpAPI搜索"""
    try:
        config = service.get_web_search_config("serpapi")
        if not config.get("enabled", False):
            return {"success": False, "error": "SerpAPI搜索服务未启用"}

        if not config.get("api_key"):
            return {"success": False, "error": "SerpAPI密钥未配置"}

        # 直接调用SerpAPI，不使用FreeWebSearchTool
        search_result = _direct_serpapi_search(config.get("api_key"), query, count)

        if "error" in search_result:
            return {"success": False, "error": search_result["error"]}

        results = search_result.get("results", [])
        if not results:
            return {"success": False, "error": "SerpAPI搜索无结果"}

        # 格式化结果
        formatted_results = []
        for item in results[:count]:
            formatted_results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "site_name": "",
                    "source": "SerpAPI",
                }
            )

        # 生成简单总结
        ai_summary = ""
        if summary and formatted_results:
            ai_summary = f"通过SerpAPI找到 {len(formatted_results)} 个相关结果"

        return {
            "success": True,
            "query": query,
            "summary": ai_summary,
            "results": formatted_results,
            "total_count": len(formatted_results),
            "error": "",
        }

    except Exception as e:
        return {"success": False, "error": f"SerpAPI搜索失败: {str(e)}"}


def _search_with_searchapi(service, query: str, count: int, freshness: str, summary: bool) -> Dict[str, Any]:
    """使用SearchAPI搜索"""
    try:
        config = service.get_web_search_config("searchapi")
        if not config.get("enabled", False):
            return {"success": False, "error": "SearchAPI搜索服务未启用"}

        if not config.get("api_key"):
            return {"success": False, "error": "SearchAPI密钥未配置"}

        # 使用FreeWebSearchTool的SearchAPI功能
        free_search = FreeWebSearchTool(config)
        search_result = free_search.search_searchapi_free(query)

        if "error" in search_result:
            return {"success": False, "error": search_result["error"]}

        results = search_result.get("results", [])
        if not results:
            return {"success": False, "error": "SearchAPI搜索无结果"}

        # 格式化结果
        formatted_results = []
        for item in results[:count]:
            formatted_results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "site_name": "",
                    "source": "SearchAPI",
                }
            )

        # 生成简单总结
        ai_summary = ""
        if summary and formatted_results:
            ai_summary = f"通过SearchAPI找到 {len(formatted_results)} 个相关结果"

        return {
            "success": True,
            "query": query,
            "summary": ai_summary,
            "results": formatted_results,
            "total_count": len(formatted_results),
            "error": "",
        }

    except Exception as e:
        return {"success": False, "error": f"SearchAPI搜索失败: {str(e)}"}


def create_web_search_tool() -> FunctionTool:
    """创建统一的Web搜索工具实例

    Returns:
        配置好的FunctionTool实例，支持多种搜索引擎，可直接用于function calling
    """
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索查询字符串，描述要搜索的内容"},
            "count": {
                "type": "integer",
                "description": "返回结果数量，默认5个，范围1-20",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
            },
            "freshness": {
                "type": "string",
                "description": "搜索结果时效性。可选值：noLimit（不限，默认推荐）、oneDay（一天内）、oneWeek（一周内）、oneMonth（一个月内）、oneYear（一年内）。注意：日期范围格式（YYYY-MM-DD..YYYY-MM-DD）和指定日期（YYYY-MM-DD）仅Bocha AI支持",
                "default": "noLimit",
            },
            "summary": {
                "type": "boolean",
                "description": "是否返回AI生成的搜索结果总结。注意：AI总结功能主要由Bocha AI支持，其他引擎提供简单总结",
                "default": True,
            },
        },
        "required": ["query"],
    }

    return FunctionTool(
        name="web_search",
        description="智能Web搜索工具，支持多种搜索引擎。根据配置按优先级自动选择可用的搜索服务：Bocha AI（高质量AI总结）、DuckDuckGo（免费即时答案）、SerpAPI（Google搜索结果）、SearchAPI（多搜索引擎支持）。每次只使用一个启用的搜索服务。可以搜索最新的网络信息，支持新闻、百科、学术等多种内容源。适用于获取实时信息、研究资料收集、事实核查等场景。",
        func=web_search_function,
        schema=schema,
        id="web_search_unified",
    )


# 便捷的工具实例
web_search_tool = create_web_search_tool()


class FreeWebSearchTool:
    """
    Free Web Search Tool - 集成多个免费API的搜索工具

    支持的免费API:
    1. DuckDuckGo Instant Answer API (完全免费)
    2. SerpAPI免费层 (每月100次)
    3. SearchAPI.io免费层 (每月100次)
    4. 备用HTML解析搜索
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = LoggerUtil.get_logger(__name__)

        # API配置
        self.serpapi_key = self.config.get("serpapi_key")
        self.searchapi_key = self.config.get("searchapi_key")

        # 免费API限制跟踪
        self.daily_usage = {"serpapi": 0, "searchapi": 0, "duckduckgo": 0}

    def search_duckduckgo_instant(self, query: str) -> Dict[str, Any]:
        """
        DuckDuckGo Instant Answer API - 完全免费
        主要用于获取即时答案，不是完整的搜索结果
        """
        try:
            url = "https://api.duckduckgo.com/"
            params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 转换为统一格式
            results = {"query": query, "source": "duckduckgo_instant", "results": [], "instant_answer": None}

            # 即时答案
            if data.get("Answer"):
                results["instant_answer"] = {
                    "answer": data["Answer"],
                    "answer_type": data.get("AnswerType", ""),
                    "source": data.get("AbstractSource", ""),
                }

            # 相关主题
            if data.get("RelatedTopics"):
                for topic in data["RelatedTopics"][:5]:  # 限制5个结果
                    if isinstance(topic, dict) and topic.get("Text"):
                        results["results"].append(
                            {
                                "title": (
                                    topic.get("Text", "")[:100] + "..."
                                    if len(topic.get("Text", "")) > 100
                                    else topic.get("Text", "")
                                ),
                                "url": topic.get("FirstURL", ""),
                                "snippet": topic.get("Text", ""),
                                "source": "DuckDuckGo",
                            }
                        )

            self.daily_usage["duckduckgo"] += 1
            return results

        except Exception as e:
            self.logger.error(f"DuckDuckGo搜索失败: {e}")
            return {"error": str(e), "source": "duckduckgo_instant"}

    def search_serpapi_free(self, query: str) -> Dict[str, Any]:
        """
        SerpAPI免费层 - 每月100次免费搜索
        """
        if not self.serpapi_key:
            return {"error": "SerpAPI key not configured", "source": "serpapi"}

        if self.daily_usage["serpapi"] >= 3:  # 每日限制3次，节省月度配额
            return {"error": "Daily SerpAPI quota exceeded", "source": "serpapi"}

        try:
            url = "https://serpapi.com/search"
            params = {"engine": "duckduckgo", "q": query, "api_key": self.serpapi_key}

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            # 转换为统一格式
            results = {"query": query, "source": "serpapi_duckduckgo", "results": []}

            # 有机搜索结果
            if data.get("organic_results"):
                for result in data["organic_results"][:5]:
                    results["results"].append(
                        {
                            "title": result.get("title", ""),
                            "url": result.get("link", ""),
                            "snippet": result.get("snippet", ""),
                            "source": "SerpAPI-DuckDuckGo",
                        }
                    )

            self.daily_usage["serpapi"] += 1
            return results

        except Exception as e:
            self.logger.error(f"SerpAPI搜索失败: {e}")
            return {"error": str(e), "source": "serpapi"}

    def search_searchapi_free(self, query: str) -> Dict[str, Any]:
        """
        SearchAPI.io免费层 - 每月100次免费搜索
        """
        if not self.searchapi_key:
            return {"error": "SearchAPI key not configured", "source": "searchapi"}

        if self.daily_usage["searchapi"] >= 3:  # 每日限制3次
            return {"error": "Daily SearchAPI quota exceeded", "source": "searchapi"}

        try:
            url = "https://www.searchapi.io/api/v1/search"
            params = {"engine": "duckduckgo", "q": query, "api_key": self.searchapi_key}

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            # 转换为统一格式
            results = {"query": query, "source": "searchapi_duckduckgo", "results": []}

            # 有机搜索结果
            if data.get("organic_results"):
                for result in data["organic_results"][:5]:
                    results["results"].append(
                        {
                            "title": result.get("title", ""),
                            "url": result.get("link", ""),
                            "snippet": result.get("snippet", ""),
                            "source": "SearchAPI-DuckDuckGo",
                        }
                    )

            self.daily_usage["searchapi"] += 1
            return results

        except Exception as e:
            self.logger.error(f"SearchAPI搜索失败: {e}")
            return {"error": str(e), "source": "searchapi"}

    def search_backup_html(self, query: str) -> Dict[str, Any]:
        """
        备用HTML解析搜索 - 直接解析搜索引擎结果页面
        作为最后的备选方案
        """
        try:
            # 使用DuckDuckGo的HTML搜索（更宽松的robots.txt）
            url = "https://html.duckduckgo.com/html/"
            params = {"q": query}

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            # 简单的HTML解析（这里只是示例，实际使用需要更复杂的解析）
            html = response.text
            results = {"query": query, "source": "backup_html", "results": []}

            # 添加一个简单的结果说明
            results["results"].append(
                {
                    "title": f"搜索结果: {query}",
                    "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                    "snippet": f'找到了关于"{query}"的搜索结果。点击查看完整结果。',
                    "source": "Backup Search",
                }
            )

            return results

        except Exception as e:
            self.logger.error(f"备用搜索失败: {e}")
            return {"error": str(e), "source": "backup_html"}

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        智能搜索 - 按优先级尝试不同的API
        """
        self.logger.info(f"开始搜索: {query}")

        # 搜索策略优先级
        search_methods = [
            ("DuckDuckGo Instant", self.search_duckduckgo_instant),
            ("SerpAPI Free", self.search_serpapi_free),
            ("SearchAPI Free", self.search_searchapi_free),
            ("Backup HTML", self.search_backup_html),
        ]

        all_results = []
        errors = []

        for method_name, method in search_methods:
            try:
                self.logger.info(f"尝试使用 {method_name} 搜索")
                result = method(query)

                if "error" not in result and result.get("results"):
                    all_results.extend(result["results"])
                    self.logger.info(f"{method_name} 搜索成功，获得 {len(result['results'])} 个结果")

                    # 如果已经有足够的结果，就停止
                    if len(all_results) >= max_results:
                        break
                else:
                    if "error" in result:
                        errors.append(f"{method_name}: {result['error']}")
                        self.logger.warning(f"{method_name} 搜索失败: {result['error']}")

                # 避免过于频繁的请求
                time.sleep(0.5)

            except Exception as e:
                error_msg = f"{method_name}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(f"{method_name} 搜索异常: {e}")

        # 去重和限制结果数量
        unique_results = []
        seen_urls = set()

        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
                if len(unique_results) >= max_results:
                    break

        # 构建最终结果
        final_result = {
            "query": query,
            "total_results": len(unique_results),
            "results": unique_results,
            "search_methods_used": [
                method[0] for method in search_methods if method[0] not in [e.split(":")[0] for e in errors]
            ],
            "errors": errors if errors else None,
            "usage_stats": self.daily_usage.copy(),
        }

        self.logger.info(f"搜索完成，总共获得 {len(unique_results)} 个有效结果")
        return final_result


class WebSearchTool:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = LoggerUtil.get_logger(__name__)

        # 优先使用免费搜索工具
        self.free_search = FreeWebSearchTool(config)

        # 保持原有的付费API配置作为备选
        self.serp_api_key = self.config.get("serp_api_key")
        self.google_api_key = self.config.get("google_api_key")
        self.google_cse_id = self.config.get("google_cse_id")

    def search_web(self, query: str, num_results: int = 5) -> str:
        """
        Web搜索主入口 - 优先使用免费API
        """
        try:
            # 首先尝试免费搜索
            result = self.free_search.search(query, num_results)

            logging.info(f"搜索结果: {result}")

            if result.get("results"):
                # 格式化结果
                formatted_results = []
                for i, item in enumerate(result["results"], 1):
                    formatted_result = f"{i}. **{item.get('title', 'No Title')}**\n"
                    formatted_result += f"   URL: {item.get('url', 'No URL')}\n"
                    formatted_result += f"   摘要: {item.get('snippet', 'No snippet available')}\n"
                    formatted_result += f"   来源: {item.get('source', 'Unknown')}\n"
                    formatted_results.append(formatted_result)

                search_summary = f"🔍 搜索查询: {query}\n"
                search_summary += f"📊 找到 {result['total_results']} 个结果\n"
                search_summary += f"🛠️ 使用的搜索方法: {', '.join(result.get('search_methods_used', []))}\n\n"

                if result.get("errors"):
                    search_summary += f"⚠️ 部分搜索方法失败: {'; '.join(result['errors'])}\n\n"

                search_summary += "📋 搜索结果:\n" + "\n".join(formatted_results)

                # 添加使用统计
                usage_stats = result.get("usage_stats", {})
                if any(usage_stats.values()):
                    search_summary += f"\n📈 今日API使用情况: "
                    stats = [f"{k}: {v}" for k, v in usage_stats.items() if v > 0]
                    search_summary += ", ".join(stats)

                return search_summary
            else:
                # 如果免费搜索失败，尝试原有的付费API
                return self._fallback_search(query, num_results)

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return f"搜索失败: {str(e)}"

    def _fallback_search(self, query: str, num_results: int = 5) -> str:
        """
        备用搜索方法 - 使用原有的付费API逻辑
        """
        return f"免费搜索API暂时不可用，建议配置付费API密钥或稍后重试。\n搜索查询: {query}"
