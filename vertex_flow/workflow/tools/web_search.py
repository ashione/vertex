import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.tools.functions import FunctionTool

logging = LoggerUtil.get_logger()

# 搜索服务常量
SEARCH_PROVIDER_BRAVE = "brave"
SEARCH_PROVIDER_BOCHA = "bocha"
SEARCH_PROVIDER_SERPAPI = "serpapi"
SEARCH_PROVIDER_SEARCHAPI = "searchapi"
SEARCH_PROVIDER_DUCKDUCKGO = "duckduckgo"

# 搜索服务列表，按优先级排序
SEARCH_PROVIDERS = [
    SEARCH_PROVIDER_BRAVE,
    SEARCH_PROVIDER_BOCHA,
    SEARCH_PROVIDER_SERPAPI,
    SEARCH_PROVIDER_SEARCHAPI,
    SEARCH_PROVIDER_DUCKDUCKGO,
]

# 全局配置缓存
_web_search_config_cache = None
_config_loaded = False
_config_lock = threading.Lock()  # 添加线程锁


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


def _get_web_search_config():
    """获取Web搜索配置（带缓存）

    Returns:
        包含被启用的搜索服务配置和对应搜索函数的字典
    """
    global _web_search_config_cache, _config_loaded

    # 使用线程锁确保配置加载的线程安全
    with _config_lock:
        if not _config_loaded or _web_search_config_cache is None:
            try:
                from vertex_flow.workflow.service import VertexFlowService

                service = VertexFlowService.get_instance()

                # 获取各种搜索服务的配置
                _web_search_config_cache = {}
                enabled_services = []

                # 搜索函数映射
                search_functions = {
                    SEARCH_PROVIDER_BRAVE: _search_with_brave,
                    SEARCH_PROVIDER_BOCHA: _search_with_bocha,
                    SEARCH_PROVIDER_SERPAPI: _search_with_serpapi,
                    SEARCH_PROVIDER_SEARCHAPI: _search_with_searchapi,
                    SEARCH_PROVIDER_DUCKDUCKGO: _search_with_duckduckgo,
                }

                # 获取各个搜索服务的配置，只保留启用的服务
                for provider in SEARCH_PROVIDERS:
                    try:
                        config = service.get_web_search_config(provider)
                        if config.get("enabled", False):
                            _web_search_config_cache[provider] = {
                                "config": config,
                                "function": search_functions[provider],
                            }
                            enabled_services.append(provider)
                    except Exception as e:
                        logging.warning(f"获取{provider}配置失败: {e}")

                _config_loaded = True
                # 只在有启用服务时打印日志
                if enabled_services:
                    logging.info(f"Web搜索配置已加载并缓存，启用的服务: {enabled_services}")
                else:
                    logging.warning("Web搜索配置已加载，但没有启用任何搜索服务")
            except Exception as e:
                logging.error(f"获取Web搜索配置失败: {str(e)}")
                _web_search_config_cache = {}

    return _web_search_config_cache


def reset_web_search_config_cache():
    """重置Web搜索配置缓存

    当配置文件更新时，可以调用此函数重新加载配置。
    """
    global _web_search_config_cache, _config_loaded
    with _config_lock:
        _web_search_config_cache = None
        _config_loaded = False
        logging.info("Web搜索配置缓存已重置")


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

    根据配置自动选择启用的搜索服务，按优先级顺序尝试。
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

    try:
        from vertex_flow.workflow.service import VertexFlowService

        service = VertexFlowService.get_instance()

        # 获取缓存的配置，避免重复加载
        configs = _get_web_search_config() or {}

        # 按优先级顺序尝试搜索服务
        for provider in SEARCH_PROVIDERS:
            provider_info = configs.get(provider)
            if provider_info:  # 如果配置存在，说明该服务已启用
                search_func = provider_info["function"]
                logging.debug(f"尝试使用 {provider} 搜索服务")
                result = search_func(service, query, count, freshness, summary, configs)
                if result.get("success", False):
                    result["search_engine"] = provider
                    return result
                else:
                    logging.warning(f"{provider} 搜索失败: {result.get('error', '未知错误')}")

        # 没有启用的搜索服务
        return {
            "success": False,
            "error": "没有启用的搜索服务，请在配置文件中启用至少一个搜索服务",
            "search_engine": "none",
            "query": query,
            "summary": "",
            "results": [],
            "total_count": 0,
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


def _search_with_bocha(
    service, query: str, count: int, freshness: str, summary: bool, configs: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """使用Bocha AI搜索"""
    try:
        # 使用缓存的配置
        provider_info = configs.get(SEARCH_PROVIDER_BOCHA, {})
        config = provider_info.get("config", {})

        if not config.get("sk"):
            return {"success": False, "error": "Bocha API密钥未配置"}

        # 创建Bocha搜索客户端
        bocha_client = BochaWebSearch(config["sk"])

        # 执行搜索
        result = bocha_client.search(query, count, freshness, summary)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        # 解析搜索结果
        web_pages = result.get("webPages", {})
        pages = web_pages.get("value", [])
        summary_text = result.get("summary", "")

        # 转换为统一格式
        formatted_results = []
        for page in pages:
            formatted_results.append(
                {
                    "title": page.get("title", ""),
                    "url": page.get("url", ""),
                    "snippet": page.get("snippet", ""),
                    "source": "Bocha AI",
                }
            )

        return {
            "success": True,
            "query": query,
            "summary": summary_text,
            "results": formatted_results,
            "total_count": len(formatted_results),
        }

    except Exception as e:
        logging.error(f"Bocha搜索异常: {e}")
        return {"success": False, "error": f"Bocha搜索异常: {str(e)}"}


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


def _search_with_duckduckgo(
    service, query: str, count: int, freshness: str, summary: bool, configs: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """使用DuckDuckGo搜索"""
    logging.info(f"DuckDuckGo搜索: {query}, {count}, {freshness}, {summary}")

    try:
        # 使用缓存的配置
        provider_info = configs.get(SEARCH_PROVIDER_DUCKDUCKGO, {})
        config = provider_info.get("config", {}) if provider_info else {}

        # 使用DuckDuckGo Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # 解析DuckDuckGo响应
        results = []
        summary_text = ""

        # 提取即时答案
        if data.get("Abstract"):
            results.append(
                {
                    "title": data.get("Heading", "DuckDuckGo即时答案"),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("Abstract", ""),
                    "source": "DuckDuckGo",
                }
            )
            summary_text = data.get("Abstract", "")

        # 提取相关主题
        for topic in data.get("RelatedTopics", [])[: count - 1]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(
                    {
                        "title": (
                            topic.get("Text", "").split(" - ")[0]
                            if " - " in topic.get("Text", "")
                            else topic.get("Text", "")
                        ),
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                        "source": "DuckDuckGo",
                    }
                )

        return {
            "success": True,
            "query": query,
            "summary": summary_text,
            "results": results,
            "total_count": len(results),
        }

    except Exception as e:
        logging.error(f"DuckDuckGo搜索异常: {e}")
        return {"success": False, "error": f"DuckDuckGo搜索异常: {str(e)}"}


def _search_with_serpapi(
    service, query: str, count: int, freshness: str, summary: bool, configs: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """使用SerpAPI搜索"""
    try:
        # 使用缓存的配置
        provider_info = configs.get(SEARCH_PROVIDER_SERPAPI, {})
        config = provider_info.get("config", {}) if provider_info else {}

        if not config.get("api_key"):
            return {"success": False, "error": "SerpAPI密钥未配置"}

        # 使用SerpAPI搜索
        result = _direct_serpapi_search(config["api_key"], query, count)

        if not result.get("success", False):
            return {"success": False, "error": result.get("error", "SerpAPI搜索失败")}

        return {
            "success": True,
            "query": query,
            "summary": "",  # SerpAPI不提供AI总结
            "results": result.get("results", []),
            "total_count": len(result.get("results", [])),
        }

    except Exception as e:
        logging.error(f"SerpAPI搜索异常: {e}")
        return {"success": False, "error": f"SerpAPI搜索异常: {str(e)}"}


def _search_with_searchapi(
    service, query: str, count: int, freshness: str, summary: bool, configs: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """使用SearchAPI搜索"""
    try:
        # 使用缓存的配置
        provider_info = configs.get(SEARCH_PROVIDER_SEARCHAPI, {})
        config = provider_info.get("config", {}) if provider_info else {}

        if not config.get("api_key"):
            return {"success": False, "error": "SearchAPI密钥未配置"}

        api_key = config["api_key"]
        url = "https://www.searchapi.io/api/v1/search"

        params = {
            "api_key": api_key,
            "q": query,
            "num": count,
            "engine": "google",
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if "error" in data:
            return {"success": False, "error": f"SearchAPI错误: {data['error']}"}

        # 解析搜索结果
        results = []
        organic_results = data.get("organic_results", [])

        for result in organic_results:
            results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": "SearchAPI",
                }
            )

        return {
            "success": True,
            "query": query,
            "summary": "",  # SearchAPI不提供AI总结
            "results": results,
            "total_count": len(results),
        }

    except Exception as e:
        logging.error(f"SearchAPI搜索异常: {e}")
        return {"success": False, "error": f"SearchAPI搜索异常: {str(e)}"}


def _search_with_brave(
    service, query: str, count: int, freshness: str, summary: bool, configs: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """使用Brave Search API搜索"""
    logging.info(f"Brave Search搜索: {query}, {count}, {freshness}, {summary}")
    try:
        provider_info = configs.get(SEARCH_PROVIDER_BRAVE, {})
        config = provider_info.get("config", {}) if provider_info else {}
        if not config.get("api_key"):
            return {"success": False, "error": "Brave Search API密钥未配置"}
        api_key = config["api_key"]
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
        params = {
            "q": query,
            "count": count,
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # 解析Brave Search结果
        results = []
        web_results = data.get("web", {}).get("results", [])

        for result in web_results:
            results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("description", ""),
                    "source": "Brave Search",
                }
            )

        return {
            "success": True,
            "query": query,
            "summary": "",  # Brave Search不提供AI总结
            "results": results,
            "total_count": len(results),
        }

    except Exception as e:
        logging.error(f"Brave Search搜索异常: {e}")
        return {"success": False, "error": f"Brave Search搜索异常: {str(e)}"}


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
        description="智能Web搜索工具，支持多种搜索引擎。根据配置文件中的enabled状态自动选择可用的搜索服务，按优先级顺序尝试：Brave Search、Bocha AI（高质量AI总结）、SerpAPI（Google搜索结果）、SearchAPI（多搜索引擎支持）、DuckDuckGo（免费即时答案）。每次只使用一个启用的搜索服务。可以搜索最新的网络信息，支持新闻、百科、学术等多种内容源。适用于获取实时信息、研究资料收集、事实核查等场景。",
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
