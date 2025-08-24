"""
Runtime metrics for WebSocket pipelines.
Tracks counters for SPOT and LINEAR streams, uptime, and last event timestamps.
(English-only comments per project rules)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WSHealth:
    started_ts: float
    spot_events: int = 0
    linear_events: int = 0
    last_event_ts: Optional[float] = None
    last_spot_ts: Optional[float] = None
    last_linear_ts: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_ts": self.started_ts,
            "uptime_ms": int((time.time() - self.started_ts) * 1000),
            "counters": {"spot": self.spot_events, "linear": self.linear_events},
            "last_event_ts": self.last_event_ts,
            "last_spot_ts": self.last_spot_ts,
            "last_linear_ts": self.last_linear_ts,
        }


class MetricsRegistry:
    """Thread-safe singleton registry of WS health metrics."""

    _instance: "MetricsRegistry|None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._lock_local = threading.Lock()
        self._state = WSHealth(started_ts=time.time())

    @classmethod
    def get(cls) -> "MetricsRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = MetricsRegistry()
            return cls._instance

    # --- mutations
    def inc_spot(self, n: int = 1) -> None:
        with self._lock_local:
            self._state.spot_events += int(n)
            now = time.time()
            self._state.last_spot_ts = now
            self._state.last_event_ts = now

    def inc_linear(self, n: int = 1) -> None:
        with self._lock_local:
            self._state.linear_events += int(n)
            now = time.time()
            self._state.last_linear_ts = now
            self._state.last_event_ts = now

    def reset(self) -> None:
        with self._lock_local:
            self._state = WSHealth(started_ts=time.time())

    # --- views
    def snapshot(self) -> Dict[str, Any]:
        with self._lock_local:
            s = WSHealth(
                started_ts=self._state.started_ts,
                spot_events=self._state.spot_events,
                linear_events=self._state.linear_events,
                last_event_ts=self._state.last_event_ts,
                last_spot_ts=self._state.last_spot_ts,
                last_linear_ts=self._state.last_linear_ts,
            )
        return s.to_dict()
