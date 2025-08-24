# tests/test_persistence.py
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from importlib import reload

from src.storage import persistence


def _reset_db(tmp_path):
    db = tmp_path / "t.db"
    return db


def test_init_db_tmp(tmp_path, monkeypatch):
    db = _reset_db(tmp_path)
    monkeypatch.setenv("DB_PATH", str(db))
    reload(persistence)
    persistence.init_db()
    assert db.exists()
    with sqlite3.connect(db) as con:
        # Signals
        con.execute("SELECT 1 FROM signals LIMIT 1")
        # Quotes
        con.execute("SELECT 1 FROM quotes LIMIT 1")
        # Meta
        con.execute("SELECT 1 FROM meta LIMIT 1")


def test_save_and_get_signals(tmp_path, monkeypatch):
    db = _reset_db(tmp_path)
    monkeypatch.setenv("DB_PATH", str(db))
    reload(persistence)
    persistence.init_db()

    old_ts = datetime.now(timezone.utc) - timedelta(hours=30)
    new_ts = datetime.now(timezone.utc) - timedelta(hours=1)

    persistence.save_signal("BTCUSDT", 68000, 68200, 0.294, 250_000_000, old_ts)
    persistence.save_signal("ETHUSDT", 3000, 3020, 0.667, 150_000_000, new_ts)

    rows = persistence.get_signals(last_hours=24)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "ETHUSDT"
    assert "basis_pct" in rows[0]


def test_recent_signal_exists(tmp_path, monkeypatch):
    db = _reset_db(tmp_path)
    monkeypatch.setenv("DB_PATH", str(db))
    reload(persistence)
    persistence.init_db()

    now = datetime.now(timezone.utc)
    persistence.save_signal(
        "AAAUSDT", 2.0, 2.04, 2.0, 12_000_000, now - timedelta(seconds=10)
    )
    # cooldown 30s -> should be True (recent)
    assert persistence.recent_signal_exists("AAAUSDT", cooldown_sec=30) is True
    # cooldown 5s  -> should be False (too old for the short window)
    assert persistence.recent_signal_exists("AAAUSDT", cooldown_sec=5) is False


def test_save_quote_and_retention(tmp_path, monkeypatch):
    db = _reset_db(tmp_path)
    monkeypatch.setenv("DB_PATH", str(db))
    reload(persistence)
    persistence.init_db()

    # Insert two quotes with different ages
    old_ts = datetime.now(timezone.utc) - timedelta(days=40)
    new_ts = datetime.now(timezone.utc) - timedelta(days=5)

    persistence.save_quote("BTCUSDT", 68000, 68200, 0.294, 250_000_000, old_ts)
    persistence.save_quote("BTCUSDT", 69000, 69200, 0.290, 260_000_000, new_ts)

    with sqlite3.connect(db) as con:
        c1 = con.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        assert c1 == 2

    # Sweep with 30 days retention -> old is deleted
    deleted_signals, deleted_quotes = persistence.retention_sweep(days=30)
    assert deleted_quotes >= 1  # at least 1 old row removed
    assert deleted_signals >= 0  # may be zero here

    with sqlite3.connect(db) as con:
        c2 = con.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        assert c2 == 1
