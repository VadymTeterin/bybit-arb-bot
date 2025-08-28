"""
AlertGate (Step 6.3.4) — cooldown + suppression

Semantics (v2):
  - Cooldown blocks ANY repeat alert for the same symbol within `cooldown_sec`.
  - Suppression of near-duplicate basis is applied **only while cooldown is active**.
    Rationale: after cooldown expires we allow a new alert, even for a small Δbasis,
    to keep the channel updated at a human pace.

Persistence adapter (optional):
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
        :param suppress_window_min: Compare with last alert within this window (minutes) —
                                    but ONLY while cooldown is active.
        :param repo: Optional persistence adapter with (get_last, set_last) API.
        """
        self.cooldown_sec = int(max(0, cooldown_sec))
        self.suppress_eps_pct = float(max(0.0, suppress_eps_pct))
        self.suppress_window_min = int(max(0, suppress_window_min))
        self.repo = repo
        self._mem: Dict[str, _LastEvent] = {}

    @classmethod
    def from_settings(cls, settings) -> AlertGate:
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
                rec = self.repo.get_last(symbol)
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

    def should_send(self, symbol: str, basis_pct: float, ts: datetime) -> Tuple[bool, str]:
        """Decide whether an alert should be sent."""
        ts = _to_utc(ts)
        t_epoch = ts.timestamp()

        last = self._load_last(symbol)
        if last is None:
            return True, ""

        dt = t_epoch - last.ts_epoch
        # 1) Cooldown check
        if self.cooldown_sec > 0 and dt < self.cooldown_sec:
            # 2) Suppression only while cooldown is active
            if self.suppress_window_min > 0 and dt <= self.suppress_window_min * 60:
                delta_pp = abs(float(basis_pct) - last.basis_pct)
                if delta_pp < self.suppress_eps_pct:
                    return False, (
                        f"suppress: |Δbasis|={delta_pp:.4f}pp < eps={self.suppress_eps_pct:.4f}pp "
                        f"within cooldown ({self.suppress_window_min}min window)"
                    )
            return (
                False,
                f"cooldown({self.cooldown_sec}s) active; last at {last.ts_epoch:.0f}",
            )

        # after cooldown -> allowed (regardless of small delta)
        return True, ""

    def commit(self, symbol: str, basis_pct: float, ts: datetime) -> None:
        ts = _to_utc(ts)
        self._store_last(symbol, _LastEvent(ts_epoch=ts.timestamp(), basis_pct=float(basis_pct)))
