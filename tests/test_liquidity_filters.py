from __future__ import annotations
from src.core.filters.liquidity import enough_liquidity


def test_enough_liquidity_true_basic():
    row = {"price": 2.5, "turnover_usd": 12_000_000}
    assert enough_liquidity(row, min_vol_usd=10_000_000, min_price=0.5) is True


def test_enough_liquidity_false_by_price():
    row = {"lastPrice": 0.0005, "turnoverUsd": 50_000_000}
    assert enough_liquidity(row, min_vol_usd=10_000_000, min_price=0.001) is False


def test_enough_liquidity_false_by_volume():
    row = {"lastPriceLatest": 1.2, "turnover24h": 1_000_000}
    assert enough_liquidity(row, min_vol_usd=10_000_000, min_price=0.5) is False


def test_enough_liquidity_handles_missing_and_strings():
    row = {"lastPrice": "3.1", "turnoverUsd": "15000000"}
    assert enough_liquidity(row, min_vol_usd=10_000_000, min_price=0.1) is True
