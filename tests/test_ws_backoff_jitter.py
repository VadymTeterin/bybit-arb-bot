# tests/test_ws_backoff_jitter.py
# English-only comments per project rules.

from __future__ import annotations

from typing import List
from random import Random
from itertools import islice
import math

import pytest

from src.ws.backoff import BackoffPolicy, exp_backoff_with_jitter_compat


def _clipped_series(base: float, factor: float, cap: float, n: int) -> List[float]:
    """Helper: nominal clipped exponential series (no jitter), length n."""
    out = []
    v = base
    for _ in range(n):
        out.append(min(v, cap))
        v = min(v * factor, cap)
    return out


def test_policy_jitter_bounds_and_caps() -> None:
    # Given: 10% jitter, cap=5.0; use seeded RNG for deterministic test
    policy = BackoffPolicy(base=0.5, factor=2.0, cap=5.0, max_sleep=5.0, jitter=0.10, rng=Random(123))
    expected = _clipped_series(0.5, 2.0, 5.0, 10)

    vals = [policy.next_delay() for _ in range(10)]

    # Each value stays within [clipped*(1 - jitter), clipped] and never negative.
    for got, clipped in zip(vals, expected):
        low = clipped * (1.0 - 0.10)
        assert low - 1e-9 <= got <= clipped + 1e-9
        assert got >= 0.0


def test_policy_does_not_overshoot_nominal_step() -> None:
    policy = BackoffPolicy(base=0.25, factor=2.0, cap=4.0, max_sleep=4.0, jitter=0.25, rng=Random(7))
    # Take finite prefix from the infinite generator
    gen_vals = list(islice(policy.sequence(), 12))
    for i, got in enumerate(gen_vals):
        nominal_i = BackoffPolicy.compute_nth(0.25, 2.0, 4.0, i)
        assert got <= nominal_i + 1e-9  # never exceed unclamped nominal (clipped)


def test_policy_reset_with_zero_jitter() -> None:
    # With jitter=0 the values are deterministic and equal to clipped exponentials
    policy = BackoffPolicy(base=0.5, factor=2.0, cap=5.0, max_sleep=5.0, jitter=0.0)
    assert math.isclose(policy.next_delay(), 0.5, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(policy.next_delay(), 1.0, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(policy.next_delay(), 2.0, rel_tol=0, abs_tol=1e-12)

    policy.reset()
    assert math.isclose(policy.next_delay(), 0.5, rel_tol=0, abs_tol=1e-12)


def test_compute_nth_clipped_sequence() -> None:
    # Verify that compute_nth returns clipped (no jitter) values
    base, factor, cap = 0.5, 2.0, 5.0
    expect = [0.5, 1.0, 2.0, 4.0, 5.0, 5.0, 5.0]
    got = [BackoffPolicy.compute_nth(base, factor, cap, i) for i in range(len(expect))]
    assert got == expect


def test_sequence_independent_from_next_delay_state() -> None:
    # Exhaust some next_delay then take finite prefix from generator
    policy = BackoffPolicy(base=1.0, factor=3.0, cap=9.0, max_sleep=9.0, jitter=0.0)
    _ = [policy.next_delay() for _ in range(5)]  # advance internal state to cap

    seq_vals = list(islice(policy.sequence(), 3))  # take first 3 generator values
    assert math.isclose(seq_vals[0], 1.0, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(seq_vals[1], 3.0, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(seq_vals[2], 9.0, rel_tol=0, abs_tol=1e-12)


def test_compat_no_jitter_matches_nominal() -> None:
    # Legacy helper with jitter=0 should equal the nominal clipped value for the attempt (1-based)
    base, factor, upper = 0.5, 2.0, 5.0
    expected = [0.5, 1.0, 2.0, 4.0, 5.0, 5.0]
    got = [exp_backoff_with_jitter_compat(i + 1, base=base, factor=factor, cap=upper, jitter=0.0) for i in range(len(expected))]
    assert got == expected


def test_compat_with_rng_respects_jitter_bounds_and_upper() -> None:
    base, factor, upper, jitter = 0.5, 2.0, 5.0, 0.10
    # attempt 4 -> nominal=4.0, clipped=4.0
    val = exp_backoff_with_jitter_compat(4, base=base, factor=factor, cap=upper, jitter=jitter, rng=Random(123))
    clipped = 4.0
    low = clipped * (1.0 - jitter)
    assert low - 1e-9 <= val <= clipped + 1e-9  # within jitter bounds and not exceeding clipped


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError):
        BackoffPolicy(base=0.0)  # base must be > 0
    with pytest.raises(ValueError):
        BackoffPolicy(base=0.5, factor=0.0)  # factor must be > 0
    with pytest.raises(ValueError):
        BackoffPolicy(base=0.5, factor=2.0, cap=0.0)  # cap must be > 0
    with pytest.raises(ValueError):
        BackoffPolicy(base=0.5, factor=2.0, cap=5.0, max_sleep=4.0)  # max_sleep >= cap
    with pytest.raises(ValueError):
        BackoffPolicy(base=0.5, factor=2.0, cap=5.0, jitter=-0.1)  # jitter >= 0
