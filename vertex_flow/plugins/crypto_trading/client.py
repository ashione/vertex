"""
Main crypto trading client that integrates all exchange functionalities
"""

import time
from typing import Any, Dict, List, Optional, Union

try:
    from .config import CryptoTradingConfig
    from .exchanges import BaseExchange, BinanceClient, OKXClient
except ImportError:
    from config import CryptoTradingConfig
    from exchanges import BaseExchange, BinanceClient, OKXClient


class CryptoTradingClient:
    """Main client for crypto trading operations"""

    def __init__(self, config: Optional[CryptoTradingConfig] = None):
        self.config = config or CryptoTradingConfig()
        self.exchanges: Dict[str, BaseExchange] = {}
        self._initialize_exchanges()

    def _initialize_exchanges(self):
        """Initialize exchange clients based on configuration"""
        if self.config.okx_config:
            self.exchanges["okx"] = OKXClient(self.config.okx_config)

        if self.config.binance_config:
            self.exchanges["binance"] = BinanceClient(self.config.binance_config)

    def get_available_exchanges(self) -> List[str]:
        """Get list of available exchanges"""
        return list(self.exchanges.keys())

    def get_account_info(self, exchange: str) -> Dict[str, Any]:
        """
        Get account information from specified exchange

        Args:
            exchange: Exchange name ('okx' or 'binance')

        Returns:
            Account information dictionary
        """
        if exchange not in self.exchanges:
            raise ValueError(f"Exchange '{exchange}' not configured or not supported")

        try:
            account_info = self.exchanges[exchange].get_account_info()
            return self._normalize_account_info(exchange, account_info)
        except Exception as e:
            return {"error": str(e), "exchange": exchange}

    def get_all_account_info(self) -> Dict[str, Dict[str, Any]]:
        """Get account information from all configured exchanges"""
        results = {}
        for exchange_name in self.exchanges:
            results[exchange_name] = self.get_account_info(exchange_name)
        return results

    def get_trading_fees(self, exchange: str, symbol: str) -> Dict[str, float]:
        """
        Get trading fees for a symbol on specified exchange

        Args:
            exchange: Exchange name ('okx' or 'binance')
            symbol: Trading symbol (e.g., 'BTC-USDT' for OKX, 'BTCUSDT' for Binance)

        Returns:
            Dictionary with maker_fee and taker_fee
        """
        if exchange not in self.exchanges:
            raise ValueError(f"Exchange '{exchange}' not configured or not supported")

        try:
            return self.exchanges[exchange].get_trading_fees(symbol)
        except Exception as e:
            return {"error": str(e), "maker_fee": 0, "taker_fee": 0}

    def get_ticker(self, exchange: str, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a symbol

        Args:
            exchange: Exchange name ('okx' or 'binance')
            symbol: Trading symbol

        Returns:
            Ticker information dictionary
        """
        if exchange not in self.exchanges:
            raise ValueError(f"Exchange '{exchange}' not configured or not supported")

        try:
            return self.exchanges[exchange].get_ticker(symbol)
        except Exception as e:
            return {"error": str(e), "exchange": exchange, "symbol": symbol}

    def get_klines(self, exchange: str, symbol: str, interval: str = "1h", limit: int = 100) -> List[List]:
        """
        Get kline/candlestick data

        Args:
            exchange: Exchange name ('okx' or 'binance')
            symbol: Trading symbol
            interval: Time interval ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')
            limit: Number of klines to retrieve

        Returns:
            List of kline data [timestamp, open, high, low, close, volume]
        """
        if exchange not in self.exchanges:
            raise ValueError(f"Exchange '{exchange}' not configured or not supported")

        try:
            return self.exchanges[exchange].get_klines(symbol, interval, limit)
        except Exception as e:
            print(f"Error getting klines: {e}")
            return []

    def get_balance(self, exchange: str, currency: Optional[str] = None) -> Union[Dict[str, float], float]:
        """
        Get balance for specific currency or all currencies

        Args:
            exchange: Exchange name
            currency: Currency symbol (optional, if None returns all balances)

        Returns:
            Balance information
        """
        account_info = self.get_account_info(exchange)

        if "error" in account_info:
            return 0.0 if currency else {}

        balances = account_info.get("balances", {})

        if currency:
            return balances.get(currency, 0.0)

        return balances

    def _normalize_account_info(self, exchange: str, raw_info: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize account information across different exchanges"""
        normalized = {"exchange": exchange, "balances": {}, "total_value_usdt": 0.0, "raw_data": raw_info}

        try:
            if exchange == "okx":
                if raw_info.get("data"):
                    for balance_info in raw_info["data"]:
                        for detail in balance_info.get("details", []):
                            currency = detail.get("ccy")
                            available = float(detail.get("availBal", 0))
                            frozen = float(detail.get("frozenBal", 0))

                            if available > 0 or frozen > 0:
                                normalized["balances"][currency] = {
                                    "available": available,
                                    "frozen": frozen,
                                    "total": available + frozen,
                                }

            elif exchange == "binance":
                for balance in raw_info.get("balances", []):
                    currency = balance.get("asset")
                    free = float(balance.get("free", 0))
                    locked = float(balance.get("locked", 0))

                    if free > 0 or locked > 0:
                        normalized["balances"][currency] = {"available": free, "frozen": locked, "total": free + locked}

        except Exception as e:
            normalized["error"] = f"Error normalizing account info: {str(e)}"

        return normalized

    def get_exchange_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all configured exchanges"""
        status = {}

        for exchange_name in self.exchanges:
            try:
                # Test connection by getting account info
                account_info = self.get_account_info(exchange_name)
                status[exchange_name] = {
                    "connected": "error" not in account_info,
                    "error": account_info.get("error"),
                    "last_check": "now",
                }
            except Exception as e:
                status[exchange_name] = {"connected": False, "error": str(e), "last_check": "now"}

        return status

    def get_spot_positions(self, exchange: str) -> Dict[str, Any]:
        """
        Get spot positions for a specific exchange

        Args:
            exchange: Exchange name ('okx' or 'binance')

        Returns:
            Spot positions information
        """
        if exchange not in self.exchanges:
            return {"error": f"Exchange '{exchange}' not configured or not supported"}

        try:
            return self.exchanges[exchange].get_spot_positions()
        except Exception as e:
            return {"error": f"Failed to get spot positions: {str(e)}"}

    def get_futures_positions(self, exchange: str) -> Dict[str, Any]:
        """
        Get futures positions for a specific exchange

        Args:
            exchange: Exchange name ('okx' or 'binance')

        Returns:
            Futures positions information
        """
        if exchange not in self.exchanges:
            return {"error": f"Exchange '{exchange}' not configured or not supported"}

        try:
            return self.exchanges[exchange].get_futures_positions()
        except Exception as e:
            return {"error": f"Failed to get futures positions: {str(e)}"}

    def get_all_positions(self, exchange: str = None) -> Dict[str, Any]:
        """
        Get both spot and futures positions for one or all exchanges

        Args:
            exchange: Exchange name (optional, if None returns all exchanges)

        Returns:
            All positions information
        """
        if exchange:
            # Get positions for specific exchange
            if exchange not in self.exchanges:
                return {"error": f"Exchange '{exchange}' not configured or not supported"}

            spot_positions = self.get_spot_positions(exchange)
            futures_positions = self.get_futures_positions(exchange)

            return {
                "exchange": exchange,
                "spot": spot_positions,
                "futures": futures_positions,
                "timestamp": time.time(),
            }
        else:
            # Get positions for all exchanges
            all_positions = {}

            for exchange_name in self.exchanges:
                spot_positions = self.get_spot_positions(exchange_name)
                futures_positions = self.get_futures_positions(exchange_name)

                all_positions[exchange_name] = {"spot": spot_positions, "futures": futures_positions}

            return {"all_exchanges": all_positions, "timestamp": time.time()}
