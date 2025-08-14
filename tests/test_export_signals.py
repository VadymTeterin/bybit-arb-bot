from __future__ import annotations
import csv
import sqlite3
from datetime import datetime, timedelta
from importlib import reload
from pathlib import Path

from src.storage import persistence as _persistence
from scripts import export_signals


def _seed(db_path: Path, rows):
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    for r in rows:
        cur.execute(
            """
            INSERT INTO signals(symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (r["symbol"], r["spot"], r["fut"], r["basis"], r["vol"], r["ts"]),
        )
    con.commit()
    con.close()


def test_export_last_24h(tmp_path, monkeypatch):
    # Тимчасова БД і прив'язка шляху через env
    db = tmp_path / "t.db"
    monkeypatch.setenv("DB_PATH", str(db))

    # Перечитати модуль persistence, щоб він побачив новий DB_PATH
    persistence = reload(_persistence)

    # 1) Ініціалізація схеми в tmp БД
    persistence.init_db()

    # 2) Seed даних: один старше 24h, два в межах 24h
    now = datetime.utcnow()
    old = now - timedelta(hours=30)
    recent1 = now - timedelta(hours=1)
    recent2 = now - timedelta(hours=2)

    _seed(
        db,
        [
            {"symbol": "OLDUSDT", "spot": 2.0, "fut": 2.1, "basis": 5.0, "vol": 50_000_000.0, "ts": old.isoformat()},
            {"symbol": "ETHUSDT", "spot": 3000.0, "fut": 3030.0, "basis": 1.0, "vol": 800_000_000.0, "ts": recent1.isoformat()},
            {"symbol": "BTCUSDT", "spot": 64000.0, "fut": 64500.0, "basis": 0.78, "vol": 1_200_000_000.0, "ts": recent2.isoformat()},
        ],
    )

    out = tmp_path / "signals_test.csv"
    path = export_signals.export_signals(out_path=out, last_hours=24, limit=None, tz=None)

    # CSV створено
    assert path.exists()

    # Перевірка вмісту
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Є заголовок + 2 рядки (ETH, BTC), але не OLDUSDT
    assert rows[0] == ["timestamp", "symbol", "spot_price", "futures_price", "basis_pct", "volume_24h_usd"]
    assert len(rows) == 1 + 2
    syms = {r[1] for r in rows[1:]}
    assert syms == {"ETHUSDT", "BTCUSDT"}
