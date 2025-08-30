
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Tuple, Protocol


# (ts_epoch, basis_pct)
LastRecord = Tuple[float, float]


class AlertGateRepo(Protocol):
    def set_last(self, symbol: str, *, ts_epoch: float, basis_pct: float) -> None: ...
    def get_last(self, symbol: str) -> Optional[LastRecord]: ...


@dataclass
class AlertGate:
    """
    Simple gate that rate-limits alert sending per symbol.

    Rules:
      - First alert always allowed.
      - If `cooldown_sec` is active (ts - last_ts < cooldown_sec) then:
          * within `suppress_window_min` minutes, alerts with |Δbasis| < `suppress_eps_pct`
            are suppressed (reason contains 'Δbasis').
          * otherwise blocked only by cooldown (reason contains 'cooldown').
      - If cooldown not active -> allowed.
    """
    cooldown_sec: int
    suppress_eps_pct: float
    suppress_window_min: int
    repo: Optional[AlertGateRepo] = None

    # fallback storage when repo is not provided
    _mem: Dict[str, LastRecord] = field(default_factory=dict, init=False, repr=False)

    @staticmethod
    def _epoch(ts: datetime) -> float:
        return ts.timestamp()

    def _get_last(self, symbol: str) -> Optional[LastRecord]:
        if self.repo is not None:
            return self.repo.get_last(symbol)
        return self._mem.get(symbol)

    def commit(self, symbol: str, basis_pct: float, ts: datetime) -> None:
        ts_epoch = self._epoch(ts)
        if self.repo is not None:
            self.repo.set_last(symbol, ts_epoch=ts_epoch, basis_pct=basis_pct)
        else:
            self._mem[symbol] = (ts_epoch, basis_pct)

    def should_send(self, symbol: str, *, basis_pct: float, ts: datetime) -> tuple[bool, str]:
        last = self._get_last(symbol)
        if last is None:
            return True, "ok-first"

        last_ts_epoch, last_basis = last
        elapsed = self._epoch(ts) - last_ts_epoch

        # inside cooldown?
        if self.cooldown_sec > 0 and elapsed < self.cooldown_sec:
            # within suppression window?
            if elapsed <= self.suppress_window_min * 60:
                delta = abs(basis_pct - last_basis)
                if delta < self.suppress_eps_pct:
                    # test expects the token 'Δbasis' in the reason
                    return False, f"cooldown;Δbasis={delta:.2f}pp<thresh={self.suppress_eps_pct:.2f}pp"
            # otherwise, simply blocked by cooldown
            return False, "cooldown"

        # no cooldown -> allowed
        return True, "ok"
