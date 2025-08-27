# -*- coding: utf-8 -*-
"""
AlertGate (Step 6.3.4)
----------------------
Implements per-symbol cooldown and near-duplicate suppression for Telegram alerts.

Usage (example):
    from datetime import datetime, timezone
    from src.infra.config import get_settings
    from src.core.alerts_gate import AlertGate

    s = get_settings()
    gate = AlertGate.from_settings(s)

    now = datetime.now(timezone.utc)
    ok, reason = gate.should_send("BTCUSDT", basis_pct=1.37, ts=now)
    if ok:
        # send_telegram_alert(...)
        gate.commit("BTCUSDT", basis_pct=1.37, ts=now)
    else:
        logger.info("Alert suppressed for BTCUSDT: %s", reason)

Notes:
- The gate keeps state in-memory by default.
- You can inject a persistence adapter via the repo parameter to keep state across restarts:
    repo.get_last(symbol) -> tuple[float, float] | None        # (ts_epoch, basis_pct)
    repo.set_last(symbol, ts_epoch: float, basis_pct: float) -> None
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

try:
    from loguru import logger  # type: ignore
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)


def _to_utc(ts: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC)."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


@dataclass
class _LastEvent:
    ts_epoch: float
    basis_pct: float


class AlertGate:
    """Cooldown + suppression gate per trading symbol."""

    def __init__(
        self,
        cooldown_sec: int = 300,
        suppress_eps_pct: float = 0.2,
        suppress_window_min: int = 15,
        repo: Optional[object] = None,
    ) -> None:
        """
        :param cooldown_sec: Minimal seconds between alerts for the same symbol.
        :param suppress_eps_pct: Suppress if |Δbasis| < this (percentage points).
        :param suppress_window_min: Compare with last alert if it's not older than this window (minutes).
        :param repo: Optional persistence adapter with (get_last, set_last) API.
        """
        self.cooldown_sec = int(max(0, cooldown_sec))
        self.suppress_eps_pct = float(max(0.0, suppress_eps_pct))
        self.suppress_window_min = int(max(0, suppress_window_min))
        self.repo = repo
        self._mem: Dict[str, _LastEvent] = {}

    # ---------- factory ----------

    @classmethod
    def from_settings(cls, settings) -> "AlertGate":
        """Create gate from AppSettings (src.infra.config.get_settings())."""
        a = settings.alerts
        return cls(
            cooldown_sec=int(getattr(a, "cooldown_sec", 300)),
            suppress_eps_pct=float(getattr(a, "suppress_eps_pct", 0.2)),
            suppress_window_min=int(getattr(a, "suppress_window_min", 15)),
        )

    # ---------- persistence helpers ----------

    def _load_last(self, symbol: str) -> Optional[_LastEvent]:
        if symbol in self._mem:
            return self._mem[symbol]
        if self.repo and hasattr(self.repo, "get_last"):
            try:
                rec = self.repo.get_last(
                    symbol
                )  # expected (ts_epoch, basis_pct) or None
                if rec:
                    ev = _LastEvent(ts_epoch=float(rec[0]), basis_pct=float(rec[1]))
                    self._mem[symbol] = ev
                    return ev
            except Exception as e:  # pragma: no cover
                logger.warning("AlertGate repo.get_last failed for %s: %s", symbol, e)
        return None

    def _store_last(self, symbol: str, ev: _LastEvent) -> None:
        self._mem[symbol] = ev
        if self.repo and hasattr(self.repo, "set_last"):
            try:
                self.repo.set_last(symbol, ev.ts_epoch, ev.basis_pct)
            except Exception as e:  # pragma: no cover
                logger.warning("AlertGate repo.set_last failed for %s: %s", symbol, e)

    # ---------- public API ----------

    def should_send(
        self, symbol: str, basis_pct: float, ts: datetime
    ) -> Tuple[bool, str]:
        """
        Decide whether an alert should be sent.
        :return: (allowed, reason) where reason is empty string if allowed.
        """
        ts = _to_utc(ts)
        t_epoch = ts.timestamp()

        last = self._load_last(symbol)

        # 1) Cooldown check
        if last is not None and self.cooldown_sec > 0:
            if (t_epoch - last.ts_epoch) < self.cooldown_sec:
                return (
                    False,
                    f"cooldown({self.cooldown_sec}s) active; last at {last.ts_epoch:.0f}",
                )

        # 2) Suppression of near-duplicate basis (within window)
        if last is not None and self.suppress_window_min > 0:
            window_sec = self.suppress_window_min * 60
            if (t_epoch - last.ts_epoch) <= window_sec:
                delta_pp = abs(float(basis_pct) - last.basis_pct)
                if delta_pp < self.suppress_eps_pct:
                    return (
                        False,
                        f"suppress: |Δbasis|={delta_pp:.4f}pp < eps={self.suppress_eps_pct:.4f}pp "
                        f"within {self.suppress_window_min}min",
                    )

        return True, ""

    def commit(self, symbol: str, basis_pct: float, ts: datetime) -> None:
        """Record the fact that the alert was sent (update last event)."""
        ts = _to_utc(ts)
        self._store_last(
            symbol, _LastEvent(ts_epoch=ts.timestamp(), basis_pct=float(basis_pct))
        )
