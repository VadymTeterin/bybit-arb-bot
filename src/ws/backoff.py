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
    - `reset()` sets the internal state back to `base`.
    - Iterable: iter(backoff) yields successive delays.
    """

    base: float = 0.5
    factor: float = 2.0
    cap: float = 30.0

    def __post_init__(self) -> None:
        if self.base <= 0:
            raise ValueError("base must be > 0")
        if self.factor <= 1.0:
            raise ValueError("factor must be > 1.0")
        if self.cap < self.base:
            raise ValueError("cap must be >= base")
        self._current = self.base

    def reset(self) -> None:
        """Reset sequence to `base`."""
        self._current = self.base

    def next_delay(self) -> float:
        """
        Return the current delay, then advance the internal state
        using min(cap, current*factor). This guarantees no overshoot above `cap`.
        """
        value = float(self._current)
        next_value = self._current * self.factor
        self._current = next_value if next_value < self.cap else self.cap
        return value

    def __iter__(self):
        return self

    def __next__(self) -> float:
        return self.next_delay()

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
