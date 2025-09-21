"""
Exchange API clients for OKX and Binance
"""

import base64
import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from error_handler import ErrorHandler

try:
    from .config import ExchangeConfig
except ImportError:
    from config import ExchangeConfig


class BaseExchange(ABC):
    """Base class for exchange API clients"""

    def __init__(self, config: ExchangeConfig):
        self.config = config
        self.session = requests.Session()

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        pass

    @abstractmethod
    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """Get trading fees for a symbol"""
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker information"""
        pass

    @abstractmethod
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Get kline/candlestick data"""
        pass

    @abstractmethod
    def place_order(
        self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Place an order"""
        pass

    @abstractmethod
    def get_spot_positions(self) -> Dict[str, Any]:
        """Get spot positions/balances"""
        pass

    @abstractmethod
    def get_futures_positions(self) -> Dict[str, Any]:
        """Get futures positions"""
        pass


class OKXClient(BaseExchange):
    """OKX exchange API client"""

    def __init__(self, config: ExchangeConfig):
        super().__init__(config)
        # 根据沙盒模式选择API URL
        if config.sandbox:
            self.base_url = "https://www.okx.com"  # OKX沙盒环境使用相同URL
        else:
            self.base_url = config.base_url or "https://www.okx.com"
        self.api_url = f"{self.base_url}/api/v5"

    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """Generate OKX API signature"""
        message = timestamp + method + request_path + body
        signature = base64.b64encode(
            hmac.new(self.config.secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        return signature

    def _get_server_time(self) -> str:
        """获取OKX服务器时间"""
        try:
            response = self.session.get(f"{self.api_url}/public/time")
            response.raise_for_status()
            data = response.json()
            if data.get("code") == "0" and data.get("data"):
                # OKX返回的时间戳是毫秒级的字符串
                timestamp_ms = data["data"][0]["ts"]
                # 转换为ISO8601格式
                import datetime

                dt = datetime.datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=datetime.timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        except Exception as e:
            print(f"获取服务器时间失败: {e}")

        # 如果获取服务器时间失败，使用本地UTC时间
        import datetime

        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _make_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to OKX API"""
        # 使用服务器时间确保时间戳准确
        timestamp = self._get_server_time()
        # 签名需要完整的API路径，包含/api/v5前缀
        request_path = "/api/v5" + endpoint

        if params:
            request_path += "?" + urlencode(params)

        body = json.dumps(data, separators=(",", ":")) if data else ""
        signature = self._generate_signature(timestamp, method.upper(), request_path, body)

        headers = {
            "OK-ACCESS-KEY": self.config.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.config.passphrase,
            "Content-Type": "application/json",
        }

        url = self.api_url + endpoint

        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params)
            else:
                response = self.session.post(url, headers=headers, json=data)

            response.raise_for_status()

            # 检查响应内容是否为空
            if not response.text.strip():
                return {"error": "Empty response from server"}

            return response.json()
        except requests.exceptions.RequestException as e:
            error_info = ErrorHandler.format_api_error("OKX", e, getattr(e, "response", None))
            print(f"❌ OKX API请求失败: {ErrorHandler.get_user_friendly_message(error_info)}")
            return error_info
        except json.JSONDecodeError as e:
            error_info = ErrorHandler.format_api_error("OKX", e, response if "response" in locals() else None)
            print(f"❌ OKX数据解析失败: {ErrorHandler.get_user_friendly_message(error_info)}")
            return error_info
        except Exception as e:
            error_info = ErrorHandler.format_api_error("OKX", e)
            print(f"❌ OKX未知错误: {ErrorHandler.get_user_friendly_message(error_info)}")
            return error_info

    def get_account_info(self) -> Dict[str, Any]:
        """Get OKX account information"""
        return self._make_request("GET", "/account/balance")

    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """Get OKX trading fees"""
        response = self._make_request("GET", "/account/trade-fee", {"instType": "SPOT", "instId": symbol})
        if response.get("data"):
            fee_data = response["data"][0]
            return {"maker_fee": float(fee_data.get("maker", 0)), "taker_fee": float(fee_data.get("taker", 0))}
        return {"maker_fee": 0.001, "taker_fee": 0.001}  # Default fees

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get OKX ticker information"""
        response = self._make_request("GET", "/market/ticker", {"instId": symbol})
        if response.get("data"):
            ticker = response["data"][0]
            return {
                "symbol": ticker["instId"],
                "price": float(ticker["last"]),
                "bid": float(ticker["bidPx"]),
                "ask": float(ticker["askPx"]),
                "volume": float(ticker["vol24h"]),
                "change": float(ticker["sodUtc8"]),
            }
        # 如果没有数据或请求失败，返回错误信息
        if "error" in response:
            # 如果response本身就是错误信息字典，直接返回
            return response
        else:
            return {"error": "Failed to get ticker data"}

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Get OKX kline data"""
        # OKX interval mapping
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
            "1w": "1W",
        }

        okx_interval = interval_map.get(interval, "1m")
        response = self._make_request(
            "GET", "/market/candles", {"instId": symbol, "bar": okx_interval, "limit": str(limit)}
        )

        if response.get("data"):
            return [[float(x) for x in candle] for candle in response["data"]]
        return []

    def place_order(
        self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Place order on OKX"""
        order_data = {
            "instId": symbol,
            "tdMode": "cash",
            "side": side.lower(),
            "ordType": "market" if order_type.lower() == "market" else "limit",
            "sz": str(quantity),
        }

        if price and order_type.lower() == "limit":
            order_data["px"] = str(price)

        return self._make_request("POST", "/trade/order", data=order_data)

    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """查询订单状态"""
        try:
            params = {"ordId": order_id, "instId": symbol}

            response = self._make_request("GET", "/trade/order", params)

            if response.get("code") == "0" and response.get("data"):
                order_info = response["data"][0]
                return {"success": True, "data": order_info}
            else:
                return {"error": f"OKX API error: {response.get('msg', 'Unknown error')}"}

        except Exception as e:
            return {"error": f"Failed to get OKX order status: {str(e)}"}

    def get_spot_positions(self) -> Dict[str, Any]:
        """Get spot account balance"""
        try:
            response = self._make_request("GET", "/account/balance")
            if response.get("code") == "0" and response.get("data"):
                positions = []
                for account in response["data"]:
                    for detail in account.get("details", []):
                        if float(detail.get("eq", 0) or 0) > 0:  # 只返回有余额的币种
                            positions.append(
                                {
                                    "currency": detail["ccy"],
                                    "balance": float(detail.get("eq", 0) or 0),
                                    "available": float(detail.get("availEq", 0) or 0),
                                    "frozen": float(detail.get("frozenBal", 0) or 0),
                                }
                            )
                return {"success": True, "data": positions}
            else:
                return {"error": f"OKX API error: {response.get('msg', 'Unknown error')}"}
        except Exception as e:
            return {"error": f"Failed to get OKX spot positions: {str(e)}"}

    def get_futures_positions(self) -> Dict[str, Any]:
        """Get futures positions"""
        try:
            response = self._make_request("GET", "/account/positions")
            if response.get("code") == "0" and response.get("data"):
                positions = []
                for position in response["data"]:
                    pos_size = position.get("pos", "0")
                    if pos_size and pos_size != "0" and float(pos_size) != 0:  # 只显示有持仓的合约
                        positions.append(
                            {
                                "symbol": position["instId"],
                                "side": position["posSide"],
                                "size": float(pos_size),
                                "notional": float(position.get("notionalUsd", 0) or 0),
                                "unrealized_pnl": float(position.get("upl", 0) or 0),
                                "margin": float(position.get("margin", 0) or 0),
                            }
                        )
                return {"success": True, "data": positions}
            else:
                return {"error": f"OKX API error: {response.get('msg', 'Unknown error')}"}

        except Exception as e:
            return {"error": f"Failed to get OKX futures positions: {str(e)}"}


class BinanceClient(BaseExchange):
    """Binance exchange API client"""

    def __init__(self, config: ExchangeConfig):
        super().__init__(config)
        self.base_url = config.base_url or (
            "https://api.binance.com" if not config.sandbox else "https://testnet.binance.vision"
        )
        self.api_url = f"{self.base_url}/api/v3"

    def _generate_signature(self, query_string: str) -> str:
        """Generate Binance API signature"""
        return hmac.new(
            self.config.secret_key.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _make_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = False
    ) -> Dict[str, Any]:
        """Make request to Binance API"""
        params = params or {}

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            query_string = urlencode(params)
            signature = self._generate_signature(query_string)
            params["signature"] = signature

        headers = {"X-MBX-APIKEY": self.config.api_key} if signed else {}
        url = self.api_url + endpoint

        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params)
            else:
                response = self.session.post(url, headers=headers, params=params)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            error_info = ErrorHandler.format_api_error("Binance", e, getattr(e, "response", None))
            print(f"❌ Binance API请求失败: {ErrorHandler.get_user_friendly_message(error_info)}")
            return error_info
        except json.JSONDecodeError as e:
            error_info = ErrorHandler.format_api_error("Binance", e, response if "response" in locals() else None)
            print(f"❌ Binance数据解析失败: {ErrorHandler.get_user_friendly_message(error_info)}")
            return error_info
        except Exception as e:
            error_info = ErrorHandler.format_api_error("Binance", e)
            print(f"❌ Binance未知错误: {ErrorHandler.get_user_friendly_message(error_info)}")
            return error_info

    def get_account_info(self) -> Dict[str, Any]:
        """Get Binance account information"""
        return self._make_request("GET", "/account", signed=True)

    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """Get Binance trading fees"""
        response = self._make_request("GET", "/account", signed=True)
        maker_commission = response.get("makerCommission", 10) / 10000
        taker_commission = response.get("takerCommission", 10) / 10000

        return {"maker_fee": maker_commission, "taker_fee": taker_commission}

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get Binance ticker information"""
        try:
            response = self._make_request("GET", "/ticker/24hr", {"symbol": symbol})
            return {
                "symbol": response["symbol"],
                "price": float(response["lastPrice"]),
                "bid": float(response["bidPrice"]),
                "ask": float(response["askPrice"]),
                "volume": float(response["volume"]),
                "change": float(response["priceChangePercent"]),
            }
        except Exception as e:
            return {"error": f"Failed to get ticker: {str(e)}"}

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Get Binance kline data"""
        # Binance interval mapping
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1w",
        }

        binance_interval = interval_map.get(interval, "1m")
        response = self._make_request(
            "GET", "/klines", {"symbol": symbol, "interval": binance_interval, "limit": limit}
        )

        return [[float(x) for x in candle[:6]] for candle in response]

    def place_order(
        self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Place order on Binance"""
        order_params = {"symbol": symbol, "side": side.upper(), "type": order_type.upper(), "quantity": quantity}

        if price and order_type.upper() == "LIMIT":
            order_params["price"] = price
            order_params["timeInForce"] = "GTC"

        return self._make_request("POST", "/order", order_params, signed=True)

    def get_spot_positions(self) -> Dict[str, Any]:
        """Get spot positions/balances from Binance"""
        try:
            response = self._make_request("GET", "/account", signed=True)

            positions = {}
            balances = response.get("balances", [])

            for balance in balances:
                asset = balance.get("asset", "")
                free = float(balance.get("free", "0"))
                locked = float(balance.get("locked", "0"))
                total = free + locked

                if total > 0:  # 只显示有余额的币种
                    positions[asset] = {"currency": asset, "available": free, "frozen": locked, "total": total}

            return {"exchange": "binance", "type": "spot", "positions": positions, "timestamp": time.time()}

        except Exception as e:
            return {"error": f"Failed to get Binance spot positions: {str(e)}"}

    def get_futures_positions(self) -> Dict[str, Any]:
        """Get futures positions from Binance"""
        try:
            # Binance futures API endpoint
            futures_base_url = "https://fapi.binance.com/fapi/v2"

            # 构建请求参数
            params = {"timestamp": int(time.time() * 1000)}
            query_string = urlencode(params)
            signature = self._generate_signature(query_string)
            params["signature"] = signature

            headers = {"X-MBX-APIKEY": self.config.api_key}

            url = f"{futures_base_url}/positionRisk"
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            positions_data = response.json()

            positions = {}

            for position in positions_data:
                symbol = position.get("symbol", "")
                position_amt = float(position.get("positionAmt", "0"))

                if position_amt != 0:  # 只显示有持仓的合约
                    positions[symbol] = {
                        "symbol": symbol,
                        "side": "long" if position_amt > 0 else "short",
                        "size": abs(position_amt),
                        "contracts": position_amt,
                        "notional": float(position.get("notional", "0")),
                        "entry_price": float(position.get("entryPrice", "0")),
                        "mark_price": float(position.get("markPrice", "0")),
                        "unrealized_pnl": float(position.get("unRealizedProfit", "0")),
                        "percentage": float(position.get("percentage", "0")),
                        "leverage": float(position.get("leverage", "0")),
                        "margin_type": position.get("marginType", ""),
                        "isolated_margin": float(position.get("isolatedMargin", "0")),
                    }

            return {"exchange": "binance", "type": "futures", "positions": positions, "timestamp": time.time()}

        except Exception as e:
            return {"error": f"Failed to get Binance futures positions: {str(e)}"}
