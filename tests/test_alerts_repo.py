from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.core.alerts_gate import AlertGate
from src.infra.alerts_repo import SqliteAlertGateRepo


def test_sqlite_repo_set_get(tmp_path: Path):
    db = tmp_path / "alerts.db"
    repo = SqliteAlertGateRepo(str(db))
    assert repo.get_last("BTCUSDT") is None

    repo.set_last("BTCUSDT", ts_epoch=1000.0, basis_pct=1.5)
    ts, basis = repo.get_last("BTCUSDT")
    assert ts == 1000.0
    assert basis == 1.5

    repo.set_last("BTCUSDT", ts_epoch=2000.0, basis_pct=1.6)
    ts2, basis2 = repo.get_last("BTCUSDT")
    assert ts2 == 2000.0
    assert basis2 == 1.6


def test_alertgate_with_sqlite_repo_persists(tmp_path: Path):
    db = tmp_path / "alerts.db"
    repo = SqliteAlertGateRepo(str(db))

    gate = AlertGate(cooldown_sec=300, suppress_eps_pct=0.2, suppress_window_min=15, repo=repo)
    t0 = datetime(2025, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
    gate.commit("ETHUSDT", basis_pct=1.7, ts=t0)

    # New instance reads from DB
    gate2 = AlertGate(cooldown_sec=300, suppress_eps_pct=0.2, suppress_window_min=15, repo=repo)
    ok, reason = gate2.should_send("ETHUSDT", basis_pct=1.8, ts=t0 + timedelta(seconds=10))
    assert not ok and "cooldown" in reason
