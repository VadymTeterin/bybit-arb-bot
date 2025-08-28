from datetime import datetime, timedelta, timezone

from src.core.alerts_gate import AlertGate


def _t(h=12, m=0, s=0):
    return datetime(2025, 8, 27, h, m, s, tzinfo=timezone.utc)


def test_first_alert_is_allowed():
    g = AlertGate(cooldown_sec=300, suppress_eps_pct=0.2, suppress_window_min=15)
    t0 = _t()
    ok, reason = g.should_send("BTCUSDT", basis_pct=1.50, ts=t0)
    assert ok, reason
    g.commit("BTCUSDT", 1.50, t0)


def test_cooldown_blocks_repeat_inside_window():
    g = AlertGate(cooldown_sec=300, suppress_eps_pct=0.2, suppress_window_min=15)
    t0 = _t()
    g.commit("BTCUSDT", 1.50, t0)

    t1 = t0 + timedelta(seconds=299)
    ok, reason = g.should_send("BTCUSDT", basis_pct=1.60, ts=t1)
    assert not ok and "cooldown" in reason


def test_after_cooldown_allowed():
    g = AlertGate(cooldown_sec=300, suppress_eps_pct=0.2, suppress_window_min=15)
    t0 = _t()
    g.commit("BTCUSDT", 1.50, t0)

    t1 = t0 + timedelta(seconds=301)
    ok, reason = g.should_send("BTCUSDT", basis_pct=1.60, ts=t1)
    assert ok, reason


def test_suppression_within_window_by_eps_during_cooldown():
    # suppression works only while cooldown is active
    g = AlertGate(cooldown_sec=600, suppress_eps_pct=0.2, suppress_window_min=15)
    t0 = _t()
    g.commit("BTCUSDT", 1.50, t0)

    # within window (5 min) and within cooldown (10 min), Δ = 0.08pp < 0.2pp => suppressed
    t1 = t0 + timedelta(minutes=5)
    ok, reason = g.should_send("BTCUSDT", basis_pct=1.58, ts=t1)
    assert not ok and "Δbasis" in reason

    # within window & cooldown, Δ = 0.35pp >= 0.2pp => still blocked by cooldown (different reason)
    ok2, reason2 = g.should_send("BTCUSDT", basis_pct=1.85, ts=t1)
    assert not ok2 and "cooldown" in reason2


def test_window_expired_allows_even_small_delta_when_no_cooldown():
    # when cooldown is 0, suppression is not applied; small delta allowed after long pause
    g = AlertGate(cooldown_sec=0, suppress_eps_pct=0.2, suppress_window_min=15)
    t0 = _t()
    g.commit("BTCUSDT", 1.50, t0)

    # after 16 minutes (window expired), small delta should be allowed
    t1 = t0 + timedelta(minutes=16)
    ok, reason = g.should_send("BTCUSDT", basis_pct=1.55, ts=t1)
    assert ok, reason
