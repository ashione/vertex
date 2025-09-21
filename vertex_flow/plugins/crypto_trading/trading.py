"""
Trading engine for crypto trading operations
"""

import time
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal, ROUND_DOWN

try:
    from .client import CryptoTradingClient
    from .indicators import TechnicalIndicators
except ImportError:
    from client import CryptoTradingClient
    from indicators import TechnicalIndicators


class TradingEngine:
    """Trading engine with risk management and order execution"""
    
    def __init__(self, client: CryptoTradingClient):
        self.client = client
        self.config = client.config
    
    def calculate_position_size(self, exchange: str, symbol: str, risk_percentage: float = None) -> float:
        """
        Calculate position size based on risk management rules
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            risk_percentage: Risk percentage of total balance (default from config)
            
        Returns:
            Position size in base currency
        """
        if risk_percentage is None:
            risk_percentage = self.config.trading_config.risk_percentage
        
        # Get account balance
        balance_info = self.client.get_balance(exchange)
        if isinstance(balance_info, dict) and "USDT" in balance_info:
            usdt_balance = balance_info["USDT"].get("available", 0) if isinstance(balance_info["USDT"], dict) else balance_info["USDT"]
        else:
            usdt_balance = 1000  # Default fallback
        
        # Calculate position size
        risk_amount = usdt_balance * risk_percentage
        max_position = min(risk_amount, self.config.trading_config.max_position_size)
        
        return max_position
    
    def calculate_stop_loss_take_profit(self, entry_price: float, side: str) -> Dict[str, float]:
        """
        Calculate stop loss and take profit levels
        
        Args:
            entry_price: Entry price
            side: 'buy' or 'sell'
            
        Returns:
            Dictionary with stop_loss and take_profit prices
        """
        stop_loss_pct = self.config.trading_config.stop_loss_percentage
        take_profit_pct = self.config.trading_config.take_profit_percentage
        
        if side.lower() == 'buy':
            stop_loss = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + take_profit_pct)
        else:  # sell
            stop_loss = entry_price * (1 + stop_loss_pct)
            take_profit = entry_price * (1 - take_profit_pct)
        
        return {
            'stop_loss': round(stop_loss, 8),
            'take_profit': round(take_profit, 8)
        }
    
    def format_quantity(self, exchange: str, symbol: str, quantity: float) -> float:
        """Format quantity according to exchange requirements"""
        # This is a simplified version - in production, you'd get this from exchange info
        if exchange == "binance":
            # Binance typically requires specific decimal places
            return round(quantity, 6)
        elif exchange == "okx":
            # OKX has different requirements
            return round(quantity, 8)
        
        return round(quantity, 8)
    
    def buy_market(self, exchange: str, symbol: str, amount_usdt: float) -> Dict[str, Any]:
        """
        Execute market buy order
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            amount_usdt: Amount in USDT to buy
            
        Returns:
            Order result dictionary
        """
        try:
            # Get current price
            ticker = self.client.get_ticker(exchange, symbol)
            if "error" in ticker:
                return {"error": f"Failed to get ticker: {ticker['error']}"}
            
            current_price = ticker["price"]
            quantity = amount_usdt / current_price
            quantity = self.format_quantity(exchange, symbol, quantity)
            
            # Place market buy order
            if exchange not in self.client.exchanges:
                return {"error": f"Exchange {exchange} not configured"}
            
            order_result = self.client.exchanges[exchange].place_order(
                symbol=symbol,
                side="buy",
                order_type="market",
                quantity=quantity
            )
            
            # Calculate stop loss and take profit
            sl_tp = self.calculate_stop_loss_take_profit(current_price, "buy")
            
            result = {
                "status": "success",
                "exchange": exchange,
                "symbol": symbol,
                "side": "buy",
                "type": "market",
                "quantity": quantity,
                "amount_usdt": amount_usdt,
                "estimated_price": current_price,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "order_result": order_result,
                "timestamp": time.time()
            }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to execute buy order: {str(e)}",
                "exchange": exchange,
                "symbol": symbol
            }
    
    def sell_market(self, exchange: str, symbol: str, quantity: float) -> Dict[str, Any]:
        """
        Execute market sell order
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            quantity: Quantity to sell
            
        Returns:
            Order result dictionary
        """
        try:
            # Get current price
            ticker = self.client.get_ticker(exchange, symbol)
            if "error" in ticker:
                return {"error": f"Failed to get ticker: {ticker['error']}"}
            
            current_price = ticker["price"]
            quantity = self.format_quantity(exchange, symbol, quantity)
            
            # Place market sell order
            if exchange not in self.client.exchanges:
                return {"error": f"Exchange {exchange} not configured"}
            
            order_result = self.client.exchanges[exchange].place_order(
                symbol=symbol,
                side="sell",
                order_type="market",
                quantity=quantity
            )
            
            # Calculate stop loss and take profit
            sl_tp = self.calculate_stop_loss_take_profit(current_price, "sell")
            
            result = {
                "status": "success",
                "exchange": exchange,
                "symbol": symbol,
                "side": "sell",
                "type": "market",
                "quantity": quantity,
                "estimated_price": current_price,
                "estimated_amount_usdt": quantity * current_price,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "order_result": order_result,
                "timestamp": time.time()
            }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to execute sell order: {str(e)}",
                "exchange": exchange,
                "symbol": symbol
            }
    
    def buy_limit(self, exchange: str, symbol: str, quantity: float, price: float) -> Dict[str, Any]:
        """
        Execute limit buy order
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            quantity: Quantity to buy
            price: Limit price
            
        Returns:
            Order result dictionary
        """
        try:
            quantity = self.format_quantity(exchange, symbol, quantity)
            
            if exchange not in self.client.exchanges:
                return {"error": f"Exchange {exchange} not configured"}
            
            order_result = self.client.exchanges[exchange].place_order(
                symbol=symbol,
                side="buy",
                order_type="limit",
                quantity=quantity,
                price=price
            )
            
            # Calculate stop loss and take profit
            sl_tp = self.calculate_stop_loss_take_profit(price, "buy")
            
            result = {
                "status": "success",
                "exchange": exchange,
                "symbol": symbol,
                "side": "buy",
                "type": "limit",
                "quantity": quantity,
                "price": price,
                "amount_usdt": quantity * price,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "order_result": order_result,
                "timestamp": time.time()
            }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to execute limit buy order: {str(e)}",
                "exchange": exchange,
                "symbol": symbol
            }
    
    def sell_limit(self, exchange: str, symbol: str, quantity: float, price: float) -> Dict[str, Any]:
        """
        Execute limit sell order
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            quantity: Quantity to sell
            price: Limit price
            
        Returns:
            Order result dictionary
        """
        try:
            quantity = self.format_quantity(exchange, symbol, quantity)
            
            if exchange not in self.client.exchanges:
                return {"error": f"Exchange {exchange} not configured"}
            
            order_result = self.client.exchanges[exchange].place_order(
                symbol=symbol,
                side="sell",
                order_type="limit",
                quantity=quantity,
                price=price
            )
            
            # Calculate stop loss and take profit
            sl_tp = self.calculate_stop_loss_take_profit(price, "sell")
            
            result = {
                "status": "success",
                "exchange": exchange,
                "symbol": symbol,
                "side": "sell",
                "type": "limit",
                "quantity": quantity,
                "price": price,
                "amount_usdt": quantity * price,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "order_result": order_result,
                "timestamp": time.time()
            }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to execute limit sell order: {str(e)}",
                "exchange": exchange,
                "symbol": symbol
            }
    
    def auto_trade_by_signals(self, exchange: str, symbol: str, amount_usdt: float = None) -> Dict[str, Any]:
        """
        Execute trade based on technical analysis signals
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            amount_usdt: Amount to trade (optional, uses risk management if not provided)
            
        Returns:
            Trade result dictionary
        """
        try:
            # Get klines data
            klines = self.client.get_klines(exchange, symbol, "1h", 100)
            if not klines:
                return {"error": "Failed to get klines data"}
            
            # Calculate indicators
            indicators = TechnicalIndicators.calculate_all_indicators(klines)
            if "error" in indicators:
                return {"error": f"Failed to calculate indicators: {indicators['error']}"}
            
            # Get trading signals
            signals = TechnicalIndicators.get_trading_signals(indicators)
            overall_signal = signals.get("overall", "HOLD")
            
            if overall_signal == "HOLD":
                return {
                    "status": "no_action",
                    "signal": overall_signal,
                    "signals": signals,
                    "indicators": indicators,
                    "message": "No clear trading signal, holding position"
                }
            
            # Calculate position size if not provided
            if amount_usdt is None:
                amount_usdt = self.calculate_position_size(exchange, symbol)
            
            # Execute trade based on signal
            if overall_signal == "BUY":
                result = self.buy_market(exchange, symbol, amount_usdt)
            else:  # SELL
                # For sell signal, we need to determine quantity to sell
                # This is simplified - in practice, you'd track your positions
                ticker = self.client.get_ticker(exchange, symbol)
                if "error" not in ticker:
                    quantity = amount_usdt / ticker["price"]
                    result = self.sell_market(exchange, symbol, quantity)
                else:
                    result = {"error": "Failed to get current price for sell order"}
            
            # Add signal information to result
            if "error" not in result:
                result["signal_info"] = {
                    "overall_signal": overall_signal,
                    "signals": signals,
                    "key_indicators": {
                        "rsi": indicators.get("rsi"),
                        "macd": indicators.get("macd"),
                        "current_price": indicators.get("current_price")
                    }
                }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to execute auto trade: {str(e)}",
                "exchange": exchange,
                "symbol": symbol
            }
    
    def get_trading_summary(self, exchange: str, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive trading summary including market data and signals
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            
        Returns:
            Trading summary dictionary
        """
        try:
            # Get market data
            ticker = self.client.get_ticker(exchange, symbol)
            klines = self.client.get_klines(exchange, symbol, "1h", 100)
            
            # Calculate indicators and signals
            indicators = TechnicalIndicators.calculate_all_indicators(klines)
            signals = TechnicalIndicators.get_trading_signals(indicators)
            
            # Get account info
            balance = self.client.get_balance(exchange)
            
            # Calculate recommended position size
            position_size = self.calculate_position_size(exchange, symbol)
            
            summary = {
                "exchange": exchange,
                "symbol": symbol,
                "market_data": ticker,
                "technical_analysis": {
                    "indicators": indicators,
                    "signals": signals,
                    "overall_signal": signals.get("overall", "HOLD")
                },
                "risk_management": {
                    "recommended_position_size_usdt": position_size,
                    "risk_percentage": self.config.trading_config.risk_percentage,
                    "stop_loss_percentage": self.config.trading_config.stop_loss_percentage,
                    "take_profit_percentage": self.config.trading_config.take_profit_percentage
                },
                "account_balance": balance,
                "timestamp": time.time()
            }
            
            return summary
            
        except Exception as e:
            return {
                "error": f"Failed to generate trading summary: {str(e)}",
                "exchange": exchange,
                "symbol": symbol
            }