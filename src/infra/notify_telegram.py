from typing import Optional

from src.infra import config
from src.telegram.sender import TelegramSender


class TelegramNotifier:
    """
    Невтручальний адаптер для відправки повідомлень у Telegram.
    Працює лише якщо задано TELEGRAM_BOT_TOKEN і TELEGRAM_CHAT_ID.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        cooldown_s: Optional[int] = None,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self._sender = TelegramSender(
            token=token or config.TELEGRAM_BOT_TOKEN,
            chat_id=chat_id or config.TELEGRAM_CHAT_ID,
            cooldown_s=cooldown_s if cooldown_s is not None else config.TELEGRAM_COOLDOWN_SECONDS,
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
