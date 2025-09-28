"""Monitoring and alerting helpers for trading workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional

from persistence import DataStore


class EventLogger:
    """Central logger that fans out to console and optional sinks."""

    def __init__(self, datastore: Optional[DataStore] = None) -> None:
        self.datastore = datastore
        self.history: List[Dict[str, Any]] = []

    def log(self, event_type: str, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "event": event_type,
            "message": message,
            "payload": payload or {},
        }
        self.history.append(entry)
        print(f"[{entry['timestamp']}] {event_type}: {message}")
        if self.datastore:
            self.datastore.record_metric(entry)

    def recent(self, limit: int = 10) -> Iterable[Dict[str, Any]]:
        return self.history[-limit:]


class AlertManager:
    """Dispatch alerts to registered handlers and persist them."""

    def __init__(self, datastore: Optional[DataStore] = None) -> None:
        self.handlers: List[Callable[[Dict[str, Any]], None]] = []
        self.datastore = datastore

    def register(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self.handlers.append(handler)

    def notify(self, severity: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "severity": severity,
            "message": message,
            "context": context or {},
        }
        for handler in self.handlers:
            try:
                handler(payload)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Alert handler failed: {exc}")
        if self.datastore:
            self.datastore.record_alert(payload)

