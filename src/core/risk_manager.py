from __future__ import annotations
from dataclasses import dataclass


@dataclass(slots=True)
class RiskConfig:
    dry_run: bool
    max_pos_usd: float
    max_exposure_pct: float


class RiskManager:
    """Phase 7 scaffold (7.0.0): placeholder interface; logic arrives in 7.1.x."""

    def __init__(self, cfg: RiskConfig) -> None:
        self.cfg = cfg

    def check(self) -> bool:
        """Placeholder: always allow. Real checks will enforce limits in 7.1.x."""
        return True
