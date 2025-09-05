# src/infra/alerts_repo.py
"""
SQLite repository for alert gate:
- Keeps fast "last alert per symbol" (table: alerts)
- Adds persistent history log (table: alerts_log)
- WAL & sane pragmas
- Back-compat:
    * get_last() returns (ts_epoch, basis_pct) | None
    * set_last() accepts both 'ts_epoch' and 'ts' named arguments
"""

from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LastAlert:
    symbol: str
    ts: float          # epoch seconds (UTC)
    basis_pct: float


class SqliteAlertGateRepo:
    """
    Backed by SQLite. Thread-safe connection per instance.
    Tables:
      - alerts(symbol TEXT PRIMARY KEY, ts REAL NOT NULL, basis REAL NOT NULL)
      - alerts_log(id INTEGER PK AUTOINCREMENT, ts REAL NOT NULL, symbol TEXT NOT NULL,
                   basis REAL NOT NULL, reason TEXT NULL, tg_msg_id TEXT NULL)
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn = self._connect(db_path)
        self._ensure_schema()

    # ---------- construction ----------

    @classmethod
    def from_settings(cls, path: str | None = None) -> SqliteAlertGateRepo:
        """
        Build from environment or explicit path.
        Priority:
          1) explicit 'path' (allows ':memory:' for tests)
          2) ALERTS__DB_PATH (nested)
          3) ALERTS_DB_PATH  (flat)
          4) default 'data/alerts.db'
        """
        db_path = (
            path
            or os.getenv("ALERTS__DB_PATH")
            or os.getenv("ALERTS_DB_PATH")
            or "data/alerts.db"
        )
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return cls(db_path)

    # ---------- internals ----------

    def _connect(self, db_path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(
            db_path, isolation_level=None, timeout=30.0, check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA foreign_keys=ON;")
            cur.execute("PRAGMA temp_store=MEMORY;")
        finally:
            cur.close()
        return conn

    def _ensure_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            try:
                # Fast "last alert per symbol"
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts (
                        symbol TEXT PRIMARY KEY,
                        ts     REAL NOT NULL,
                        basis  REAL NOT NULL
                    )
                    """
                )
                # Persistent history
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts_log (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts         REAL NOT NULL,
                        symbol     TEXT NOT NULL,
                        basis      REAL NOT NULL,
                        reason     TEXT,
                        tg_msg_id  TEXT
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_log_ts ON alerts_log(ts DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_log_symbol_ts ON alerts_log(symbol, ts DESC)")
            finally:
                cur.close()

    # ---------- back-compat API ----------

    def get_last(self, symbol: str) -> tuple[float, float] | None:
        """
        Return last alert as (ts_epoch, basis_pct) or None.
        (Back-compat with existing tests and AlertGate.)
        """
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(
                    "SELECT ts, basis FROM alerts WHERE symbol = ? LIMIT 1",
                    (symbol,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return float(row["ts"]), float(row["basis"])
            finally:
                cur.close()

    def set_last(
        self,
        symbol: str,
        *,
        basis_pct: float,
        ts_epoch: float | None = None,
        ts: float | None = None,
    ) -> None:
        """
        Upsert last alert row for symbol.
        Back-compat: both 'ts_epoch' and 'ts' are accepted. Prefer ts_epoch if provided.
        """
        use_ts: float | None = ts_epoch if ts_epoch is not None else ts
        if use_ts is None:
            raise ValueError("set_last(...) requires 'ts_epoch' or 'ts'")

        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO alerts(symbol, ts, basis)
                    VALUES(?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET ts=excluded.ts, basis=excluded.basis
                    """,
                    (symbol, float(use_ts), float(basis_pct)),
                )
            finally:
                cur.close()

    # ---------- new history API ----------

    def log_event(
        self,
        symbol: str,
        *,
        ts_epoch: float,
        basis_pct: float,
        reason: str | None = None,
        tg_msg_id: str | None = None,
    ) -> int:
        """
        Insert a history record. Returns rowid.
        """
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO alerts_log(ts, symbol, basis, reason, tg_msg_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (float(ts_epoch), symbol, float(basis_pct), reason, tg_msg_id),
                )
                return int(cur.lastrowid or 0)
            finally:
                cur.close()

    def get_recent(
        self,
        *,
        limit: int = 100,
        since_ts: float | None = None,
        symbol: str | None = None,
    ) -> list[LastAlert]:
        """
        Return recent history records (as LastAlert for convenience).
        """
        where_parts: list[str] = []
        args: list[Any] = []
        if since_ts is not None:
            where_parts.append("ts >= ?")
            args.append(float(since_ts))
        if symbol:
            where_parts.append("symbol = ?")
            args.append(symbol)
        where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        sql = f"""
            SELECT symbol, ts, basis
            FROM alerts_log
            {where}
            ORDER BY ts DESC, id DESC
            LIMIT ?
        """
        args.append(int(limit))
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(sql, tuple(args))
                rows = cur.fetchall()
                return [
                    LastAlert(
                        symbol=row["symbol"],
                        ts=float(row["ts"]),
                        basis_pct=float(row["basis"]),
                    )
                    for row in rows
                ]
            finally:
                cur.close()
