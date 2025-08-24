# tests/test_status_snapshot.py
from __future__ import annotations

from src.ws.health import MetricsRegistry


def test_status_snapshot_has_human_fields():
    reg = MetricsRegistry.get()
    reg.reset()
    reg.inc_spot(2)
    reg.inc_linear(1)
    snap = reg.snapshot()
    assert snap["counters"]["spot"] == 2
    assert snap["counters"]["linear"] == 1
    # human-friendly utc strings exist (can be None only at start)
    assert "last_event_at_utc" in snap
    assert "last_spot_at_utc" in snap
    assert "last_linear_at_utc" in snap
