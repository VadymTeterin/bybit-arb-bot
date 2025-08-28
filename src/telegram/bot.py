# src/telegram/bot.py
"""
Minimal aiogram bot with /start and /status.
Reads MetricsRegistry from the running process to display WS uptime and counters.

Run:
    python -m src.telegram.bot

Env:
    TELEGRAM__BOT_TOKEN or TELEGRAM__TOKEN  - required
    TELEGRAM__ALERT_CHAT_ID or TELEGRAM__CHAT_ID - optional allowlist (single chat)

Comments: English-only (per project rules)
"""

from __future__ import annotations

import asyncio
import os

try:
    # aiogram v3 style imports
    from aiogram import Bot, Dispatcher
    from aiogram.filters import Command
    from aiogram.types import Message
except Exception as e:  # noqa: BLE001
    raise RuntimeError(
        "aiogram not available or incompatible. Ensure aiogram v3 is installed."
    ) from e

from ..ws.health import MetricsRegistry


def _get_token() -> str:
    token = os.getenv("TELEGRAM__BOT_TOKEN") or os.getenv("TELEGRAM__TOKEN") or ""
    token = token.strip()
    if not token:
        raise RuntimeError("Telegram token is not set. Provide TELEGRAM__BOT_TOKEN in .env")
    return token


def _allowed_chat_id() -> int | None:
    cid = os.getenv("TELEGRAM__ALERT_CHAT_ID") or os.getenv("TELEGRAM__CHAT_ID") or ""
    cid = cid.strip()
    try:
        return int(cid) if cid else None
    except Exception:
        return None


def _format_status() -> str:
    m = MetricsRegistry.get().snapshot()
    # Compact human-readable format
    lines = [
        "🔎 *WS Status*",
        f"• Uptime: `{m['uptime_ms']} ms`",
        f"• Counters: `spot={m['counters']['spot']}`, `linear={m['counters']['linear']}`",
        f"• Last Event (UTC): `{m['last_event_at_utc'] or 'n/a'}`",
        f"• Last Spot (UTC): `{m['last_spot_at_utc'] or 'n/a'}`",
        f"• Last Linear (UTC): `{m['last_linear_at_utc'] or 'n/a'}`",
    ]
    return "\n".join(lines)


async def main() -> None:
    token = _get_token()
    allow_chat = _allowed_chat_id()

    bot = Bot(token=token, parse_mode="Markdown")
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start_handler(msg: Message):
        if allow_chat is not None and msg.chat.id != allow_chat:
            await msg.answer("Access denied: this chat is not allowlisted.")
            return
        text = (
            "Hi! I'm the WS status bot.\n"
            "Commands:\n"
            "• /status — show current WS metrics (uptime & counters)\n"
        )
        await msg.answer(text)

    @dp.message(Command("status"))
    async def status_handler(msg: Message):
        if allow_chat is not None and msg.chat.id != allow_chat:
            await msg.answer("Access denied: this chat is not allowlisted.")
            return
        await msg.answer(_format_status())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
