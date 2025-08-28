# src/core/alerts.py
from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, cast

# --- безпечне підключення форматера сигналів ---
try:
    from src.telegram import formatters as _formatters

    _FORMAT_SIGNAL: Callable[..., str] = cast(Callable[..., str], _formatters.format_signal)
except Exception:  # pragma: no cover - захист від відсутності модулів у середовищі тестів

    def _FORMAT_SIGNAL(*_args: Any, **_kwargs: Any) -> str:
        # мінімальний запасний варіант для розробницького режиму
        sym = _kwargs.get("symbol") or (_args[0] if _args else "?")
        bpct = _kwargs.get("basis_pct")
        return f"[signal] {sym} | basis={bpct}"

    _FORMAT_SIGNAL = _FORMAT_SIGNAL  # type: ignore[assignment]


def _format_signal_safe(**data: Any) -> str:
    """
    Адаптер: передає у format_signal тільки ті імена параметрів, які він реально підтримує.
    Це усуває mypy-помилки та запобігає рантайм-TypeError при змінених сигнатурах.
    """
    try:
        import inspect

        params = inspect.signature(_FORMAT_SIGNAL).parameters
        supported = {k: v for k, v in data.items() if k in params}
        # Якщо форматер приймає **kwargs — просто пройдуть і невідомі
        # Якщо ні — ми вже відфільтрували зайве
        return _FORMAT_SIGNAL(**supported)
    except Exception:
        # Непередбачена ситуація — повертаємо стислий fallback
        sym = data.get("symbol", "?")
        bpct = data.get("basis_pct")
        return f"[signal] {sym} | basis={bpct}"


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

            # Готуємо повідомлення через безпечний адаптер
            text = _format_signal_safe(
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


# --- optional: Telegram async sender (non-invasive) ---
try:
    from src.infra import config as _cfg
    from src.infra.notify_telegram import TelegramNotifier

    async def telegram_sender(text: str) -> None:
        """
        Безпечно викликається як SendFunc (Awaitable[None]).
        Працює тільки якщо TELEGRAM_ENABLED увімкнено.
        """
        if not getattr(_cfg, "TELEGRAM_ENABLED", False):
            return
        notifier = TelegramNotifier(enabled=True)
        loop = asyncio.get_running_loop()
        # виконуємо синхронну відправку у пулі без блокування event loop
        await loop.run_in_executor(None, lambda: notifier.send_text(text))

except Exception:
    # fail-silent: не впливаємо на основний цикл алертів
    pass
