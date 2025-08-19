# tests/bybit/test_ws_public_parsers.py
from __future__ import annotations

from datetime import datetime, timezone

from exchanges.bybit.ws_public import parse_ws_ticker


def _dt(ms: int) -> datetime:
    # Конвертація мс -> UTC datetime (джерело істини — самі мілісекунди)
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def test_parse_ws_ticker_list_data_ok():
    payload = {
        "topic": "tickers",
        "type": "snapshot",
        "ts": 1739900000000,
        "data": [
            {
                "symbol": "BTCUSDT",
                "bid1Price": "65000",
                "ask1Price": "65010",
                "lastPrice": "65005",
                "updateTime": 1739900000000,
            }
        ],
    }
    t = parse_ws_ticker(payload)
    assert t is not None
    assert t.symbol == "BTC/USDT"
    assert t.bid == 65000.0 and t.ask == 65010.0 and t.last == 65005.0
    assert t.ts == _dt(1739900000000)


def test_parse_ws_ticker_dict_data_ok():
    payload = {
        "topic": "tickers",
        "type": "delta",
        "ts": 1739900900000,
        "data": {
            "symbol": "BTCUSDT",
            "bidPrice": "65100",
            "askPrice": "65110",
            "price": "65105",
            "updateTime": 1739900900000,
        },
    }
    t = parse_ws_ticker(payload)
    assert t is not None
    assert t.symbol == "BTC/USDT"
    assert t.bid == 65100.0 and t.ask == 65110.0 and t.last == 65105.0
    assert t.ts == _dt(1739900900000)


def test_parse_ws_ticker_missing_data():
    assert parse_ws_ticker({"topic": "tickers"}) is None
