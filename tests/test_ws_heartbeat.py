# tests/test_ws_heartbeat.py
from __future__ import annotations

import time

from src.ws.manager import WSManager


def test_heartbeat_updates_and_msg_age():
    m = WSManager()
    m.set_topics(["tickers"])
    m.on_connect()

    # simulate pong
    m.on_message({"op": "pong"})
    snap1 = m.snapshot().to_dict()
    assert snap1["last_heartbeat_ts"] is not None
    assert snap1["last_msg_ts"] is not None

    # msg age grows with time
    time.sleep(0.01)
    snap2 = m.snapshot().to_dict()
    assert snap2["last_msg_age_ms"] >= snap1["last_msg_age_ms"]
