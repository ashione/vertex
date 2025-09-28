"""
Crypto Trading Plugin for Vertex Flow

This plugin provides quantitative trading capabilities for cryptocurrency exchanges,
supporting OKX and Binance APIs for account management, trading, and technical analysis.
"""

from .backtester import Backtester, MovingAverageCrossStrategy
from .client import CryptoTradingClient
from .exchanges import BinanceClient, OKXClient
from .indicators import TechnicalIndicators
from .monitoring import AlertManager, EventLogger
from .risk_manager import RiskMonitor
from .scheduler import StrategyScheduler
from .trading import TradingEngine

__version__ = "1.0.0"
__all__ = [
    "CryptoTradingClient",
    "OKXClient",
    "BinanceClient",
    "TechnicalIndicators",
    "TradingEngine",
    "Backtester",
    "MovingAverageCrossStrategy",
    "StrategyScheduler",
    "RiskMonitor",
    "EventLogger",
    "AlertManager",
]
