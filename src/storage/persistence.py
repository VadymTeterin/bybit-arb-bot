from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.infra.config import load_settings

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
def conn_ctx(db_path: Optional[str] = None):
    # Визначаємо шлях до БД під час виклику, щоб тести з monkeypatch.setenv працювали коректно
    if db_path is None:
        env_db = os.getenv("DB_PATH")
        if env_db:
            db_path = env_db
        else:
            try:
                db_path = load_settings().db_path  # fallback на конфіг
            except Exception:
                db_path = "data/signals.db"

    # Гарантуємо існування директорії
    dirn = os.path.dirname(db_path)
    if dirn and not os.path.isdir(dirn):
        os.makedirs(dirn, exist_ok=True)

    # row_factory дає можливість отримувати dict-подібні рядки за назвою колонки (якщо у вас це потрібно — додайте)
    con = sqlite3.connect(db_path)
    try:
        yield con
    finally:
        con.close()


def init_db() -> None:
    """РЎС‚РІРѕСЂСЋС” С‚Р°Р±Р»РёС†С–, СЏРєС‰Рѕ С—С… РЅРµРјР°С”."""
    with conn_ctx() as con:
        con.executescript(SCHEMA)
        con.commit()


def _ts_to_db_value(ts: datetime | None) -> str:
    """Р—Р±РµСЂС–РіР°С”РјРѕ С‡Р°СЃ Сѓ ISO8601 (UTC, naive)."""
    if ts is None:
        ts = datetime.now(timezone.utc)
    # sqlite РґРѕР±СЂРµ РїСЂР°С†СЋС” Р· С‚РµРєСЃС‚РѕРІРёРјРё ISO-СЂСЏРґРєР°РјРё
    return ts.isoformat(timespec="microseconds")


def _parse_ts(val: Any) -> Optional[datetime]:
    """РђРєСѓСЂР°С‚РЅРѕ РїР°СЂСЃРёРјРѕ timestamp Р· Р‘Р” (str -> datetime)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        # РѕС‡С–РєСѓС”РјРѕ ISO-СЂСЏРґРѕРє, СЏРєРёР№ РјРё СЃР°РјС– С– Р·Р°РїРёСЃСѓС”РјРѕ
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
    """Р—Р°РїРёСЃСѓС” РЅРѕРІРёР№ СЃРёРіРЅР°Р» Сѓ Р‘Р”."""
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
    """РћС‚СЂРёРјСѓС” СЃРёРіРЅР°Р»Рё Р·Р° РѕСЃС‚Р°РЅРЅС– last_hours РіРѕРґРёРЅ, РІС–РґСЃРѕСЂС‚РѕРІР°РЅС– Р·Р° basis_pct (СЃРїР°РґРЅРѕ)."""
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
        # РїРѕРІРµСЂРЅРµРјРѕ timestamp СЏРє ISO-СЂСЏРґРѕРє (СЏРє С– Р·Р°РїРёСЃР°РЅРёР№) вЂ” СЃСѓРјС–СЃРЅРѕ Р· С–СЃРЅСѓСЋС‡РёРј РєРѕРґРѕРј
        return rows


# ---------------------
#   COOLDOWN API
# ---------------------


def get_last_signal_ts(symbol: str) -> Optional[datetime]:
    """
    РџРѕРІРµСЂС‚Р°С” С‡Р°СЃ РѕСЃС‚Р°РЅРЅСЊРѕРіРѕ СЃРёРіРЅР°Р»Сѓ РґР»СЏ СЃРёРјРІРѕР»Сѓ Р°Р±Рѕ None, СЏРєС‰Рѕ Р·Р°РїРёСЃС–РІ РЅРµРјР°С”.
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
        # row[0] вЂ” ISO-СЂСЏРґРѕРє (Р°Р±Рѕ datetime, Р·Р°Р»РµР¶РЅРѕ РІС–Рґ РґСЂР°Р№РІРµСЂР°)
        return _parse_ts(row[0])


def recent_signal_exists(symbol: str, cooldown_sec: int) -> bool:
    """
    РџРµСЂРµРІС–СЂСЏС”, С‡Рё С–СЃРЅСѓС” СЃРІС–Р¶РёР№ Р·Р°РїРёСЃ РїРѕ СЃРёРјРІРѕР»Сѓ РІ РјРµР¶Р°С… cooldown.
    True  -> СЃРёРіРЅР°Р» Р±СѓРІ РЅРµРґР°РІРЅРѕ (С‰Рµ РІ В«РєСѓР»РґР°СѓРЅС–В»), Р·Р±РµСЂС–РіР°С‚Рё РЅРµ С‚СЂРµР±Р°
    False -> РјРѕР¶РЅР° Р·Р±РµСЂС–РіР°С‚Рё РЅРѕРІРёР№ СЃРёРіРЅР°Р»
    """
    last_ts = get_last_signal_ts(symbol)
    if last_ts is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=int(cooldown_sec))
    return last_ts >= cutoff
