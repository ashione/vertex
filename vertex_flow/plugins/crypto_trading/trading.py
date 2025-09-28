"""
Trading engine for crypto trading operations
"""

import time
from decimal import ROUND_DOWN, Decimal
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from .client import CryptoTradingClient
    from .indicators import TechnicalIndicators
    from .execution_controls import ExecutionControls, ExecutionParameters
    from .monitoring import AlertManager, EventLogger
    from .persistence import ConfigHistory, DataStore
    from .risk_manager import RiskMonitor
    from .scheduler import StrategyScheduler
except ImportError:
    from client import CryptoTradingClient
    from indicators import TechnicalIndicators
    from execution_controls import ExecutionControls, ExecutionParameters
    from monitoring import AlertManager, EventLogger
    from persistence import ConfigHistory, DataStore
    from risk_manager import RiskMonitor
    from scheduler import StrategyScheduler

try:
    from .backtester import Backtester, MovingAverageCrossStrategy, Strategy
except ImportError:
    from backtester import Backtester, MovingAverageCrossStrategy, Strategy


class TradingEngine:
    """Trading engine with risk management and order execution"""

    def __init__(self, client: CryptoTradingClient):
        self.client = client
        self.config = client.config
        trading_cfg = self.config.trading_config

        self.datastore = DataStore()
        self.logger = EventLogger(self.datastore)
        self.alerts = AlertManager(self.datastore)
        self.scheduler = StrategyScheduler(self.logger)
        self.config_history = ConfigHistory(self.datastore)
        self.config_history.snapshot("runtime", self.config.get_sanitised_config())

        execution_params = ExecutionParameters(
            slippage_buffer=trading_cfg.slippage_buffer,
            max_order_notional=trading_cfg.max_order_notional,
        )
        self.execution_controls = ExecutionControls(execution_params)

        self.risk_monitor = RiskMonitor(
            max_drawdown=trading_cfg.max_drawdown,
            max_daily_loss=trading_cfg.max_daily_loss,
            max_order_notional=trading_cfg.max_order_notional,
            logger=self.logger,
            alerts=self.alerts,
            datastore=self.datastore,
        )

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
            usdt_balance = (
                balance_info["USDT"].get("available", 0)
                if isinstance(balance_info["USDT"], dict)
                else balance_info["USDT"]
            )
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

        if side.lower() == "buy":
            stop_loss = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + take_profit_pct)
        else:  # sell
            stop_loss = entry_price * (1 + stop_loss_pct)
            take_profit = entry_price * (1 - take_profit_pct)

        return {"stop_loss": round(stop_loss, 8), "take_profit": round(take_profit, 8)}

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

            current_price = float(ticker["price"])
            raw_quantity = amount_usdt / current_price
            quantity = self.format_quantity(exchange, symbol, raw_quantity)

            prepared = self.execution_controls.prepare_order("buy", quantity, current_price)
            quantity = self.format_quantity(exchange, symbol, prepared["quantity"])
            proposed_notional = quantity * current_price

            if not self.risk_monitor.allow_order(proposed_notional):
                return {
                    "error": "Order blocked by risk controls",
                    "exchange": exchange,
                    "symbol": symbol,
                    "side": "buy",
                    "notional": proposed_notional,
                }

            # Place market buy order
            if exchange not in self.client.exchanges:
                return {"error": f"Exchange {exchange} not configured"}

            order_result = self.client.exchanges[exchange].place_order(
                symbol=symbol, side="buy", order_type="market", quantity=quantity
            )

            # Calculate stop loss and take profit
            sl_tp = self.calculate_stop_loss_take_profit(current_price, "buy")

            self.logger.log(
                "order",
                "Executed market buy",
                {
                    "exchange": exchange,
                    "symbol": symbol,
                    "notional": proposed_notional,
                    "slippage_price": prepared["price"],
                },
            )

            result = {
                "status": "success",
                "exchange": exchange,
                "symbol": symbol,
                "side": "buy",
                "type": "market",
                "quantity": quantity,
                "amount_usdt": proposed_notional,
                "estimated_price": current_price,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "order_result": order_result,
                "timestamp": time.time(),
                "risk": {"notional": proposed_notional, "slippage_price": prepared["price"]},
            }

            return result

        except Exception as e:
            return {"error": f"Failed to execute buy order: {str(e)}", "exchange": exchange, "symbol": symbol}

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

            current_price = float(ticker["price"])
            quantity = self.format_quantity(exchange, symbol, quantity)

            prepared = self.execution_controls.prepare_order("sell", quantity, current_price)
            quantity = self.format_quantity(exchange, symbol, prepared["quantity"])
            proposed_notional = quantity * current_price

            if not self.risk_monitor.allow_order(proposed_notional):
                return {
                    "error": "Order blocked by risk controls",
                    "exchange": exchange,
                    "symbol": symbol,
                    "side": "sell",
                    "notional": proposed_notional,
                }

            # Place market sell order
            if exchange not in self.client.exchanges:
                return {"error": f"Exchange {exchange} not configured"}

            order_result = self.client.exchanges[exchange].place_order(
                symbol=symbol, side="sell", order_type="market", quantity=quantity
            )

            # Calculate stop loss and take profit
            sl_tp = self.calculate_stop_loss_take_profit(current_price, "sell")

            self.logger.log(
                "order",
                "Executed market sell",
                {
                    "exchange": exchange,
                    "symbol": symbol,
                    "notional": proposed_notional,
                    "slippage_price": prepared["price"],
                },
            )

            result = {
                "status": "success",
                "exchange": exchange,
                "symbol": symbol,
                "side": "sell",
                "type": "market",
                "quantity": quantity,
                "estimated_price": current_price,
                "estimated_amount_usdt": proposed_notional,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "order_result": order_result,
                "timestamp": time.time(),
                "risk": {"notional": proposed_notional, "slippage_price": prepared["price"]},
            }

            return result

        except Exception as e:
            return {"error": f"Failed to execute sell order: {str(e)}", "exchange": exchange, "symbol": symbol}

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
            capped_quantity, capped_notional = self.execution_controls.cap_notional(quantity, price)
            quantity = self.format_quantity(exchange, symbol, capped_quantity)
            proposed_notional = quantity * price

            if not self.risk_monitor.allow_order(proposed_notional):
                return {
                    "error": "Order blocked by risk controls",
                    "exchange": exchange,
                    "symbol": symbol,
                    "side": "buy",
                    "notional": proposed_notional,
                }

            if exchange not in self.client.exchanges:
                return {"error": f"Exchange {exchange} not configured"}

            order_result = self.client.exchanges[exchange].place_order(
                symbol=symbol, side="buy", order_type="limit", quantity=quantity, price=price
            )

            # Calculate stop loss and take profit
            sl_tp = self.calculate_stop_loss_take_profit(price, "buy")

            self.logger.log(
                "order",
                "Placed limit buy",
                {
                    "exchange": exchange,
                    "symbol": symbol,
                    "notional": proposed_notional,
                    "price": price,
                },
            )

            result = {
                "status": "success",
                "exchange": exchange,
                "symbol": symbol,
                "side": "buy",
                "type": "limit",
                "quantity": quantity,
                "price": price,
                "amount_usdt": proposed_notional,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "order_result": order_result,
                "timestamp": time.time(),
                "risk": {"notional": proposed_notional},
            }

            return result

        except Exception as e:
            return {"error": f"Failed to execute limit buy order: {str(e)}", "exchange": exchange, "symbol": symbol}

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
            capped_quantity, capped_notional = self.execution_controls.cap_notional(quantity, price)
            quantity = self.format_quantity(exchange, symbol, capped_quantity)
            proposed_notional = quantity * price

            if not self.risk_monitor.allow_order(proposed_notional):
                return {
                    "error": "Order blocked by risk controls",
                    "exchange": exchange,
                    "symbol": symbol,
                    "side": "sell",
                    "notional": proposed_notional,
                }

            if exchange not in self.client.exchanges:
                return {"error": f"Exchange {exchange} not configured"}

            order_result = self.client.exchanges[exchange].place_order(
                symbol=symbol, side="sell", order_type="limit", quantity=quantity, price=price
            )

            # Calculate stop loss and take profit
            sl_tp = self.calculate_stop_loss_take_profit(price, "sell")

            self.logger.log(
                "order",
                "Placed limit sell",
                {
                    "exchange": exchange,
                    "symbol": symbol,
                    "notional": proposed_notional,
                    "price": price,
                },
            )

            result = {
                "status": "success",
                "exchange": exchange,
                "symbol": symbol,
                "side": "sell",
                "type": "limit",
                "quantity": quantity,
                "price": price,
                "amount_usdt": proposed_notional,
                "stop_loss": sl_tp["stop_loss"],
                "take_profit": sl_tp["take_profit"],
                "order_result": order_result,
                "timestamp": time.time(),
                "risk": {"notional": proposed_notional},
            }

            return result

        except Exception as e:
            return {"error": f"Failed to execute limit sell order: {str(e)}", "exchange": exchange, "symbol": symbol}

    def schedule_strategy(self, name: str, interval: float, callback: Callable[[], Any]) -> None:
        """Register a named strategy callback with the cooperative scheduler."""
        self.scheduler.add_task(name, interval, callback)

    def run_scheduler(self, duration: float, poll_interval: float = 1.0) -> None:
        """Run the scheduler loop for a bounded amount of time."""
        self.scheduler.run_for(duration, poll_interval)

    def run_backtest(
        self,
        exchange: str,
        symbol: str,
        strategy: Optional[Strategy] = None,
        interval: str = "1h",
        limit: int = 200,
        initial_equity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Fetch historical data and execute a simple backtest."""
        candles = self.client.get_klines(exchange, symbol, interval, limit)
        if not candles:
            return {"error": "No historical data available"}

        runner = strategy or MovingAverageCrossStrategy()
        backtester = Backtester(
            strategy=runner,
            initial_equity=initial_equity or self.calculate_position_size(exchange, symbol),
        )
        result = backtester.run(candles)
        payload = {
            "strategy": result.strategy,
            "starting_equity": result.starting_equity,
            "ending_equity": result.ending_equity,
            "total_return": result.total_return,
            "max_drawdown": result.max_drawdown,
            "trade_count": len(result.trades),
            "trades": [trade.__dict__ for trade in result.trades],
        }
        self.logger.log(
            "backtest",
            f"Backtest finished for {symbol}",
            {
                "strategy": result.strategy,
                "return": payload["total_return"],
                "max_drawdown": result.max_drawdown,
            },
        )
        return payload

    def capture_equity_snapshot(self, exchange: str) -> Dict[str, Any]:
        """Update the risk monitor with the latest balance-derived equity."""
        account = self.client.get_account_info(exchange)
        if "error" in account:
            return {"error": account["error"], "exchange": exchange}

        balances = account.get("balances", {})
        usdt = balances.get("USDT")
        equity = 0.0
        if isinstance(usdt, dict):
            equity = float(usdt.get("total", usdt.get("available", 0.0)))
        elif isinstance(usdt, (int, float)):
            equity = float(usdt)

        self.risk_monitor.update_equity(equity)
        snapshot = {
            "exchange": exchange,
            "equity": equity,
            "timestamp": time.time(),
        }
        self.logger.log("equity", f"Equity snapshot for {exchange}", {"equity": equity})
        return snapshot

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
                    "message": "No clear trading signal, holding position",
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
                    quantity = amount_usdt / float(ticker["price"])
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
                        "current_price": indicators.get("current_price"),
                    },
                }

            return result

        except Exception as e:
            return {"error": f"Failed to execute auto trade: {str(e)}", "exchange": exchange, "symbol": symbol}

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
                    "overall_signal": signals.get("overall", "HOLD"),
                },
                "risk_management": {
                    "recommended_position_size_usdt": position_size,
                    "risk_percentage": self.config.trading_config.risk_percentage,
                    "stop_loss_percentage": self.config.trading_config.stop_loss_percentage,
                    "take_profit_percentage": self.config.trading_config.take_profit_percentage,
                },
                "account_balance": balance,
                "timestamp": time.time(),
            }

            return summary

        except Exception as e:
            return {"error": f"Failed to generate trading summary: {str(e)}", "exchange": exchange, "symbol": symbol}
