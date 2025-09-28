"""Risk monitoring utilities for strategy and execution oversight."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from monitoring import AlertManager, EventLogger
from persistence import DataStore


@dataclass
class RiskState:
    """Keeps track of rolling performance and exposure."""

    equity_high: float = 0.0
    equity_low: float = 0.0
    cumulative_pnl: float = 0.0
    daily_loss: float = 0.0
    last_update: Optional[str] = None
    kill_switch: bool = False


class RiskMonitor:
    """Evaluate orders and equity swings against configuration thresholds."""

    def __init__(
        self,
        max_drawdown: float,
        max_daily_loss: float,
        max_order_notional: float,
        logger: Optional[EventLogger] = None,
        alerts: Optional[AlertManager] = None,
        datastore: Optional[DataStore] = None,
    ) -> None:
        self.max_drawdown = max_drawdown
        self.max_daily_loss = max_daily_loss
        self.max_order_notional = max_order_notional
        self.logger = logger
        self.alerts = alerts
        self.datastore = datastore
        self.state = RiskState()

    def _emit_alert(self, severity: str, message: str, extra: Dict[str, Any]) -> None:
        if self.logger:
            self.logger.log("risk", message, extra)
        if self.alerts:
            self.alerts.notify(severity, message, extra)

    def allow_order(self, notional: float) -> bool:
        """Check if the proposed order stays within per-trade limits."""
        if self.state.kill_switch:
            self._emit_alert("critical", "Order rejected: kill switch active", {"notional": notional})
            return False
        if notional > self.max_order_notional:
            self._emit_alert(
                "warning",
                "Order size exceeds configured limit",
                {"notional": notional, "limit": self.max_order_notional},
            )
            return False
        return True

    def update_equity(self, equity: float) -> None:
        """Track equity curve and evaluate drawdown / daily loss."""
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        if self.state.equity_high == 0.0:
            self.state.equity_high = equity
            self.state.equity_low = equity
        else:
            self.state.equity_high = max(self.state.equity_high, equity)
            self.state.equity_low = min(self.state.equity_low, equity)

        drawdown = 0.0
        if self.state.equity_high > 0:
            drawdown = (self.state.equity_high - equity) / self.state.equity_high
        daily_loss = max(0.0, self.state.equity_high - equity)

        self.state.daily_loss = daily_loss
        self.state.last_update = now

        record = {
            "timestamp": now,
            "equity": equity,
            "drawdown": drawdown,
            "daily_loss": daily_loss,
        }
        if self.datastore:
            self.datastore.record_metric({"metric": "equity", **record})

        if drawdown >= self.max_drawdown and not self.state.kill_switch:
            self.state.kill_switch = True
            self._emit_alert("critical", "Max drawdown breached; kill switch engaged", record)
        elif daily_loss >= self.max_daily_loss:
            self._emit_alert("warning", "Daily loss threshold breached", record)

    def record_trade(self, trade: Dict[str, Any]) -> None:
        """Record realised PnL from completed trades."""
        pnl = float(trade.get("pnl", 0.0))
        self.state.cumulative_pnl += pnl
        if self.datastore:
            self.datastore.record_trade(trade)
        if pnl < 0 and abs(pnl) > self.max_order_notional * 0.1:
            self._emit_alert("info", "Large loss recorded", {"pnl": pnl, "trade": trade})

    def reset_kill_switch(self) -> None:
        self.state.kill_switch = False
        self._emit_alert("info", "Kill switch reset", {})

