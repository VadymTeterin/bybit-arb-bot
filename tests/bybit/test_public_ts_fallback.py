# tests/bybit/test_public_ts_fallback.py
from __future__ import annotations

from exchanges.bybit.public_client import parse_ticker


def test_parse_ticker_uses_top_level_time_when_missing_update_ts():
    payload = {
        "retCode": 0,
        "time": 1739900000000,  # top-level time
        "result": {
            "category": "linear",
            "list": [
                {
                    "symbol": "BTCUSDT",
                    "bid1Price": "1",
                    "ask1Price": "2",
                    "lastPrice": "1.5",
                    # updateTime is intentionally missing
                }
            ],
        },
    }
    t = parse_ticker(payload, "BTC/USDT")
    # If it didn't fallback, timestamp would be epoch(0)
    assert t.ts.year == 2025 and t.ts.month in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
