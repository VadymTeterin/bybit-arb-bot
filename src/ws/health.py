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


def _utc_iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    # Render as "YYYY-MM-DD HH:MM:SS UTC"
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))


@dataclass
class WSHealth:
    started_ts: float
    spot_events: int = 0
    linear_events: int = 0
    last_event_ts: Optional[float] = None
    last_spot_ts: Optional[float] = None
    last_linear_ts: Optional[float] = None

    @property
    def uptime_ms(self) -> int:
        return int((time.time() - self.started_ts) * 1000)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "started_ts": self.started_ts,
            "started_at_utc": _utc_iso(self.started_ts),
            "uptime_ms": self.uptime_ms,
            "counters": {"spot": self.spot_events, "linear": self.linear_events},
            "last_event_ts": self.last_event_ts,
            "last_event_at_utc": _utc_iso(self.last_event_ts),
            "last_spot_ts": self.last_spot_ts,
            "last_spot_at_utc": _utc_iso(self.last_spot_ts),
            "last_linear_ts": self.last_linear_ts,
            "last_linear_at_utc": _utc_iso(self.last_linear_ts),
        }
        return d


class MetricsRegistry:
    """
    Thread-safe singleton holding WebSocket health metrics.
    Use `MetricsRegistry.get()` to access the single instance.
    """

    _instance: Optional["MetricsRegistry"] = None
    _guard = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = WSHealth(started_ts=time.time())

    # --- Singleton access ---
    @classmethod
    def get(cls) -> "MetricsRegistry":
        if cls._instance is None:
            with cls._guard:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # --- Mutations ---
    def reset(self) -> None:
        with self._lock:
            self._state = WSHealth(started_ts=time.time())

    def inc_spot(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("n must be >= 0")
        now = time.time()
        with self._lock:
            self._state.spot_events += n
            self._state.last_spot_ts = now
            self._state.last_event_ts = now

    def inc_linear(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("n must be >= 0")
        now = time.time()
        with self._lock:
            self._state.linear_events += n
            self._state.last_linear_ts = now
            self._state.last_event_ts = now

    # --- Read-only view ---
    def snapshot(self) -> Dict[str, Any]:
        """
        Return a copy of the current metrics as a serializable dict.
        """
        with self._lock:
            s = WSHealth(
                started_ts=self._state.started_ts,
                spot_events=self._state.spot_events,
                linear_events=self._state.linear_events,
                last_event_ts=self._state.last_event_ts,
                last_spot_ts=self._state.last_spot_ts,
                last_linear_ts=self._state.last_linear_ts,
            )
        return s.to_dict()
