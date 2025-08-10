from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.infra.config import load_settings

settings = load_settings()

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    spot_price REAL NOT NULL,
    futures_price REAL NOT NULL,
    basis_pct REAL NOT NULL,
    volume_24h_usd REAL NOT NULL,
    timestamp DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_ts ON signals(symbol, timestamp);
"""

@contextmanager
def conn_ctx(db_path: str = settings.db_path):
    con = sqlite3.connect(db_path)
    try:
        yield con
    finally:
        con.close()

def init_db():
    """Створює таблиці, якщо їх немає."""
    with conn_ctx() as con:
        con.executescript(SCHEMA)
        con.commit()

def save_signal(symbol: str, spot: float, fut: float, basis_pct: float, vol_usd: float, ts: datetime | None = None):
    """Записує новий сигнал у БД."""
    if ts is None:
        ts = datetime.utcnow()
    with conn_ctx() as con:
        con.execute(
            "INSERT INTO signals(symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp) VALUES (?,?,?,?,?,?)",
            (symbol, float(spot), float(fut), float(basis_pct), float(vol_usd), ts),
        )
        con.commit()

def get_signals(last_hours: int = 24, limit: int | None = None) -> List[Dict[str, Any]]:
    """Отримує сигнали за останні last_hours годин, відсортовані за basis_pct (спадно)."""
    since = datetime.utcnow() - timedelta(hours=last_hours)
    q = """
    SELECT symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp
    FROM signals
    WHERE timestamp >= ?
    ORDER BY basis_pct DESC
    """
    if limit:
        q += f" LIMIT {int(limit)}"
    with conn_ctx() as con:
        cur = con.execute(q, (since,))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
