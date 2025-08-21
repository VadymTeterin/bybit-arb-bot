from __future__ import annotations

from typing import Any, Optional, cast

from src.infra import config
from src.telegram.sender import TelegramSender


def _load_settings_safe() -> Any | None:
    """
    Акуратно пробуємо отримати налаштування через load_settings(),
    не фіксуючи саму функцію в змінній (щоб уникнути конфлікту типів з mypy).
    """
    try:
        from src.infra.config import load_settings  # type: ignore[attr-defined]
    except Exception:
        return None

    try:
        return load_settings()
    except Exception:
        return None


class TelegramNotifier:
    """
    Невтручальний адаптер для відправки повідомлень у Telegram.

    Джерела конфігурації (пріоритет зверху вниз):
    1) Аргументи конструктора
    2) Плоскі змінні в src.infra.config: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / TELEGRAM_COOLDOWN_SECONDS
    3) Nested settings: load_settings().telegram.bot_token / .alert_chat_id, а також settings.alert_cooldown_sec
    """

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        cooldown_s: Optional[int] = None,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled

        # 1) аргументи або плоскі значення з config
        _token = token or cast(
            Optional[str], getattr(config, "TELEGRAM_BOT_TOKEN", None)
        )
        _chat = chat_id or cast(
            Optional[str], getattr(config, "TELEGRAM_CHAT_ID", None)
        )
        _cooldown_opt = (
            cooldown_s
            if cooldown_s is not None
            else cast(Optional[int], getattr(config, "TELEGRAM_COOLDOWN_SECONDS", None))
        )

        # 2) fallback на nested settings
        if (not _token or not _chat) or _cooldown_opt is None:
            settings = _load_settings_safe()
            if settings is not None:
                tg = getattr(settings, "telegram", None)
                if tg is not None:
                    if not _token:
                        _token = cast(Optional[str], getattr(tg, "bot_token", None))
                    if not _chat:
                        _chat = cast(Optional[str], getattr(tg, "alert_chat_id", None))
                if _cooldown_opt is None:
                    _cooldown_opt = cast(
                        Optional[int], getattr(settings, "alert_cooldown_sec", None)
                    )

        # 3) дефолт для cooldown
        cooldown_final: int = _cooldown_opt if _cooldown_opt is not None else 30

        # 4) конструктор відправника
        self._sender: TelegramSender = TelegramSender(
            token=_token or "",
            chat_id=_chat or "",
            cooldown_s=cooldown_final,
        )

    def send_text(self, text: str) -> bool:
        if not self.enabled:
            return False
        return self._sender.send(text)


def send_telegram(text: str, enabled: bool = True) -> bool:
    """
    Зручна функція-враппер для швидкої відправки повідомлення у Telegram.
    """
    if not enabled:
        return False
    notifier = TelegramNotifier(enabled=True)
    return notifier.send_text(text)
