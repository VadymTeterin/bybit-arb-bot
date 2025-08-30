from __future__ import annotations

from datetime import datetime
from typing import Tuple

from loguru import logger

from src.core.alerts_gate import AlertGate
from src.infra.alerts_repo import SqliteAlertGateRepo

# Local, lightweight wiring that doesn't pull configs:
_repo = SqliteAlertGateRepo.from_settings(":memory:")
_gate = AlertGate(cooldown_sec=300, suppress_eps_pct=0.2, suppress_window_min=15, repo=_repo)


def should_send(symbol: str, basis_pct: float, ts: datetime) -> Tuple[bool, str]:
    """
    Thin wrapper so other components can ask the question without importing internals.
    Use keyword args for AlertGate API to satisfy typing (basis/ts are keyword-only).
    """
    ok, reason = _gate.should_send(symbol=symbol, basis_pct=basis_pct, ts=ts)
    logger.debug(f"alerts_hook.should_send({symbol=}, {basis_pct=}, ts={ts.isoformat()}): {ok=} {reason=}")
    return ok, reason
