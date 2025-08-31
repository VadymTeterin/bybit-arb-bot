# src/ws/backoff.py
# English-only comments per project rules.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional
import random


__all__ = [
    "BackoffPolicy",
    "exp_backoff_with_jitter_compat",
]


@dataclass
class BackoffPolicy:
    """
    Exponential backoff with bounded jitter.

    Parameters:
        base:        Initial delay (seconds), must be > 0.
        factor:      Multiplier for each step, must be > 0.
        cap:         Soft upper bound for the *calculated* delay before jitter (seconds), must be > 0.
        max_sleep:   Hard upper bound for the final returned delay after jitter (seconds), must be >= cap.
        jitter:      Portion (0..1) of 'clipped' used to compute +/- random noise.
        rng:         Optional random.Random for deterministic tests (seedable).

    Behavior:
        - 'next_delay()' returns the current delay and advances the internal state.
        - 'reset()' returns the sequence to the initial state.
        - 'sequence()' yields an infinite sequence of delays.
        - Jitter is symmetric in [-j, +j], j = jitter * clipped.
        - Returned value is never negative and never exceeds 'max_sleep'.
        - Returned value never exceeds the unclamped target after jitter
          (i.e., we do not overshoot the nominal exponential step).
    """

    base: float = 0.5
    factor: float = 2.0
    cap: float = 30.0
    max_sleep: float = 30.0
    jitter: float = 0.10
    rng: Optional[random.Random] = field(default=None, repr=False)

    _current: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Validation
        if self.base <= 0 or self.factor <= 0 or self.cap <= 0:
            raise ValueError("base, factor, cap must be positive")
        if self.max_sleep <= 0:
            raise ValueError("max_sleep must be positive")
        if self.max_sleep < self.cap:
            # Keep invariant: hard bound should be >= soft bound.
            raise ValueError("max_sleep must be >= cap")
        if self.jitter < 0:
            raise ValueError("jitter must be >= 0")
        self._current = float(self.base)

    def reset(self) -> None:
        self._current = float(self.base)

    def _random_uniform(self, a: float, b: float) -> float:
        r = self.rng.uniform(a, b) if self.rng is not None else random.uniform(a, b)
        return float(r)

    def _jittered(self, clipped: float, nominal: float) -> float:
        # jitter span based on 'clipped'
        span = self.jitter * clipped
        if span <= 0:
            return clipped
        jittered = clipped + self._random_uniform(-span, span)
        # Do not exceed the nominal target after jitter, clamp to hard max
        value = min(clipped, jittered)
        return max(0.0, min(value, self.max_sleep))

    def next_delay(self) -> float:
        """
        Return current delay (with jitter), then advance the internal state.
        """
        nominal = self._current
        clipped = min(nominal, self.cap)
        out = self._jittered(clipped, nominal)

        # Advance for the next call
        next_nominal = self._current * self.factor
        self._current = next_nominal if next_nominal < self.cap else self.cap
        return out

    def sequence(self) -> Iterator[float]:
        """
        Infinite generator of delays (with jitter). Independent of 'next_delay()' state.
        """
        nominal = float(self.base)
        while True:
            clipped = min(nominal, self.cap)
            # same jitter rule as in 'next_delay()'
            span = self.jitter * clipped
            if span > 0:
                jittered = clipped + self._random_uniform(-span, span)
                value = min(clipped, jittered)
            else:
                value = clipped
            yield max(0.0, min(value, self.max_sleep))
            # advance nominal
            nominal = nominal * self.factor
            if nominal >= self.cap:
                nominal = self.cap

    @staticmethod
    def compute_nth(base: float, factor: float, cap: float, n: int) -> float:
        """
        Compute the n-th *clipped* value (0-based) without jitter/state mutation.
        Example: n=0 -> base, n=1 -> min(cap, base*factor), ...
        """
        if n < 0:
            raise ValueError("n must be >= 0")
        value = float(base)
        for _ in range(n):
            value = value * factor
            if value >= cap:
                value = cap
                break
        return float(value if value <= cap else cap)


def exp_backoff_with_jitter_compat(
    attempt: int,
    *,
    base: float = 0.5,
    factor: float = 2.0,
    cap: float | None = None,
    max_delay: float | None = None,
    jitter: float = 0.10,
    rng: Optional[random.Random] = None,
) -> float:
    """
    Backward-compatible helper mirroring legacy behavior:

    - 'attempt' is 1-based: attempt=1 -> base, attempt=2 -> base*factor, ...
    - 'cap' is accepted as an alias for 'max_delay'; if both set -> use min(cap, max_delay).
    - Jitter is symmetric in [-span, +span], span = jitter * clipped.
    - The returned value is min(jittered, clipped) — never exceeding the unclamped nominal step.
    - Hard clamp at 'max_sleep' (== chosen upper bound).
    """
    # Resolve a single upper bound
    if cap is not None and max_delay is not None:
        upper = min(cap, max_delay)
    elif cap is not None:
        upper = cap
    elif max_delay is not None:
        upper = max_delay
    else:
        upper = float("inf")

    # 1-based attempt -> 0-based exponent
    k = max(0, int(attempt) - 1)
    nominal = float(base) * (float(factor) ** k)
    clipped = min(upper, nominal)

    # Jitter
    span = max(0.0, float(jitter)) * clipped
    u = rng.uniform(-span, span) if rng is not None else random.uniform(-span, span)
    jittered = clipped + u

    # Do not exceed unclamped nominal after jitter
    value = min(clipped, jittered)
    # Never negative; hard clamp by the same upper bound
    value = max(0.0, min(value, upper))
    return float(value)
