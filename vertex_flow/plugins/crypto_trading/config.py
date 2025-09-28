"""
Configuration management for crypto trading plugin
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


@dataclass
class ExchangeConfig:
    """Exchange configuration"""

    api_key: str
    secret_key: str
    passphrase: Optional[str] = None  # For OKX
    sandbox: bool = False
    base_url: Optional[str] = None


@dataclass
class TradingConfig:
    """Trading configuration"""

    default_symbol: str = "BTC-USDT"
    max_position_size: float = 1000.0
    risk_percentage: float = 0.02
    stop_loss_percentage: float = 0.05
    take_profit_percentage: float = 0.10
    slippage_buffer: float = 0.0005
    max_order_notional: float = 5000.0
    max_drawdown: float = 0.2
    max_daily_loss: float = 200.0


class CryptoTradingConfig:
    """Main configuration class for crypto trading plugin"""

    def __init__(self):
        self.okx_config: Optional[ExchangeConfig] = None
        self.binance_config: Optional[ExchangeConfig] = None
        self.trading_config = TradingConfig()
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables"""
        # OKX Configuration
        okx_api_key = os.getenv("OKX_API_KEY")
        okx_secret_key = os.getenv("OKX_SECRET_KEY")
        okx_passphrase = os.getenv("OKX_PASSPHRASE")

        if okx_api_key and okx_secret_key and okx_passphrase:
            self.okx_config = ExchangeConfig(
                api_key=okx_api_key,
                secret_key=okx_secret_key,
                passphrase=okx_passphrase,
                sandbox=os.getenv("OKX_SANDBOX", "false").lower() == "true",
            )

        # Binance Configuration
        binance_api_key = os.getenv("BINANCE_API_KEY")
        binance_secret_key = os.getenv("BINANCE_SECRET_KEY")

        if binance_api_key and binance_secret_key:
            self.binance_config = ExchangeConfig(
                api_key=binance_api_key,
                secret_key=binance_secret_key,
                sandbox=os.getenv("BINANCE_SANDBOX", "false").lower() == "true",
            )

        # Trading Configuration
        default_symbol = os.getenv("DEFAULT_SYMBOL")
        if default_symbol:
            self.trading_config.default_symbol = default_symbol

        max_position_size = os.getenv("MAX_POSITION_SIZE")
        if max_position_size:
            try:
                self.trading_config.max_position_size = float(max_position_size)
            except ValueError:
                pass

        risk_percentage = os.getenv("RISK_PERCENTAGE")
        if risk_percentage:
            try:
                self.trading_config.risk_percentage = float(risk_percentage)
            except ValueError:
                pass

        stop_loss_percentage = os.getenv("STOP_LOSS_PERCENTAGE")
        if stop_loss_percentage:
            try:
                self.trading_config.stop_loss_percentage = float(stop_loss_percentage)
            except ValueError:
                pass

        take_profit_percentage = os.getenv("TAKE_PROFIT_PERCENTAGE")
        if take_profit_percentage:
            try:
                self.trading_config.take_profit_percentage = float(take_profit_percentage)
            except ValueError:
                pass

        slippage_buffer = os.getenv("SLIPPAGE_BUFFER")
        if slippage_buffer:
            try:
                self.trading_config.slippage_buffer = float(slippage_buffer)
            except ValueError:
                pass

        max_order_notional = os.getenv("MAX_ORDER_NOTIONAL")
        if max_order_notional:
            try:
                self.trading_config.max_order_notional = float(max_order_notional)
            except ValueError:
                pass

        max_drawdown = os.getenv("MAX_DRAWDOWN")
        if max_drawdown:
            try:
                self.trading_config.max_drawdown = float(max_drawdown)
            except ValueError:
                pass

        max_daily_loss = os.getenv("MAX_DAILY_LOSS")
        if max_daily_loss:
            try:
                self.trading_config.max_daily_loss = float(max_daily_loss)
            except ValueError:
                pass

    def set_okx_config(self, api_key: str, secret_key: str, passphrase: str, sandbox: bool = False):
        """Set OKX configuration"""
        self.okx_config = ExchangeConfig(api_key=api_key, secret_key=secret_key, passphrase=passphrase, sandbox=sandbox)

    def set_binance_config(self, api_key: str, secret_key: str, sandbox: bool = False):
        """Set Binance configuration"""
        self.binance_config = ExchangeConfig(api_key=api_key, secret_key=secret_key, sandbox=sandbox)

    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            "okx": self.okx_config.__dict__ if self.okx_config else None,
            "binance": self.binance_config.__dict__ if self.binance_config else None,
            "trading": self.trading_config.__dict__,
        }

    def get_sanitised_config(self) -> Dict[str, Any]:
        """Return a copy of the configuration with secrets masked."""
        def mask(value: Optional[ExchangeConfig]) -> Optional[Dict[str, Any]]:
            if not value:
                return None
            data = value.__dict__.copy()
            for key in ("api_key", "secret_key", "passphrase"):
                if key in data and data[key]:
                    data[key] = "***masked***"
            return data

        return {
            "okx": mask(self.okx_config),
            "binance": mask(self.binance_config),
            "trading": self.trading_config.__dict__.copy(),
        }
