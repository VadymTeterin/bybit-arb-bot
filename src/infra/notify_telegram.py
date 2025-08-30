from __future__ import annotations

import os
from typing import Any, cast

try:
    from loguru import logger  # type: ignore
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)

# Local deps
from src.infra import config
from src.telegram.sender import TelegramSender


def _load_settings_safe() -> Any | None:
    """Try to load settings from config without pinning to a specific function name."""
    # We support either get_settings() or load_settings() depending on project stage.
    for fname in ("get_settings", "load_settings"):
        try:
            fn = cast(Any, getattr(config, fname, None))
            if fn:
                return fn()
        except Exception as e:  # pragma: no cover
            logger.warning("%s() failed: %s", fname, e)
    return None


def _env_get(*names: str) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


def _chat_label(settings: Any | None) -> str:
    """Resolve a short chat label/prefix.

    Priority:
      1) Explicit env vars: TELEGRAM__LABEL / TG_LABEL / ALERT_CHAT_LABEL
      2) Settings fields if present: settings.telegram.label / settings.label
      3) Derive from runtime env: dev -> "🧪 DEV", stage -> "🟨 STAGE", prod -> ""
    """
    v = _env_get("TELEGRAM__LABEL", "TG_LABEL", "ALERT_CHAT_LABEL")
    if v:
        return str(v).strip()

    # Settings-based label
    try:
        tg = getattr(settings, "telegram", None)
        if tg and getattr(tg, "label", None):
            return str(tg.label).strip()
        if getattr(settings, "label", None):
            return str(settings.label).strip()
    except Exception:
        pass

    # Derive from runtime.env
    try:
        env = str(getattr(getattr(settings, "runtime", object()), "env", "")).lower()
    except Exception:
        env = ""
    if env in ("dev", "development"):
        return "🧪 DEV"
    if env in ("stage", "staging", "preprod", "uat"):
        return "🟨 STAGE"
    return ""  # production by default


class TelegramNotifier:
    """Thin wrapper around TelegramSender that applies a label prefix if configured."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = bool(enabled)
        self._settings = _load_settings_safe()

        # Token
        token = None
        try:
            if self._settings is not None and getattr(self._settings, "telegram", None):
                token = getattr(self._settings.telegram, "bot_token", None) or getattr(
                    self._settings, "tg_bot_token", None
                )
            token = token or _env_get("TG_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
        except Exception:
            token = token or _env_get("TG_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")

        # Chat id
        chat_id = None
        try:
            if self._settings is not None and getattr(self._settings, "telegram", None):
                chat_id = getattr(self._settings.telegram, "chat_id", None) or getattr(
                    self._settings, "tg_chat_id", None
                )
            chat_id = chat_id or _env_get("TG_CHAT_ID", "TELEGRAM_CHAT_ID")
        except Exception:
            chat_id = chat_id or _env_get("TG_CHAT_ID", "TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            logger.warning("TelegramNotifier missing token/chat_id; disabled")
            self.enabled = False

        self._label = _chat_label(self._settings)
        self._sender = TelegramSender(token=str(token or ""), chat_id=str(chat_id or ""))

    def _apply_label(self, text: str) -> str:
        if not self._label:
            return text
        # avoid double-prefixing in case caller already added it
        if text.startswith(self._label):
            return text
        return f"{self._label} | {text}"

    def send_text(self, text: str) -> bool:
        if not self.enabled:
            return False
        return self._sender.send(self._apply_label(text))


def send_telegram(text: str, enabled: bool = True) -> bool:
    """Convenience wrapper for quick Telegram send with optional label prefix."""
    if not enabled:
        return False
    notifier = TelegramNotifier(enabled=True)
    return notifier.send_text(text)
