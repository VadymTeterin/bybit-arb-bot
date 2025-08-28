# src/ws/reconnect.py
"""Generic reconnection policy and heartbeat helpers for WS clients."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass
class ReconnectPolicy:
    """
    Stateful reconnection policy.
    - base_delay: initial seconds (first retry).
    - max_delay: cap for delay.
    - factor: multiplier per attempt.
    - jitter: 0.0..1.0 => +/- percentage of the computed delay.
    """

    base_delay: float = 0.5
    max_delay: float = 30.0
    factor: float = 2.0
    jitter: float = 0.1
    _attempt: int = 0

    def next_delay(self) -> float:
        # compute pure exponential (attempt 0 => base)
        delay = self.base_delay * (self.factor**self._attempt)
        if delay > self.max_delay:
            delay = self.max_delay
        # apply symmetric jitter as percentage of delay
        if self.jitter > 0.0:
            j = (random.random() * 2.0 - 1.0) * self.jitter
            delay = max(0.0, delay * (1.0 + j))
        self._attempt += 1
        return float(delay)

    def reset(self) -> None:
        self._attempt = 0


def heartbeat_late(now_ms: int, last_heartbeat_ms: int | None, timeout_ms: int) -> bool:
    """Return True if heartbeat is late (or missing) beyond timeout_ms."""
    if last_heartbeat_ms is None:
        return True
    return (now_ms - last_heartbeat_ms) > timeout_ms


def now_ms() -> int:
    return int(time.time() * 1000)
