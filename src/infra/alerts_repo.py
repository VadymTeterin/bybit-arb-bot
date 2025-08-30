# src/infra/alerts_repo.py
"""
Persistence adapter for Alerts Gate (SQLite)
-------------------------------------------
Minimal API used by tests:
    - get_last(symbol) -> tuple[float, float] | None      # (ts_epoch, basis_pct)
    - set_last(symbol, ts_epoch, basis_pct) -> None
Optional helpers (safe no-ops in tests):
    - purge_older_than(min_ts) -> int
    - clear() -> None
    - close() / context manager support
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

__all__ = ["SqliteAlertGateRepo", "AlertRecord"]


@dataclass(frozen=True, slots=True)
class AlertRecord:
    symbol: str
    ts_epoch: float
    basis_pct: float


class SqliteAlertGateRepo:
    def __init__(self, db_path: str | Path = "data/signals.db") -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path.as_posix(), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts_last (
                symbol TEXT PRIMARY KEY,
                ts_epoch REAL NOT NULL,
                basis_pct REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    # --- Basic API used by gate -------------------------------------------------
    def get_last(self, symbol: str) -> tuple[float, float] | None:
        cur = self._conn.execute(
            "SELECT ts_epoch, basis_pct FROM alerts_last WHERE symbol = ?",
            (symbol,),
        )
        row = cur.fetchone()
        return (float(row[0]), float(row[1])) if row else None

    def set_last(self, symbol: str, ts_epoch: float, basis_pct: float) -> None:
        self._conn.execute(
            """
            INSERT INTO alerts_last(symbol, ts_epoch, basis_pct)
            VALUES (?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                ts_epoch=excluded.ts_epoch,
                basis_pct=excluded.basis_pct
            """,
            (symbol, float(ts_epoch), float(basis_pct)),
        )
        self._conn.commit()

    # --- Utilities --------------------------------------------------------------
    def purge_older_than(self, min_ts: float) -> int:
        cur = self._conn.execute(
            "DELETE FROM alerts_last WHERE ts_epoch < ?", (float(min_ts),)
        )
        self._conn.commit()
        return cur.rowcount

    def clear(self) -> None:
        self._conn.execute("DELETE FROM alerts_last")
        self._conn.commit()

    # --- Context manager & cleanup ---------------------------------------------
    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self) -> "SqliteAlertGateRepo":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # --- Introspection ----------------------------------------------------------
    @property
    def path(self) -> Path:
        return self._path
