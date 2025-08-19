import time

from src.ws.health import MetricsRegistry


def test_singleton():
    r1 = MetricsRegistry.get()
    r2 = MetricsRegistry.get()
    assert r1 is r2


def test_inc_and_last_ts():
    reg = MetricsRegistry.get()
    reg.reset()
    reg.inc_spot()
    reg.inc_linear(2)
    snap = reg.snapshot()
    assert snap["counters"]["spot"] == 1
    assert snap["counters"]["linear"] == 2
    assert snap["last_event_ts"] is not None
    assert snap["last_spot_ts"] is not None
    assert snap["last_linear_ts"] is not None


def test_uptime_non_decreasing():
    reg = MetricsRegistry.get()
    reg.reset()
    snap1 = reg.snapshot()
    time.sleep(0.01)
    snap2 = reg.snapshot()
    assert snap2["uptime_ms"] >= snap1["uptime_ms"]


def test_reset_clears_counters_and_timestamps():
    reg = MetricsRegistry.get()
    reg.inc_spot()
    reg.reset()
    snap = reg.snapshot()
    assert snap["counters"]["spot"] == 0
    assert snap["counters"]["linear"] == 0
    assert snap["last_event_ts"] is None
    assert snap["last_spot_ts"] is None
    assert snap["last_linear_ts"] is None
