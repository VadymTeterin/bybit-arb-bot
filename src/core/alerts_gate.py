# src/core/alerts_gate.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import logging

log: logging.Logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AlertGate:
    """
    Рішальник, чи надсилати алерт по символу.
    Правила (узгоджено з тестами):
    - Перший алерт по символу дозволено завжди.
    - Якщо активний cooldown (ts_now - ts_last < cooldown_sec), повторні алерти блокуються.
    - Додатково, поки триває cooldown і час з останнього алерта всередині suppress_window_min,
      дрібні зміни (Δbasis < suppress_eps_pct, у відсоткових пунктах) теж придушуються.
      У цьому випадку reason повинен містити підрядок 'Δbasis'.
    - Поза cooldown або поза suppress_window_min — правило придушення за епсилоном не діє.
    """

    cooldown_sec: int
    suppress_eps_pct: float
    suppress_window_min: int
    repo: Optional["AlertGateRepo"] = None

    _mem: Dict[str, Tuple[float, float]] = field(default_factory=dict, init=False, repr=False)

    # --------- API ---------

    def should_send(self, symbol: str, *, basis_pct: float, ts: datetime) -> Tuple[bool, str]:
        last = self._get_last(symbol)
        if not last:
            return True, "first"

        last_ts, last_basis = last
        now_epoch = _to_epoch(ts)
        elapsed = max(0.0, now_epoch - last_ts)

        reasons: list[str] = []
        in_cooldown = self.cooldown_sec > 0 and elapsed < self.cooldown_sec
        if in_cooldown:
            reasons.append("cooldown")
            in_window = elapsed <= self.suppress_window_min * 60
            if in_window and self.suppress_eps_pct > 0.0:
                delta = abs(float(basis_pct) - float(last_basis))
                if delta < self.suppress_eps_pct:
                    # ключове — включити маркер 'Δbasis' у reason
                    reasons.append(f"Δbasis={delta:.2f}pp<thr={self.suppress_eps_pct:.2f}pp")

        if reasons:
            return False, ";".join(reasons)

        return True, "ok"

    def commit(self, symbol: str, basis_pct: float, ts: datetime) -> None:
        ts_epoch = _to_epoch(ts)
        if self.repo is not None:
            self.repo.set_last(symbol, ts_epoch=ts_epoch, basis_pct=basis_pct)
        else:
            self._mem[symbol] = (ts_epoch, float(basis_pct))
        log.debug("AlertGate: commit %r at %s", symbol, datetime.fromtimestamp(ts_epoch, tz=timezone.utc).isoformat())

    # --------- helpers ---------

    def _get_last(self, symbol: str) -> Optional[Tuple[float, float]]:
        if self.repo is not None:
            return self.repo.get_last(symbol)
        return self._mem.get(symbol)

    # --------- factories ---------

    @classmethod
    def from_settings(cls, settings: Any, *, repo: Optional["AlertGateRepo"] = None) -> "AlertGate":
        """
        Безпечна фабрика: читає поля з налаштувань, але не вимагає їх обов'язкової наявності.
        """
        cooldown = int(getattr(settings, "alerts_cooldown_sec", getattr(settings, "cooldown_sec", 0)) or 0)
        eps = float(getattr(settings, "alerts_suppress_eps_pct", getattr(settings, "suppress_eps_pct", 0.0)) or 0.0)
        window_min = int(getattr(settings, "alerts_suppress_window_min", getattr(settings, "suppress_window_min", 0)) or 0)
        if repo is None:
            try:
                from src.infra.alerts_repo import SqliteAlertGateRepo  # local import to avoid heavy deps at type-time
                repo = SqliteAlertGateRepo.from_settings(settings)
            except Exception:
                repo = None
        return cls(cooldown_sec=cooldown, suppress_eps_pct=eps, suppress_window_min=window_min, repo=repo)


# Protocol is only needed for typing; we import it lazily above as well
try:
    from typing import Protocol
    class AlertGateRepo(Protocol):
        def get_last(self, symbol: str) -> Optional[Tuple[float, float]]: ...
        def set_last(self, symbol: str, *, ts_epoch: float, basis_pct: float) -> None: ...
except Exception:  # pragma: no cover - mypy/typing fallback
    AlertGateRepo = object  # type: ignore[misc]


def _to_epoch(ts: datetime) -> float:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.timestamp()
