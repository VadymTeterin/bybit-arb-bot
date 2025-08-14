from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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
    # row_factory дозволяє отримувати dict-подібні рядки за назвою колонки
    con = sqlite3.connect(db_path)
    try:
        yield con
    finally:
        con.close()


def init_db() -> None:
    """Створює таблиці, якщо їх немає."""
    with conn_ctx() as con:
        con.executescript(SCHEMA)
        con.commit()


def _ts_to_db_value(ts: datetime | None) -> str:
    """Зберігаємо час у ISO8601 (UTC, naive)."""
    if ts is None:
        ts = datetime.now(timezone.utc)
    # sqlite добре працює з текстовими ISO-рядками
    return ts.isoformat(timespec="microseconds")


def _parse_ts(val: Any) -> Optional[datetime]:
    """Акуратно парсимо timestamp з БД (str -> datetime)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        # очікуємо ISO-рядок, який ми самі і записуємо
        return datetime.fromisoformat(str(val))
    except Exception:
        return None


def save_signal(
    symbol: str,
    spot: float,
    fut: float,
    basis_pct: float,
    vol_usd: float,
    ts: datetime | None = None,
) -> None:
    """Записує новий сигнал у БД."""
    with conn_ctx() as con:
        con.execute(
            """
            INSERT INTO signals(symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp)
            VALUES (?,?,?,?,?,?)
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
    """Отримує сигнали за останні last_hours годин, відсортовані за basis_pct (спадно)."""
    since = datetime.now(timezone.utc) - timedelta(hours=last_hours)
    q = """
        SELECT symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp
        FROM signals
        WHERE timestamp >= ?
        ORDER BY basis_pct DESC
    """
    params: list[Any] = [_ts_to_db_value(since)]
    if limit:
        q += f" LIMIT {int(limit)}"
    with conn_ctx() as con:
        cur = con.execute(q, params)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        # повернемо timestamp як ISO-рядок (як і записаний) — сумісно з існуючим кодом
        return rows


# ---------------------
#   COOLDOWN API
# ---------------------


def get_last_signal_ts(symbol: str) -> Optional[datetime]:
    """
    Повертає час останнього сигналу для символу або None, якщо записів немає.
    """
    with conn_ctx() as con:
        cur = con.execute(
            """
            SELECT timestamp
            FROM signals
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (symbol,),
        )
        row = cur.fetchone()
        if not row:
            return None
        # row[0] — ISO-рядок (або datetime, залежно від драйвера)
        return _parse_ts(row[0])


def recent_signal_exists(symbol: str, cooldown_sec: int) -> bool:
    """
    Перевіряє, чи існує свіжий запис по символу в межах cooldown.
    True  -> сигнал був недавно (ще в «кулдауні»), зберігати не треба
    False -> можна зберігати новий сигнал
    """
    last_ts = get_last_signal_ts(symbol)
    if last_ts is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=int(cooldown_sec))
    return last_ts >= cutoff
