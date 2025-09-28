"""Naive backtesting harness for quantitative strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from risk_manager import RiskMonitor


class Strategy(Protocol):
    """Minimal strategy protocol used by the backtester."""

    name: str

    def on_bar(self, index: int, candles: List[List[float]]) -> Dict[str, Any]:
        """Return an action dict such as {"action": "buy", "size": 1}."""
        ...


@dataclass
class BacktestTrade:
    timestamp: float
    action: str
    price: float
    size: float
    pnl: float = 0.0


@dataclass
class BacktestResult:
    strategy: str
    starting_equity: float
    ending_equity: float
    trades: List[BacktestTrade] = field(default_factory=list)
    max_drawdown: float = 0.0

    @property
    def total_return(self) -> float:
        if self.starting_equity == 0:
            return 0.0
        return (self.ending_equity - self.starting_equity) / self.starting_equity


class Backtester:
    """Runs a simple long-only backtest using OHLC candles."""

    def __init__(
        self,
        strategy: Strategy,
        initial_equity: float = 1000.0,
        fee_rate: float = 0.0005,
        risk_monitor: Optional[RiskMonitor] = None,
    ) -> None:
        self.strategy = strategy
        self.initial_equity = initial_equity
        self.fee_rate = fee_rate
        self.risk_monitor = risk_monitor

    def run(self, candles: List[List[float]]) -> BacktestResult:
        cash = self.initial_equity
        position = 0.0
        entry_price = 0.0
        peak_equity = cash
        max_drawdown = 0.0
        trades: List[BacktestTrade] = []

        for idx, candle in enumerate(candles):
            if len(candle) < 5:
                continue
            timestamp, _, _, _, close, _ = candle[:6]
            close = float(close)
            action = self.strategy.on_bar(idx, candles)
            if not action:
                continue
            side = action.get("action")
            size = float(action.get("size", 0))
            if side not in {"buy", "sell"} or size <= 0:
                continue

            if side == "buy" and cash > 0:
                price = close
                cost = price * size
                fee = cost * self.fee_rate
                total_cost = cost + fee
                if cash >= total_cost:
                    position += size
                    cash -= total_cost
                    entry_price = price
                    trades.append(BacktestTrade(timestamp=timestamp, action="buy", price=price, size=size, pnl=0))
            elif side == "sell" and position >= size:
                price = close
                proceeds = price * size
                fee = proceeds * self.fee_rate
                realized = proceeds - fee
                pnl = (price - entry_price) * size - fee
                cash += realized
                position -= size
                trades.append(BacktestTrade(timestamp=timestamp, action="sell", price=price, size=size, pnl=pnl))
                if self.risk_monitor:
                    self.risk_monitor.record_trade({"timestamp": timestamp, "pnl": pnl, "action": "backtest"})

            equity = cash + position * close
            peak_equity = max(peak_equity, equity)
            drawdown = 0.0
            if peak_equity > 0:
                drawdown = (peak_equity - equity) / peak_equity
            if self.risk_monitor:
                self.risk_monitor.update_equity(equity)
            max_drawdown = max(max_drawdown, drawdown)

        ending_equity = cash + position * float(candles[-1][4]) if candles else cash
        result = BacktestResult(
            strategy=self.strategy.name,
            starting_equity=self.initial_equity,
            ending_equity=ending_equity,
            trades=trades,
            max_drawdown=max_drawdown if candles else 0.0,
        )
        return result


class MovingAverageCrossStrategy:
    """Very simple MA cross strategy for demonstrations."""

    def __init__(self, fast: int = 5, slow: int = 20, name: str = "ma_cross") -> None:
        self.fast = fast
        self.slow = slow
        self.name = name

    def on_bar(self, index: int, candles: List[List[float]]) -> Dict[str, Any]:
        if index < self.slow:
            return {}
        closes = [candle[4] for candle in candles[: index + 1]]
        fast_ma = sum(closes[-self.fast :]) / self.fast
        slow_ma = sum(closes[-self.slow :]) / self.slow
        if fast_ma > slow_ma:
            return {"action": "buy", "size": 1.0}
        elif fast_ma < slow_ma:
            return {"action": "sell", "size": 1.0}
        return {}
