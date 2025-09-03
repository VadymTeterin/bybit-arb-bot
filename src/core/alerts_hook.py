from __future__ import annotations

from datetime import datetime
from loguru import logger

from src.core.alerts_gate import AlertGate
from src.infra.alerts_repo import SqliteAlertGateRepo

# Persistent repo (uses ALERTS__DB_PATH / ALERTS_DB_PATH / default 'data/alerts.db')
_repo = SqliteAlertGateRepo.from_settings()
_gate = AlertGate(
    cooldown_sec=300,
    suppress_eps_pct=0.2,
    suppress_window_min=15,
    repo=_repo,
)


def should_send(symbol: str, basis_pct: float, ts: datetime) -> tuple[bool, str]:
    """Thin wrapper so other components can ask without importing internals."""
    ok, reason = _gate.should_send(symbol=symbol, basis_pct=basis_pct, ts=ts)
    logger.debug(
        f"alerts_hook.should_send(symbol={symbol}, basis_pct={basis_pct}, ts={ts.isoformat()}): ok={ok} reason={reason}"
    )
    return ok, reason


def commit(symbol: str, basis_pct: float, ts: datetime) -> None:
    """Expose commit to persist last alert state for external callers."""
    _gate.commit(symbol=symbol, basis_pct=basis_pct, ts=ts)
