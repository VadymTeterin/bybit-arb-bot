from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .alerts_gate import AlertsGate
from ..infra.notify_telegram import TelegramNotifier, make_label

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AlertContext:
    symbol: str
    basis_pct: float
    text: str  # готовий текст повідомлення (без мітки)


class AlertsHook:
    """Зручна обгортка: перевіряє Gate та (за потреби) шле у Telegram."""

    def __init__(
        self,
        gate: AlertsGate,
        notifier: Optional[TelegramNotifier] = None,
    ) -> None:
        self._gate = gate
        self._notifier = notifier

    def process(self, *, ctx: AlertContext, ts) -> bool:
        allow, reason = self._gate.allow(symbol=ctx.symbol, basis_pct=ctx.basis_pct, ts=ts)
        if not allow:
            logger.debug("alert suppressed: %s (%s)", ctx, reason)
            return False

        self._gate.commit(symbol=ctx.symbol, basis_pct=ctx.basis_pct, ts=ts)
        label = make_label(ctx.symbol, ctx.basis_pct)
        if self._notifier is not None:
            self._notifier.send(ctx.text, label=label)
        return True