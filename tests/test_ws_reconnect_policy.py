# tests/test_ws_reconnect_policy.py
from __future__ import annotations

from src.ws.reconnect import ReconnectPolicy, heartbeat_late


def test_backoff_progression_and_reset():
    p = ReconnectPolicy(base_delay=0.5, max_delay=8.0, factor=2.0, jitter=0.0)
    d1 = p.next_delay()
    d2 = p.next_delay()
    d3 = p.next_delay()
    assert d1 == 0.5 and d2 == 1.0 and d3 == 2.0
    p.reset()
    d4 = p.next_delay()
    assert d4 == 0.5


def test_heartbeat_late_logic():
    now = 1_000_000
    assert heartbeat_late(now, None, 1000) is True
    assert heartbeat_late(now, now - 500, 1000) is False
    assert heartbeat_late(now, now - 1500, 1000) is True
