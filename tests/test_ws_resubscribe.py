# tests/test_ws_resubscribe.py
from __future__ import annotations

from src.ws.manager import WSManager


def test_resubscribe_replays_topics():
    m = WSManager()
    m.set_topics(["tickers.BTCUSDT"])
    m.add_topics(["tickers.ETHUSDT", "tickers.BTCUSDT"])  # duplicate ignored
    to_sub = m.on_connect()
    assert set(to_sub) == {"tickers.BTCUSDT", "tickers.ETHUSDT"}

    # remove one and ensure replay returns only remaining
    m.remove_topics(["tickers.BTCUSDT"])
    again = m.on_connect()
    assert set(again) == {"tickers.ETHUSDT"}

    # disconnect increments reconnects_total
    m.on_disconnect("test")
    snap = m.snapshot().to_dict()
    assert snap["reconnects_total"] >= 1
    assert "last_connect_ts" in snap
