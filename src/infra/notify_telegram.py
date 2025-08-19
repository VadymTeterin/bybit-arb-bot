from typing import Optional

from src.infra import config
from src.telegram.sender import TelegramSender

# Fallback на Pydantic Settings, якщо плоскі змінні порожні
try:
    from src.infra.config import load_settings  # читає .env через pydantic Settings
except Exception:  # noqa: BLE001
    load_settings = None  # type: ignore


class TelegramNotifier:
    """
    Невтручальний адаптер для відправки повідомлень у Telegram.
    Працює якщо є токен і chat_id: з плоских ключів або з AppSettings().telegram.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        cooldown_s: Optional[int] = None,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled

        # 1) спроба взяти з аргументів або плоских ключів (os.getenv -> config.*)
        _token = token or config.TELEGRAM_BOT_TOKEN
        _chat = chat_id or config.TELEGRAM_CHAT_ID
        _cooldown = (
            cooldown_s if cooldown_s is not None else config.TELEGRAM_COOLDOWN_SECONDS
        )

        # 2) якщо щось відсутнє — fallback на nested (.env -> AppSettings().telegram)
        if (not _token or not _chat) and load_settings:
            try:
                s = load_settings()
                if not _token:
                    _token = getattr(s.telegram, "bot_token", "")  # TELEGRAM__BOT_TOKEN
                if not _chat:
                    _chat = getattr(
                        s.telegram, "alert_chat_id", ""
                    )  # TELEGRAM__ALERT_CHAT_ID
                if cooldown_s is None:
                    _cooldown = getattr(s, "alert_cooldown_sec", _cooldown)
            except Exception:
                pass

        self._sender = TelegramSender(
            token=_token,
            chat_id=_chat,
            cooldown_s=_cooldown,
        )

    def send_text(self, text: str) -> bool:
        if not self.enabled:
            return False
        return self._sender.send(text)


# Зручна функція-враппер
def send_telegram(text: str, enabled: bool = True) -> bool:
    if not enabled:
        return False
    notifier = TelegramNotifier(enabled=True)
    return notifier.send_text(text)
