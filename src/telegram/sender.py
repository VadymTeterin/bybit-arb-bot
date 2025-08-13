import time
from typing import Optional

import httpx


class TelegramSender:
    """
    Простий відправник повідомлень у Telegram з локальним тротлінгом (cooldown).
    Очікує, що токен і chat_id будуть передані явно або зчитані в наступних оновленнях (config).
    """

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None, cooldown_s: int = 30):
        self.token = token
        self.chat_id = chat_id
        self.cooldown_s = cooldown_s
        self._last_sent_ts = 0.0

    def _throttled(self) -> bool:
        return (time.time() - self._last_sent_ts) < self.cooldown_s

    def send(self, text: str) -> bool:
        """
        Відправляє текст у Telegram. Повертає True при успіху, False  якщо не вдалося
        або якщо спрацював тротлінг/cooldown.
        """
        if not self.token or not self.chat_id:
            return False
        if self._throttled():
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
            self._last_sent_ts = time.time()
            return True
        except Exception:
            return False
