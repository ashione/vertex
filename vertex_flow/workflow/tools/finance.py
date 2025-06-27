import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.tools.functions import FunctionTool

# yfinance依赖已移除，直接使用Yahoo Finance RESTful API


logging = LoggerUtil.get_logger()


class FinanceAPI:
    """金融数据API客户端

    提供股票价格、汇率、财经新闻等金融数据查询功能
    使用免费的金融API服务
    """

    def __init__(self, alpha_vantage_key: Optional[str] = None, finnhub_key: Optional[str] = None):
        """初始化金融API客户端

        Args:
            alpha_vantage_key: Alpha Vantage API密钥（可选）
            finnhub_key: Finnhub API密钥（可选）
        """
        # 使用免费的金融API服务
        self.alpha_vantage_base = "https://www.alphavantage.co/query"
        self.exchange_rate_base = "https://api.exchangerate-api.com/v4/latest"
        self.finnhub_base = "https://finnhub.io/api/v1"
        self.yahoo_finance_enabled = True  # 使用Yahoo Finance RESTful API

        # API密钥配置
        self.alpha_vantage_key = alpha_vantage_key
        self.finnhub_key = finnhub_key

    def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """获取股票价格

        Args:
            symbol: 股票代码，如 'AAPL', 'TSLA'

        Returns:
            包含股票价格信息的字典
        """
        try:
            # 优先尝试使用Yahoo Finance
            if self.yahoo_finance_enabled:
                try:
                    return self._get_yahoo_stock_data(symbol)
                except Exception as yahoo_error:
                    logging.warning(f"Yahoo Finance失败: {yahoo_error}")
                    # 如果没有Alpha Vantage API密钥，直接返回Yahoo Finance的错误
                    if (
                        not hasattr(self, "alpha_vantage_key")
                        or not self.alpha_vantage_key
                        or self.alpha_vantage_key == "demo"
                    ):
                        return {"error": f"Yahoo Finance API失败且未配置Alpha Vantage API密钥: {yahoo_error}"}
                    logging.warning("尝试使用Alpha Vantage作为备用数据源")

            # 回退到Alpha Vantage API
            if not hasattr(self, "alpha_vantage_key") or not self.alpha_vantage_key or self.alpha_vantage_key == "demo":
                return {"error": "未设置有效的Alpha Vantage API密钥"}

            url = f"https://www.alphavantage.co/query"
            params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.alpha_vantage_key}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "Global Quote" in data:
                quote = data["Global Quote"]
                return {
                    "symbol": quote.get("01. symbol", symbol),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "0%"),
                    "volume": int(quote.get("06. volume", 0)),
                    "latest_trading_day": quote.get("07. latest trading day", ""),
                    "previous_close": float(quote.get("08. previous close", 0)),
                    "source": "Alpha Vantage",
                }
            else:
                raise ValueError(f"Alpha Vantage API返回异常数据: {data}")

        except Exception as e:
            logging.error(f"获取股票价格失败: {e}")
            raise e

    def _get_yahoo_stock_data(self, symbol: str) -> Dict[str, Any]:
        """使用Yahoo Finance RESTful API获取股票数据"""
        import json
        import time

        import requests.exceptions

        max_retries = 2
        for attempt in range(max_retries):
            try:
                logging.info(
                    f"正在通过Yahoo Finance API获取股票 {symbol} 的信息... (尝试 {
                        attempt + 1}/{max_retries})"
                )

                # Yahoo Finance API endpoints
                quote_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                # 获取股票报价数据
                params = {"interval": "1d", "range": "5d", "includePrePost": "false"}

                response = requests.get(quote_url, params=params, headers=headers, timeout=10)

                if response.status_code == 429:
                    logging.warning("Yahoo Finance API限流，等待后重试")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        raise ValueError("Yahoo Finance API请求过于频繁")

                response.raise_for_status()

                try:
                    data = response.json()
                except json.JSONDecodeError as json_e:
                    logging.error(f"JSON解码失败: {json_e}")
                    raise ValueError(f"Yahoo Finance API返回无效JSON: {json_e}")

                # 解析Yahoo Finance API响应
                if "chart" not in data or "result" not in data["chart"]:
                    logging.error(f"API响应格式异常: {data}")
                    raise ValueError(f"Yahoo Finance API响应格式异常")

                result = data["chart"]["result"]
                if not result:
                    raise ValueError(f"Yahoo Finance API未返回股票 {symbol} 的数据")

                stock_data = result[0]
                meta = stock_data.get("meta", {})

                # 获取价格数据
                current_price = meta.get("regularMarketPrice")
                previous_close = meta.get("previousClose") or meta.get("chartPreviousClose")

                if current_price is None:
                    raise ValueError(f"无法获取股票 {symbol} 的当前价格")

                # 如果没有previous_close，尝试从历史数据中获取
                if previous_close is None and "timestamp" in stock_data and "indicators" in stock_data:
                    try:
                        quotes = stock_data["indicators"]["quote"][0]
                        closes = quotes.get("close", [])
                        if len(closes) >= 2:
                            # 获取倒数第二个收盘价作为前一日收盘价
                            previous_close = closes[-2]
                    except (KeyError, IndexError, TypeError):
                        logging.warning("无法从历史数据中获取前一日收盘价")

                # 计算变化
                change = current_price - previous_close if previous_close else 0
                change_percent = (change / previous_close) * 100 if previous_close and previous_close != 0 else 0

                # 获取成交量
                volume = meta.get("regularMarketVolume", 0)

                # 获取其他信息
                market_cap = meta.get("marketCap")
                pe_ratio = meta.get("trailingPE")
                week_52_high = meta.get("fiftyTwoWeekHigh")
                week_52_low = meta.get("fiftyTwoWeekLow")

                # 获取交易日期
                trading_day = datetime.fromtimestamp(meta.get("regularMarketTime", time.time())).strftime("%Y-%m-%d")

                return {
                    "symbol": symbol.upper(),
                    "price": round(float(current_price), 2),
                    "change": round(float(change), 2),
                    "change_percent": f"{
                        change_percent:+.2f}%",
                    "volume": int(volume) if volume else 0,
                    "latest_trading_day": trading_day,
                    "previous_close": round(float(previous_close), 2) if previous_close else 0,
                    "market_cap": market_cap,
                    "pe_ratio": pe_ratio,
                    "52_week_high": week_52_high,
                    "52_week_low": week_52_low,
                    "source": "Yahoo Finance API",
                    "data_period": "实时数据",
                }

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException,
            ) as network_e:
                logging.warning(f"网络错误 (尝试 {attempt + 1}/{max_retries}): {network_e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                    continue
                else:
                    raise ValueError(f"Yahoo Finance API网络连接失败: {network_e}")
            except Exception as e:
                logging.error(
                    f"Yahoo Finance API获取股票数据失败 (尝试 {
                        attempt + 1}/{max_retries}): {e}"
                )
                logging.error(f"错误类型: {type(e).__name__}")
                if attempt < max_retries - 1 and ("Connection" in str(e) or "timeout" in str(e).lower()):
                    time.sleep(1)
                    continue
                else:
                    raise e

    def get_stock_history(self, symbol: str, period: str = "1mo") -> Dict[str, Any]:
        """获取股票历史数据

        Args:
            symbol: 股票代码
            period: 时间周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            包含历史数据的字典
        """
        # 使用Yahoo Finance RESTful API获取历史数据
        try:
            # 计算时间范围
            end_date = datetime.now()
            if period == "1d":
                start_date = end_date - timedelta(days=1)
            elif period == "5d":
                start_date = end_date - timedelta(days=5)
            elif period == "1mo":
                start_date = end_date - timedelta(days=30)
            elif period == "3mo":
                start_date = end_date - timedelta(days=90)
            elif period == "6mo":
                start_date = end_date - timedelta(days=180)
            elif period == "1y":
                start_date = end_date - timedelta(days=365)
            elif period == "2y":
                start_date = end_date - timedelta(days=730)
            elif period == "5y":
                start_date = end_date - timedelta(days=1825)
            elif period == "10y":
                start_date = end_date - timedelta(days=3650)
            else:
                start_date = end_date - timedelta(days=365)  # 默认1年

            # 构建Yahoo Finance历史数据API URL
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())

            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                "period1": start_timestamp,
                "period2": end_timestamp,
                "interval": "1d",
                "includePrePost": "true",
                "events": "div%2Csplit",
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 429:
                logging.warning(f"Yahoo Finance API rate limit hit for {symbol}, retrying...")
                time.sleep(1)
                response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return {
                    "error": f"Failed to fetch historical data for {symbol}: HTTP {
                        response.status_code}"
                }

            data = response.json()

            if "chart" not in data or not data["chart"]["result"]:
                return {"error": f"No historical data found for {symbol}"}

            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {})
            quote = indicators.get("quote", [{}])[0]

            opens = quote.get("open", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])

            if not timestamps or not closes:
                return {"error": f"No historical data found for {symbol}"}

            # 转换为可序列化的格式
            history_data = []
            for i, timestamp in enumerate(timestamps):
                if i < len(closes) and closes[i] is not None:
                    date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    history_data.append(
                        {
                            "date": date,
                            "open": round(float(opens[i]) if i < len(opens) and opens[i] is not None else 0, 2),
                            "high": round(float(highs[i]) if i < len(highs) and highs[i] is not None else 0, 2),
                            "low": round(float(lows[i]) if i < len(lows) and lows[i] is not None else 0, 2),
                            "close": round(float(closes[i]), 2),
                            "volume": int(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0,
                        }
                    )

            return {
                "symbol": symbol.upper(),
                "period": period,
                "data_points": len(history_data),
                "history": history_data,
                "source": "Yahoo Finance",
            }

        except Exception as e:
            logging.error(f"获取历史数据失败: {e}")
            return {"error": f"Failed to get history for {symbol}: {str(e)}"}

    def get_crypto_price(self, symbol: str) -> Dict[str, Any]:
        """获取加密货币价格（使用免费API）

        Args:
            symbol: 加密货币代码，如 'BTC-USD', 'ETH-USD'

        Returns:
            包含加密货币价格信息的字典
        """
        try:
            # 使用Yahoo Finance获取加密货币数据
            if not symbol.endswith("-USD"):
                symbol = f"{symbol}-USD"

            return self._get_yahoo_stock_data(symbol)

        except Exception as e:
            logging.error(f"获取加密货币价格失败: {e}")
            raise e

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """获取汇率信息

        Args:
            from_currency: 源货币代码，如 'USD'
            to_currency: 目标货币代码，如 'CNY'

        Returns:
            包含汇率信息的字典
        """
        try:
            url = f"{self.exchange_rate_base}/{from_currency.upper()}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            rates = data.get("rates", {})

            if to_currency.upper() not in rates:
                raise ValueError(f"不支持的货币代码: {to_currency.upper()}")

            return {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "rate": rates[to_currency.upper()],
                "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
                "base": data.get("base", from_currency.upper()),
                "source": "ExchangeRate-API",
            }

        except Exception as e:
            logging.error(f"获取汇率失败: {e}")
            raise e

    def get_financial_news(self, category: str = "general", count: int = 5) -> Dict[str, Any]:
        """获取财经新闻

        Args:
            category: 新闻类别，如 'general', 'forex', 'crypto', 'merger'
            count: 返回新闻数量

        Returns:
            包含财经新闻的字典
        """
        # 使用Finnhub API获取真实新闻数据
        try:
            if not hasattr(self, "finnhub_key") or self.finnhub_key == "demo":
                raise ValueError("未设置有效的Finnhub API密钥")

            url = f"{self.finnhub_base}/news"
            params = {"category": category, "token": self.finnhub_key}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and data:
                news_items = []
                for item in data[:count]:
                    news_items.append(
                        {
                            "headline": item.get("headline", ""),
                            "summary": item.get("summary", ""),
                            "source": item.get("source", ""),
                            "datetime": datetime.fromtimestamp(item.get("datetime", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                            "category": category,
                            "url": item.get("url", ""),
                        }
                    )

                return {"category": category, "count": len(news_items), "news": news_items, "source": "Finnhub"}
            else:
                raise ValueError("API返回数据格式异常")

        except Exception as e:
            logging.error(f"获取财经新闻失败: {e}")
            raise e


# 全局配置缓存
_finance_config_cache = None
_config_loaded = False


def _get_finance_config():
    """获取金融配置（带缓存）

    Returns:
        金融配置字典
    """
    global _finance_config_cache, _config_loaded

    if not _config_loaded:
        try:
            from vertex_flow.workflow.service import VertexFlowService

            service = VertexFlowService.get_instance()
            _finance_config_cache = service.get_finance_config()
            _config_loaded = True
            logging.info("金融配置已加载并缓存")
        except Exception as e:
            logging.error(f"获取金融配置失败: {str(e)}")
            _finance_config_cache = {}

    return _finance_config_cache


def reset_finance_config_cache():
    """重置金融配置缓存

    当配置文件更新时，可以调用此函数重新加载配置。
    """
    global _finance_config_cache, _config_loaded
    _finance_config_cache = None
    _config_loaded = False
    logging.info("金融配置缓存已重置")


def finance_function(inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """金融工具函数

    这是一个综合性的金融工具，支持股票价格查询、汇率转换、财经新闻获取等功能。
    支持从配置文件自动加载API密钥，提供高质量的金融数据查询服务。

    Args:
        inputs: 输入参数字典，包含:
            - action: 操作类型 ('stock_price', 'stock_history', 'crypto_price', 'exchange_rate', 'financial_news')
            - symbol: 股票代码或加密货币代码
            - from_currency: 源货币代码（当action为'exchange_rate'时）
            - to_currency: 目标货币代码（当action为'exchange_rate'时）
            - period: 历史数据时间周期（当action为'stock_history'时）
            - category: 新闻类别（当action为'financial_news'时）
            - count: 返回数量（当action为'financial_news'时）
        context: 上下文信息（可选）

    Returns:
        包含查询结果的字典
    """
    # 打印调用参数
    logging.info(f"Finance tool called with inputs: {inputs}")

    # 参数验证
    if not inputs.get("action"):
        return {"success": False, "error": "操作类型不能为空", "data": None}

    # 获取缓存的配置
    try:
        config = _get_finance_config()

        # 检查是否至少有一个数据源启用
        alpha_vantage_enabled = config.get("alpha_vantage", {}).get("enabled", False)
        finnhub_enabled = config.get("finnhub", {}).get("enabled", False)
        yahoo_finance_enabled = config.get("yahoo_finance", {}).get("enabled", True)

        if not (alpha_vantage_enabled or finnhub_enabled or yahoo_finance_enabled):
            return {"success": False, "error": "金融服务未启用任何数据源，请检查配置文件", "data": None}

        # 获取API密钥
        alpha_vantage_key = config.get("alpha_vantage", {}).get("api_key")
        finnhub_key = config.get("finnhub", {}).get("api_key")

    except Exception as e:
        return {"success": False, "error": f"获取配置失败: {str(e)}", "data": None}

    try:
        action = inputs.get("action")

        finance_api = FinanceAPI(alpha_vantage_key=alpha_vantage_key, finnhub_key=finnhub_key)

        if action == "stock_price":
            symbol = inputs.get("symbol")
            if not symbol:
                return {"error": "缺少必需参数: symbol"}

            result = finance_api.get_stock_price(symbol)
            return {"success": True, "action": "stock_price", "data": result}

        elif action == "stock_history":
            symbol = inputs.get("symbol")
            if not symbol:
                return {"error": "缺少必需参数: symbol"}

            period = inputs.get("period", "1mo")
            result = finance_api.get_stock_history(symbol, period)
            return {"success": True, "action": "stock_history", "data": result}

        elif action == "crypto_price":
            symbol = inputs.get("symbol")
            if not symbol:
                return {"error": "缺少必需参数: symbol"}

            result = finance_api.get_crypto_price(symbol)
            return {"success": True, "action": "crypto_price", "data": result}

        elif action == "exchange_rate":
            from_currency = inputs.get("from_currency")
            to_currency = inputs.get("to_currency")
            if not from_currency or not to_currency:
                return {"error": "缺少必需参数: from_currency 和 to_currency"}

            result = finance_api.get_exchange_rate(from_currency, to_currency)
            return {"success": True, "action": "exchange_rate", "data": result}

        elif action == "financial_news":
            category = inputs.get("category", "general")
            count = inputs.get("count", 5)

            result = finance_api.get_financial_news(category, count)
            return {"success": True, "action": "financial_news", "data": result}

        else:
            return {
                "error": f"不支持的操作类型: {action}。支持的操作: stock_price, stock_history, crypto_price, exchange_rate, financial_news"
            }

    except Exception as e:
        logging.error(f"金融工具执行失败: {e}")
        return {"error": f"执行失败: {str(e)}"}


def create_finance_tool() -> FunctionTool:
    """创建金融工具实例

    从配置文件自动加载API密钥，无需手动传递。

    Returns:
        配置好的FunctionTool实例，可直接用于function calling
    """
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["stock_price", "stock_history", "crypto_price", "exchange_rate", "financial_news"],
            },
            "symbol": {
                "type": "string",
                "description": "股票代码或加密货币代码，如AAPL、TSLA、BTC-USD（当action为stock_price、stock_history或crypto_price时必需）",
            },
            "period": {
                "type": "string",
                "description": "历史数据时间周期（当action为stock_history时可选）",
                "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                "default": "1mo",
            },
            "from_currency": {
                "type": "string",
                "description": "源货币代码，如USD、EUR（当action为exchange_rate时必需）",
            },
            "to_currency": {
                "type": "string",
                "description": "目标货币代码，如CNY、USD（当action为exchange_rate时必需）",
            },
            "category": {
                "type": "string",
                "description": "新闻类别（当action为financial_news时可选）",
                "enum": ["general", "forex", "crypto", "technology", "automotive", "monetary_policy"],
                "default": "general",
            },
            "count": {
                "type": "integer",
                "description": "返回新闻数量（当action为financial_news时可选）",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
            },
        },
        "required": ["action"],
    }

    return FunctionTool(
        name="finance_tool",
        description="基于配置文件的综合金融工具。支持股票价格查询、股票历史数据、加密货币价格、汇率转换、财经新闻获取等功能。API密钥从配置文件自动加载，支持Alpha Vantage、Finnhub等多个数据源。适用于金融数据分析、投资研究、市场监控等场景。",
        func=finance_function,
        schema=schema,
        id="finance_tool",
    )


# 便捷的工具实例
finance_tool = create_finance_tool()
