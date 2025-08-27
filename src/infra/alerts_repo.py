# -*- coding: utf-8 -*-
"""SQLite-backed repo for AlertGate persistence (Step 6.3.5).

API expected by AlertGate:
  - get_last(symbol) -> tuple[ts_epoch: float, basis_pct: float] | None
  - set_last(symbol, ts_epoch: float, basis_pct: float) -> None
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import Optional, Tuple

try:
    from loguru import logger  # type: ignore
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)


class SqliteAlertGateRepo:
    """Thread-safe minimal SQLite repo for AlertGate state."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        # Ensure parent dir exists
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_schema()

    @classmethod
    def from_settings(cls, settings) -> "SqliteAlertGateRepo":
        # Priority: env ALERTS_DB_PATH -> settings.persistence.alerts_db -> ./data/alerts.db
        env_path = os.getenv("ALERTS_DB_PATH") or os.getenv("ALERTS__DB_PATH")
        if env_path:
            return cls(env_path)
        try:
            p = getattr(getattr(settings, "persistence", object()), "alerts_db", None)
            if p:
                return cls(str(p))
        except Exception:
            pass
        return cls(os.path.join(".", "data", "alerts.db"))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """                    CREATE TABLE IF NOT EXISTS alert_state (
                    symbol TEXT PRIMARY KEY,
                    ts_epoch REAL NOT NULL,
                    basis_pct REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )
            # Simple index is implicit via PK
            conn.commit()

    # ---- Public API ----
    def get_last(self, symbol: str) -> Optional[Tuple[float, float]]:
        sym = (symbol or "").upper().strip()
        if not sym:
            return None
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT ts_epoch, basis_pct FROM alert_state WHERE symbol = ?;",
                (sym,),
            )
            row = cur.fetchone()
            return (float(row[0]), float(row[1])) if row else None

    def set_last(self, symbol: str, ts_epoch: float, basis_pct: float) -> None:
        sym = (symbol or "").upper().strip()
        if not sym:
            return
        now = time.time()
        with self._lock, self._connect() as conn:
            conn.execute(
                """                    INSERT INTO alert_state(symbol, ts_epoch, basis_pct, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    ts_epoch = excluded.ts_epoch,
                    basis_pct = excluded.basis_pct,
                    updated_at = excluded.updated_at;
                """,
                (sym, float(ts_epoch), float(basis_pct), now),
            )
            conn.commit()
