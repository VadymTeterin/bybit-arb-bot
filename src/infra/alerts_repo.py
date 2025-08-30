from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional, Tuple

from loguru import logger


class AlertGateRepo:
    """Protocol-like base for alert persistence."""

    def get_last(self, symbol: str) -> Optional[Tuple[float, float]]:  # (ts_epoch, basis_pct)
        raise NotImplementedError

    def set_last(self, symbol: str, *, ts_epoch: float, basis_pct: float) -> None:
        raise NotImplementedError


@dataclass
class SqliteAlertGateRepo(AlertGateRepo):
    """
    Lightweight SQLite-backed storage for last alert per symbol.
    Schema: alerts(symbol TEXT PRIMARY KEY, ts REAL, basis REAL)
    """
    path: str
    _conn: sqlite3.Connection | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.path)
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS alerts ("
                "symbol TEXT PRIMARY KEY, "
                "ts REAL NOT NULL, "
                "basis REAL NOT NULL)"
            )
        logger.debug(f"SqliteAlertGateRepo initialized: {self.path}")

    @classmethod
    def from_settings(cls, db_path: Optional[str] = None) -> "SqliteAlertGateRepo":
        """
        Convenience factory used by higher-level wiring.
        If db_path is None, uses in-memory database (good for tests / defaults).
        """
        return cls(db_path or ":memory:")

    # --- AlertGateRepo API -------------------------------------------------

    def get_last(self, symbol: str) -> Optional[Tuple[float, float]]:
        assert self._conn is not None
        cur = self._conn.execute("SELECT ts, basis FROM alerts WHERE symbol = ?", (symbol,))
        row = cur.fetchone()
        if row is None:
            return None
        ts, basis = row
        return float(ts), float(basis)

    def set_last(self, symbol: str, *, ts_epoch: float, basis_pct: float) -> None:
        assert self._conn is not None
        with self._conn:
            self._conn.execute(
                "INSERT INTO alerts(symbol, ts, basis) VALUES (?, ?, ?) "
                "ON CONFLICT(symbol) DO UPDATE SET ts = excluded.ts, basis = excluded.basis",
                (symbol, float(ts_epoch), float(basis_pct)),
            )
