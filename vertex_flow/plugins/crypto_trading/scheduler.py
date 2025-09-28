"""Basic scheduler for orchestrating strategy callbacks."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from monitoring import EventLogger


@dataclass
class ScheduledTask:
    name: str
    interval: float
    func: Callable[[], Any]
    last_run: float = field(default=0.0)
    enabled: bool = field(default=True)

    def ready(self, now: float) -> bool:
        if not self.enabled:
            return False
        return now - self.last_run >= self.interval


class StrategyScheduler:
    """Tiny cooperative scheduler that runs registered callables."""

    def __init__(self, logger: Optional[EventLogger] = None) -> None:
        self.logger = logger
        self.tasks: Dict[str, ScheduledTask] = {}

    def add_task(self, name: str, interval: float, func: Callable[[], Any]) -> None:
        self.tasks[name] = ScheduledTask(name=name, interval=interval, func=func)
        if self.logger:
            self.logger.log("scheduler", f"Registered task '{name}'", {"interval": interval})

    def remove_task(self, name: str) -> None:
        if name in self.tasks:
            self.tasks.pop(name)
            if self.logger:
                self.logger.log("scheduler", f"Removed task '{name}'", {})

    def enable(self, name: str) -> None:
        if name in self.tasks:
            self.tasks[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self.tasks:
            self.tasks[name].enabled = False

    def run_pending(self) -> None:
        now = time.time()
        for task in self.tasks.values():
            if task.ready(now):
                if self.logger:
                    self.logger.log("scheduler", f"Running task '{task.name}'", {})
                task.func()
                task.last_run = now

    def run_for(self, duration: float, poll_interval: float = 1.0) -> None:
        """Run the scheduler loop for a bounded amount of time."""
        end = time.time() + duration
        while time.time() < end:
            self.run_pending()
            time.sleep(poll_interval)

