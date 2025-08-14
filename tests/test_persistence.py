from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from importlib import reload

from src.storage import persistence


def test_init_db_tmp(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setenv("DB_PATH", str(db))  # підмінимо шлях через env
    reload(persistence)  # щоб settings перечитався
    persistence.init_db()
    assert db.exists()
    with sqlite3.connect(db) as con:
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='signals'"
        ).fetchone()
        assert row is not None


def test_save_and_get(tmp_path, monkeypatch):
    db = tmp_path / "t2.db"
    monkeypatch.setenv("DB_PATH", str(db))
    reload(persistence)
    persistence.init_db()

    # збережемо 2 записи: один «давній», один «свіжий»
    old_ts = datetime.now(timezone.utc) - timedelta(hours=30)
    new_ts = datetime.now(timezone.utc) - timedelta(hours=1)

    persistence.save_signal("BTCUSDT", 68000, 68200, 0.294, 250_000_000, old_ts)
    persistence.save_signal("ETHUSDT", 3000, 3020, 0.667, 150_000_000, new_ts)

    # беремо тільки за останні 24 години
    rows = persistence.get_signals(last_hours=24)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "ETHUSDT"
    assert "basis_pct" in rows[0]
