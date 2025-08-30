
# src/infra/alerts_repo.py
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, Tuple

from loguru import logger


class AlertGateRepo(Protocol):
    def get_last(self, symbol: str) -> Optional[Tuple[float, float]]: ...
    def set_last(self, symbol: str, *, ts_epoch: float, basis_pct: float) -> None: ...


@dataclass
class SqliteAlertGateRepo(AlertGateRepo):
    db_path: str

    def __post_init__(self) -> None:
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        logger.debug("SqliteAlertGateRepo initialized: {}", self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS alerts_last ("
                "symbol TEXT PRIMARY KEY,"
                "ts_epoch REAL NOT NULL,"
                "basis_pct REAL NOT NULL"
                ")"
            )

    def get_last(self, symbol: str) -> Optional[Tuple[float, float]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT ts_epoch, basis_pct FROM alerts_last WHERE symbol = ?",
                (symbol,),
            )
            row = cur.fetchone()
            if not row:
                return None
            ts_epoch, basis_pct = float(row[0]), float(row[1])
            return ts_epoch, basis_pct

    def set_last(self, symbol: str, *, ts_epoch: float, basis_pct: float) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO alerts_last(symbol, ts_epoch, basis_pct) VALUES(?, ?, ?) "
                "ON CONFLICT(symbol) DO UPDATE SET ts_epoch = excluded.ts_epoch, basis_pct = excluded.basis_pct",
                (symbol, float(ts_epoch), float(basis_pct)),
            )
            conn.commit()
