# src/ws/reconnect.py
"""Generic reconnection policy and heartbeat helpers for WS clients.

This module is exchange-agnostic and can be used by any WS connector.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReconnectPolicy:
    base_delay: float = 0.5  # seconds
    max_delay: float = 30.0
    factor: float = 2.0
    jitter: float = 0.1  # fraction of delay to randomize

    _attempt: int = 0

    def next_delay(self) -> float:
        """Return the next backoff delay and increment the attempt counter."""
        delay = min(self.max_delay, self.base_delay * (self.factor**self._attempt))
        # Apply jitter
        jitter_span = delay * self.jitter
        delay = delay + random.uniform(-jitter_span, jitter_span)
        self._attempt += 1
        return max(0.0, delay)

    def reset(self) -> None:
        """Reset the backoff attempts (call on successful connect or stable heartbeat)."""
        self._attempt = 0


def heartbeat_late(
    now_ms: int, last_heartbeat_ms: Optional[int], timeout_ms: int
) -> bool:
    """Return True if heartbeat is late (or missing) beyond timeout_ms."""
    if last_heartbeat_ms is None:
        return True
    return (now_ms - last_heartbeat_ms) > timeout_ms


def now_ms() -> int:
    return int(time.time() * 1000)
