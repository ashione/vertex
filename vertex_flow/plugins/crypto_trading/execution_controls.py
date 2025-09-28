"""Execution helpers for slippage control and order preparation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ExecutionParameters:
    """Container for execution-specific settings."""

    slippage_buffer: float = 0.0005  # 5 bps
    max_order_notional: float = 5000.0


class ExecutionControls:
    """Utility class to sanitize order parameters before submission."""

    def __init__(self, params: ExecutionParameters) -> None:
        self.params = params

    def apply_slippage(self, price: float, side: str) -> float:
        """Apply a conservative slippage buffer to the target price."""
        buffer = self.params.slippage_buffer
        if side.lower() == "buy":
            return price * (1 + buffer)
        return price * (1 - buffer)

    def cap_notional(self, quantity: float, price: float) -> Tuple[float, float]:
        """Reduce quantity so that notional stays within limits."""
        notional = quantity * price
        if notional <= self.params.max_order_notional:
            return quantity, notional
        scale = self.params.max_order_notional / notional
        adjusted_qty = quantity * scale
        return adjusted_qty, self.params.max_order_notional

    def prepare_order(self, side: str, quantity: float, price: float) -> Dict[str, float]:
        """Return sanitized quantity and safety-adjusted price."""
        safe_price = self.apply_slippage(price, side)
        safe_quantity, capped_notional = self.cap_notional(quantity, safe_price)
        return {
            "quantity": safe_quantity,
            "price": safe_price,
            "notional": capped_notional,
        }

