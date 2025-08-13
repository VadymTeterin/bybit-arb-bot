from __future__ import annotations

import os
from datetime import datetime, timedelta
from importlib import reload

from src.core import report
from src.storage import persistence


def _seed(db_path):
    os.environ["DB_PATH"] = db_path
    reload(persistence)
    # Ініціалізуємо схему
    persistence.init_db()
    # Додаємо 3 записи: один за межами вікна, 2 — свіжі
    old_ts = datetime.utcnow() - timedelta(hours=30)
    t1 = datetime.utcnow() - timedelta(hours=2)
    t2 = datetime.utcnow() - timedelta(hours=1, minutes=30)

    persistence.save_signal("AAAUSDT", 1.0, 1.02, 2.0, 15_000_000, t1)
    persistence.save_signal("BBBUSDT", 2.0, 2.05, 2.5, 25_000_000, t2)
    persistence.save_signal("OLDUSDT", 3.0, 3.03, 1.0, 50_000_000, old_ts)


def test_get_top_signals_returns_sorted_and_limited(tmp_path, monkeypatch):
    db = tmp_path / "rep.db"
    _seed(str(db))

    # перезавантажимо report, щоб він працював із новим persistence
    reload(report)

    top = report.get_top_signals(last_hours=24, limit=1)
    assert len(top) == 1
    # найбільший basis серед свіжих — BBBUSDT (2.5%)
    assert top[0]["symbol"] == "BBBUSDT"


def test_format_report_contains_symbols_and_values(tmp_path, monkeypatch):
    db = tmp_path / "rep2.db"
    _seed(str(db))
    reload(report)

    items = report.get_top_signals(last_hours=24, limit=2)
    text = report.format_report(items, now=datetime(2025, 1, 1, 0, 0, 0))
    assert "Arbitrage Report" in text
    assert "AAAUSDT" in text and "BBBUSDT" in text
    assert "basis=+2.00%" in text or "basis=+2.50%" in text
