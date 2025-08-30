"""
Telegram notification helper with minimal dependencies and mypy-friendly types.
The test suite monkeypatches `TelegramSender`, so keep the class name and signature stable.
"""
from __future__ import annotations

from typing import Optional
import logging
import os

logger: logging.Logger = logging.getLogger(__name__)


class TelegramSender:
    """Thin wrapper; in tests it is monkeypatched with a fake sender."""

    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    def send(self, text: str) -> bool:  # pragma: no cover - network-disabled in CI
        # Intentionally no real network IO in library code.
        # The real implementation lives in src/telegram/sender.py.
        logger.info("TelegramSender.send called (stub): %s", text)
        return True


def _label_prefix() -> str:
    """Build the label prefix according to QA expectations: 'LABEL | ' (if set)."""
    label: Optional[str] = os.getenv("TELEGRAM__LABEL")
    if label:
        return f"{label} | "
    return ""


def send_telegram(text: str, *, enabled: bool = True) -> bool:
    """
    Send a Telegram message with optional '[LABEL | ]' prefix.

    Returns True if a send was attempted and reported success by the sender.
    Returns False if disabled or configuration is incomplete.
    """
    if not enabled:
        return False

    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    if not token or not chat_id:
        logger.debug("send_telegram: missing TG_BOT_TOKEN or TG_CHAT_ID; skip send")
        return False

    payload = f"{_label_prefix()}{text}"
    sender = TelegramSender(token, chat_id)
    return sender.send(payload)
