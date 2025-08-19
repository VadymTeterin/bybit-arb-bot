# tests/test_ws_normalizer_bybit_v5.py
from __future__ import annotations

from src.ws.normalizers.bybit_v5 import normalize


def test_normalize_ticker_minimal():
    raw = {
        "topic": "tickers.BTCUSDT",
        "ts": 1700000000000,
        "data": [
            {
                "symbol": "BTCUSDT",
                "lastPrice": "60000",
                "indexPrice": "60010",
                "markPrice": "60005",
                "openInterest": "1234",
                "turnover24h": "99999",
                "volume24h": "88888",
            }
        ],
    }
    out = normalize(raw)
    assert out["exchange"] == "BYBIT"
    assert out["channel"] == "ticker"
    assert out["symbol"] == "BTCUSDT"
    assert out["event"] in {"snapshot", "unknown"}  # depends on provider
    assert out["data"]["last_price"] == 60000.0
    assert out["data"]["mark_price"] == 60005.0


def test_normalize_trades_list():
    raw = {
        "topic": "publicTrade.ETHUSDT",
        "type": "delta",
        "ts": 1700000001234,
        "data": [
            {
                "T": 1700000001200,
                "s": "ETHUSDT",
                "p": "3500.5",
                "v": "0.25",
                "m": True,
                "i": "t1",
            },
            {
                "T": 1700000001210,
                "s": "ETHUSDT",
                "p": "3500.0",
                "v": "0.10",
                "m": False,
                "i": "t2",
            },
        ],
    }
    out = normalize(raw)
    assert out["channel"] == "trade"
    assert out["symbol"] == "ETHUSDT"
    trades = out["data"]["trades"]
    assert len(trades) == 2
    assert trades[0]["price"] == 3500.5
    assert trades[0]["side"] == "sell"  # Bybit maker flag m=True => taker side is sell


def test_normalize_orderbook_levels():
    raw = {
        "topic": "orderbook.1.BTCUSDT",
        "type": "snapshot",
        "ts": 1700000002000,
        "data": {
            "b": [["60000", "1.2"], ["59990", "0.8"]],
            "a": [["60010", "1.0"], ["60020", "2.5"]],
        },
    }
    out = normalize(raw)
    assert out["channel"] == "orderbook"
    assert out["symbol"] == "BTCUSDT"
    assert out["event"] == "snapshot"
    assert out["data"]["bids"][0]["price"] == 60000.0
    assert out["data"]["asks"][1]["qty"] == 2.5


def test_handles_unknown_topic_gracefully():
    raw = {"topic": "unknown.stuff", "ts": 1, "data": {"foo": 1}}
    out = normalize(raw)
    assert out["channel"] == "other"
    assert out["symbol"] == ""
    assert out["data"]["foo"] == 1


def test_ts_fallback_to_now_ms():
    raw = {"topic": "tickers.BTCUSDT", "data": [{"lastPrice": "1"}]}
    out = normalize(raw)
    assert isinstance(out["ts_ms"], int)
    assert out["ts_ms"] > 0
