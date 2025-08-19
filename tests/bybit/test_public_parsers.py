# tests/bybit/test_public_parsers.py
from __future__ import annotations

from datetime import datetime, timezone

from exchanges.bybit.public_client import parse_candles, parse_order_book, parse_ticker


def _ts(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def test_parse_ticker_ok():
    payload = {
        "retCode": 0,
        "result": {
            "category": "spot",
            "list": [
                {
                    "symbol": "BTCUSDT",
                    "bid1Price": "65000",
                    "ask1Price": "65010",
                    "lastPrice": "65005",
                    "updateTime": 1739900000000,
                }
            ],
        },
    }
    t = parse_ticker(payload, "BTC/USDT")
    assert t.symbol == "BTC/USDT"
    assert t.bid == 65000.0 and t.ask == 65010.0 and t.last == 65005.0
    assert t.ts == _ts(1739900000000)


def test_parse_order_book_ok():
    payload = {
        "retCode": 0,
        "result": {
            "ts": 1739900000000,
            "b": [["65000", "0.5"], ["64990", "1.0"]],
            "a": [["65010", "0.4"], ["65020", "2.0"]],
        },
    }
    ob = parse_order_book(payload, "BTC/USDT")
    assert ob.symbol == "BTC/USDT"
    assert ob.bids[0].price == 65000.0 and ob.bids[0].qty == 0.5
    assert ob.asks[1].price == 65020.0 and ob.asks[1].qty == 2.0
    assert ob.ts == _ts(1739900000000)


def test_parse_candles_ok():
    payload = {
        "retCode": 0,
        "result": {
            "list": [
                [
                    1739900000000,
                    "64000",
                    "65100",
                    "63900",
                    "65000",
                    "123.45",
                    "8000000",
                ],
                [
                    1739900900000,
                    "65000",
                    "65200",
                    "64800",
                    "65100",
                    "234.56",
                    "9000000",
                ],
            ]
        },
    }
    candles = parse_candles(payload, "BTC/USDT", "15m")
    assert len(candles) == 2
    c0 = candles[0]
    assert c0.symbol == "BTC/USDT" and c0.interval == "15m"
    assert (
        c0.open == 64000.0
        and c0.high == 65100.0
        and c0.low == 63900.0
        and c0.close == 65000.0
    )
    assert c0.volume == 123.45 and c0.open_time == _ts(1739900000000)
