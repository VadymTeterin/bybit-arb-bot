# src/storage/persistence.py
"""SQLite persistence layer for signals & quotes.

Notes:
  - Comments in English (per project guidelines).
  - Backward compatible with existing 'signals' table used by tests/selector.
  - Adds 'quotes' and 'meta' tables + retention sweeper.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# Keep import path consistent with current repo layout
from src.infra.config import load_settings

# -----------------------------
# Schema (idempotent)
# -----------------------------
SCHEMA = """
PRAGMA journal_mode=WAL;

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

CREATE TABLE IF NOT EXISTS quotes (
    symbol TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    spot_price REAL,
    futures_price REAL,
    basis_pct REAL,
    volume_24h_usd REAL,
    PRIMARY KEY (symbol, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_quotes_ts ON quotes(timestamp);
CREATE INDEX IF NOT EXISTS idx_quotes_symbol_ts ON quotes(symbol, timestamp);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

META_SCHEMA_VERSION = "1"
META_SCHEMA_KEY = "schema_version"


# -----------------------------
# Connection utils
# -----------------------------
@contextmanager
def conn_ctx(db_path: Optional[str] = None):
    """Yield a SQLite connection. The path is resolved as:
    1) explicit arg
    2) env var DB_PATH (for tests)
    3) settings().db_path
    4) default 'data/signals.db'
    Also ensures parent directory exists.
    """
    if db_path is None:
        env_db = os.getenv("DB_PATH")
        if env_db:
            db_path = env_db
        else:
            try:
                db_path = load_settings().db_path  # fallback to config
            except Exception:
                db_path = "data/signals.db"

    parent = os.path.dirname(db_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    con = sqlite3.connect(db_path)
    try:
        yield con
    finally:
        con.close()


def _ts_to_db_value(ts: Optional[datetime] = None) -> str:
    """Return ISO timestamp string (microseconds, UTC) for SQLite."""
    if ts is None:
        ts = datetime.now(timezone.utc)
    # Normalize to aware (UTC) and output with microseconds
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.isoformat(timespec="microseconds")


def _parse_ts(val: Any) -> Optional[datetime]:
    """Safe timestamp parse from DB (str -> datetime | None)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return None


# -----------------------------
# Bootstrap / Migration
# -----------------------------
def init_db() -> None:
    """Create tables if missing and set meta schema version."""
    with conn_ctx() as con:
        con.executescript(SCHEMA)
        # Upsert schema version in meta
        con.execute(
            """INSERT INTO meta(key, value) VALUES(?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (META_SCHEMA_KEY, META_SCHEMA_VERSION),
        )
        con.commit()


# -----------------------------
# Signals API
# -----------------------------
def save_signal(
    symbol: str,
    spot: float,
    fut: float,
    basis_pct: float,
    vol_usd: float,
    ts: datetime | None = None,
) -> None:
    """Insert a new signal row."""
    with conn_ctx() as con:
        con.execute(
            """
            INSERT INTO signals(symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                float(spot),
                float(fut),
                float(basis_pct),
                float(vol_usd),
                _ts_to_db_value(ts),
            ),
        )
        con.commit()


def get_signals(last_hours: int = 24, limit: int | None = None) -> List[Dict[str, Any]]:
    """Return recent signals for the last N hours, ordered by basis_pct desc."""
    since = datetime.now(timezone.utc) - timedelta(hours=int(last_hours))
    q = (
        "SELECT symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp "
        "FROM signals WHERE timestamp >= ? ORDER BY basis_pct DESC"
    )
    params: List[Any] = [_ts_to_db_value(since)]
    if limit:
        q += f" LIMIT {int(limit)}"
    with conn_ctx() as con:
        cur = con.execute(q, params)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return rows


def get_last_signal_ts(symbol: str) -> Optional[datetime]:
    """Return timestamp of the last signal for a symbol or None."""
    with conn_ctx() as con:
        cur = con.execute(
            """SELECT timestamp FROM signals WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1""",
            (symbol,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return _parse_ts(row[0])


def recent_signal_exists(symbol: str, cooldown_sec: int) -> bool:
    """Return True if there's a recent signal within cooldown window."""
    last_ts = get_last_signal_ts(symbol)
    if last_ts is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=int(cooldown_sec))
    return last_ts >= cutoff


# -----------------------------
# Quotes API
# -----------------------------
def save_quote(
    symbol: str,
    spot: Optional[float],
    fut: Optional[float],
    basis_pct: Optional[float],
    vol_usd: Optional[float],
    ts: datetime | None = None,
) -> None:
    """Upsert a quote snapshot for (symbol, ts)."""
    with conn_ctx() as con:
        con.execute(
            """
            INSERT INTO quotes(symbol, timestamp, spot_price, futures_price, basis_pct, volume_24h_usd)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, timestamp) DO UPDATE SET
                spot_price=excluded.spot_price,
                futures_price=excluded.futures_price,
                basis_pct=excluded.basis_pct,
                volume_24h_usd=excluded.volume_24h_usd
            """.strip(),
            (
                symbol,
                _ts_to_db_value(ts),
                None if spot is None else float(spot),
                None if fut is None else float(fut),
                None if basis_pct is None else float(basis_pct),
                None if vol_usd is None else float(vol_usd),
            ),
        )
        con.commit()


# -----------------------------
# Retention API
# -----------------------------
def retention_sweep(days: int = 30) -> Tuple[int, int]:
    """Delete old rows from signals/quotes older than `days`. Return (signals_deleted, quotes_deleted)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    cutoff_iso = _ts_to_db_value(cutoff)
    with conn_ctx() as con:
        cur1 = con.execute("DELETE FROM signals WHERE timestamp < ?", (cutoff_iso,))
        cur2 = con.execute("DELETE FROM quotes  WHERE timestamp < ?", (cutoff_iso,))
        con.commit()
        return cur1.rowcount or 0, cur2.rowcount or 0
