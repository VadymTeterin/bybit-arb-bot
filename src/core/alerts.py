from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional, Dict

from src.telegram.formatters import format_signal


SendFunc = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class AlerterConfig:
    enable_alerts: bool
    cooldown_sec: int = 300  # дефолт: 5 хв


class RealtimeAlerter:
    """
    Простий rate-limited алертер.
    - Перевіряє cooldown на символ.
    - Форматує повідомлення (format_signal).
    - Відправляє через ін’єктований async sender.
    """

    def __init__(self, cfg: AlerterConfig, sender: SendFunc | None = None) -> None:
        self._cfg = cfg
        self._sender: Optional[SendFunc] = sender
        self._last_sent: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    def set_sender(self, sender: SendFunc) -> None:
        """Дозволяє підкинути sender пізніше (після ініціалізації)."""
        self._sender = sender

    async def maybe_send(
        self,
        symbol: str,
        spot_price: Optional[float],
        mark_price: Optional[float],
        basis_pct: Optional[float],
        vol24h_usd: Optional[float],
        ts: Optional[float] = None,
    ) -> bool:
        """
        Повертає True якщо повідомлення відправлено, інакше False.
        Не кидає виключення назовні — помилки відправки лише логічно ігноруються.
        """
        if not self._cfg.enable_alerts:
            return False

        if self._sender is None:
            # sender ще не підключили — нема куди слати
            return False

        if (
            symbol is None
            or spot_price is None
            or mark_price is None
            or basis_pct is None
            or math.isnan(basis_pct)
        ):
            return False

        now = ts if ts is not None else time.time()

        async with self._lock:
            last = self._last_sent.get(symbol, 0.0)
            if (now - last) < max(0, self._cfg.cooldown_sec):
                return False  # cooldown ще не минув

            # Готуємо повідомлення
            text = format_signal(
                symbol=symbol,
                spot_price=spot_price,
                mark_price=mark_price,
                basis_pct=basis_pct,
                vol24h_usd=vol24h_usd,
                ts=now,
            )

            try:
                await self._sender(text)
            except Exception:
                # Навмисно не пробиваємось нагору — щоб WS-потік не падав.
                return False

            self._last_sent[symbol] = now
            return True
