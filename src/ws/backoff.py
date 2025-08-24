"""
Exponential backoff utilities.
(English-only comments per project rules)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExponentialBackoff:
    """
    Deterministic exponential backoff.
    - Starts from `base` seconds.
    - Each `next_delay()` multiplies the current value by `factor` up to `cap` (no overshoot).
    - `reset()` returns sequence to initial.
    - `compute_nth()` allows to get n-th value without mutating the instance.
    """

    base: float = 0.5
    factor: float = 2.0
    cap: float = 30.0
    _current: float = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.base <= 0 or self.factor <= 0 or self.cap <= 0:
            raise ValueError("base, factor, cap must be positive")
        self._current = self.base

    def next_delay(self) -> float:
        d = float(self._current)
        # prepare next value for the future call
        nxt = self._current * self.factor
        self._current = nxt if nxt < self.cap else self.cap
        return d

    def reset(self) -> None:
        self._current = self.base

    @staticmethod
    def compute_nth(base: float, factor: float, cap: float, n: int) -> float:
        """
        Compute the n-th backoff delay (0-based) without mutating any state.
        Example: n=0 -> base, n=1 -> min(cap, base*factor), etc.
        """
        if n < 0:
            raise ValueError("n must be >= 0")
        value = base
        for _ in range(n):
            value = value * factor
            if value >= cap:
                value = cap
                break
        return float(value if value <= cap else cap)
