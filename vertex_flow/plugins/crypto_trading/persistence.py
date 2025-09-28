"""Lightweight persistence utilities for the crypto trading plugin."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


@dataclass
class ConfigSnapshot:
    """Serializable snapshot of runtime configuration."""

    label: str
    created_at: str
    payload: Dict[str, Any]

    @classmethod
    def from_dict(cls, label: str, payload: Dict[str, Any]) -> "ConfigSnapshot":
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        return cls(label=label, created_at=timestamp, payload=payload)


class DataStore:
    """Simple JSON-lines persistence for trades, metrics, and alerts."""

    def __init__(self, base_path: str = "data") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _append(self, file_name: str, record: Dict[str, Any]) -> None:
        file_path = self.base_path / file_name
        line = json.dumps(record, ensure_ascii=False)
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def record_trade(self, trade: Dict[str, Any]) -> None:
        """Persist a trade event for later auditing."""
        self._append("trades.jsonl", trade)

    def record_metric(self, metric: Dict[str, Any]) -> None:
        """Persist aggregated metrics (risk, equity, latency)."""
        self._append("metrics.jsonl", metric)

    def record_alert(self, alert: Dict[str, Any]) -> None:
        """Persist alerts so they can be reviewed even if notification fails."""
        self._append("alerts.jsonl", alert)

    def record_config(self, snapshot: ConfigSnapshot) -> None:
        """Persist a configuration snapshot."""
        self._append("config_history.jsonl", asdict(snapshot))

    def tail(self, file_name: str, limit: int = 10) -> Iterable[Dict[str, Any]]:
        """Return the most recent records from a JSON-lines file."""
        file_path = self.base_path / file_name
        if not file_path.exists():
            return []
        with file_path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]


class ConfigHistory:
    """Manage configuration snapshots for auditing and rollback."""

    def __init__(self, datastore: Optional[DataStore] = None) -> None:
        self.datastore = datastore or DataStore()

    def snapshot(self, label: str, payload: Dict[str, Any]) -> ConfigSnapshot:
        snap = ConfigSnapshot.from_dict(label, payload)
        self.datastore.record_config(snap)
        return snap

