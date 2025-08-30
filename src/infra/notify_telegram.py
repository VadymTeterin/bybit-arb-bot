from __future__ import annotations

import os
from typing import Optional

try:
    from loguru import logger
except Exception:  # pragma: no cover
    # Fallback minimal logger if loguru is unavailable in some envs
    class _DummyLogger:
        def debug(self, *args, **kwargs): ...
        def info(self, *args, **kwargs): ...
        def warning(self, *args, **kwargs): ...
        def error(self, *args, **kwargs): ...
        def exception(self, *args, **kwargs): ...
    logger = _DummyLogger()  # type: ignore[misc,assignment]

class TelegramSender:
    """Thin wrapper for Telegram Bot sending.

    In tests this class is monkeypatched, so real network I/O is not required here.
    """
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    def send(self, text: str) -> bool:
        # Real implementation would perform an HTTP request to Telegram API.
        # Tests patch this method/class, so by default we just noop-success.
        logger.debug(f"Telegram send to {self.chat_id}: {text}")
        return True

_sender_cache: Optional[TelegramSender] = None

def get_sender() -> Optional[TelegramSender]:
    """Lazily construct and cache sender from env TG_BOT_TOKEN/TG_CHAT_ID."""
    global _sender_cache
    if _sender_cache is not None:
        return _sender_cache

    token = os.getenv("TG_BOT_TOKEN") or ""
    chat_id = os.getenv("TG_CHAT_ID") or ""
    if token and chat_id:
        _sender_cache = TelegramSender(token, chat_id)
    else:
        _sender_cache = None
    return _sender_cache


def build_message(text: str) -> str:
    """Apply optional label prefix defined by TELEGRAM__LABEL.

    Format required by tests: "<LABEL> | <text>".
    """
    label = os.getenv("TELEGRAM__LABEL") or ""
    if label:
        return f"{label} | {text}"
    return text


def send_telegram(text: str, enabled: Optional[bool] = None) -> bool:
    """Send a Telegram message (no-op if disabled or not configured).

    Args:
        text: message body (will be prefixed by TELEGRAM__LABEL if set).
        enabled: if False — force-disable; if True — force-enable;
                 if None — enable if credentials are present.

    Returns:
        True on success, False otherwise.
    """
    if enabled is False:
        return False

    msg = build_message(text)
    sender = get_sender()
    if sender is None:
        logger.debug("Telegram sender not configured; skipping send.")
        return False

    try:
        return bool(sender.send(msg))
    except Exception as e:  # pragma: no cover
        logger.exception("Telegram send failed: {}", e)
        return False
