from __future__ import annotations

import requests


def send_telegram_message(
    token: str,
    chat_id: str | int,
    text: str,
    parse_mode: str | None = None,
) -> dict:
    """
    Надсилає повідомлення у Telegram без aiogram (через Bot API).
    - token: токен бота (TELEGRAM_BOT_TOKEN)
    - chat_id: ID або @channelusername (рекомендовано числовий ID)
    - text: тіло повідомлення
    - parse_mode: "Markdown" | "MarkdownV2" | "HTML" | None
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data: dict[str, str] = {
        "chat_id": str(chat_id),
        "text": text,
        "disable_web_page_preview": "true",
    }
    if parse_mode:
        data["parse_mode"] = parse_mode

    r = requests.post(url, data=data, timeout=15)
    r.raise_for_status()
    return r.json()
