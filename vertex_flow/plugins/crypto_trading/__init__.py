"""
Crypto Trading Plugin for Vertex Flow

This plugin provides quantitative trading capabilities for cryptocurrency exchanges,
supporting OKX and Binance APIs for account management, trading, and technical analysis.
"""

from .client import CryptoTradingClient
from .exchanges import OKXClient, BinanceClient
from .indicators import TechnicalIndicators
from .trading import TradingEngine

__version__ = "1.0.0"
__all__ = ["CryptoTradingClient", "OKXClient", "BinanceClient", "TechnicalIndicators", "TradingEngine"]