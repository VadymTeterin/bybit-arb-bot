# scripts/ws_bot_supervisor.py
"""
Supervised runner: WS stream(s) + Telegram /status bot with auto-restart (exponential backoff).
Loads .env on start to populate environment variables.

Run:
    python -m scripts.ws_bot_supervisor
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv  # NEW
from loguru import logger

from src.infra.logging import setup_logging
from src.main import load_settings
from src.ws.backoff import ExponentialBackoff
from src.ws.health import MetricsRegistry

# Load .env once (non-fatal if missing)
load_dotenv(override=False)


def _csv_list(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(t).strip() for t in x if str(t).strip()]
    if isinstance(x, str):
        return [t.strip() for t in x.split(",") if t.strip()]
    return []


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default))))
    except Exception:
        return default


def _allowed_chat_id() -> int | None:
    cid = os.getenv("TELEGRAM__ALERT_CHAT_ID") or os.getenv("TELEGRAM__CHAT_ID") or ""
    cid = cid.strip()
    try:
        return int(cid) if cid else None
    except Exception:
        return None


def _get_token() -> str | None:
    tok = os.getenv("TELEGRAM__BOT_TOKEN") or os.getenv("TELEGRAM__TOKEN") or ""
    tok = tok.strip()
    return tok or None


def _nested_bybit(s):
    by = getattr(s, "bybit", None)
    url_linear = None
    url_spot = None
    topics_linear: list[str] = []
    topics_spot: list[str] = []
    if by is not None:
        url_linear = getattr(by, "ws_public_url_linear", None)
        url_spot = getattr(by, "ws_public_url_spot", None)
        topics_linear = _csv_list(getattr(by, "ws_sub_topics_linear", None))
        topics_spot = _csv_list(getattr(by, "ws_sub_topics_spot", None))
    url_linear = url_linear or getattr(s, "ws_public_url_linear", None)
    url_spot = url_spot or getattr(s, "ws_public_url_spot", None)
    topics_linear = topics_linear or _csv_list(getattr(s, "ws_topics_list_linear", None))
    topics_spot = topics_spot or _csv_list(getattr(s, "ws_topics_list_spot", None))
    return {
        "url_linear": url_linear,
        "url_spot": url_spot,
        "topics_linear": topics_linear,
        "topics_spot": topics_spot,
    }


async def ws_spot_loop(ws_url: str, topics: list[str], shared, metrics, debug):
    bo = ExponentialBackoff(base=1.0, factor=2.0, cap=30.0)
    while True:
        try:
            from src.exchanges.bybit.ws import BybitWS

            ws = BybitWS(ws_url, topics or ["tickers"])

            def _dbg(evt_norm: dict):
                if not debug["enabled"]:
                    return
                channel = str(evt_norm.get("channel") or "")
                symbol = str(evt_norm.get("symbol") or "")
                if not channel or channel == "other" or not symbol:
                    return
                if debug["channels"] and channel not in debug["channels"]:
                    return
                if debug["symbols"] and symbol not in debug["symbols"]:
                    return
                data = evt_norm.get("data")
                items = (
                    1 if isinstance(data, dict) else (len(data) if isinstance(data, list) else 0)
                )
                key = ("SPOT", channel, symbol)
                now = time.monotonic()
                last = debug["last"].get(key, 0.0)
                if (now - last) * 1000.0 < max(0, debug["sample_ms"]):
                    return
                debug["last"][key] = now
                logger.bind(tag="WS").debug(
                    f"SPOT normalized: channel={channel} symbol={symbol} items={items}"
                )

            async def on_message_spot(msg: dict):
                try:
                    evt_norm = shared["normalize"](msg)
                    _dbg(evt_norm)
                    shared["mux"].publish(
                        shared["WsEvent"](
                            source="SPOT",
                            channel=str(evt_norm.get("channel") or "other"),
                            symbol=str(evt_norm.get("symbol") or ""),
                            payload=evt_norm.get("data") or {},
                            ts=evt_norm.get("ts_ms") or 0,
                        )
                    )
                    metrics.inc_spot()
                except Exception as e:
                    logger.debug(f"normalize(msg) failed (SPOT): {e!r}")
                for item in shared["iter_ticker_entries"](msg):
                    sym = item.get("symbol")
                    last = item.get("last")
                    if sym and last is not None:
                        _ = await shared["cache"].update(sym, spot=last)
                        shared["publish_bybit_ticker"](shared["mux"], "SPOT", item)

            logger.info("SPOT loop: connecting to {}", ws_url)
            bo.reset()
            await ws.run(on_message_spot)
            logger.warning("SPOT loop ended without exception (socket closed). Reconnecting...")
        except Exception as e:
            delay = bo.next_delay()
            logger.exception("SPOT loop crashed: {}. Reconnect in {:.1f}s", e, delay)
            await asyncio.sleep(delay)


async def ws_linear_loop(ws_url: str, topics: list[str], shared, metrics, debug):
    bo = ExponentialBackoff(base=1.0, factor=2.0, cap=30.0)
    while True:
        try:
            from src.exchanges.bybit.ws import BybitWS

            ws = BybitWS(ws_url, topics or ["tickers"])

            def _dbg(evt_norm: dict):
                if not debug["enabled"]:
                    return
                channel = str(evt_norm.get("channel") or "")
                symbol = str(evt_norm.get("symbol") or "")
                if not channel or channel == "other" or not symbol:
                    return
                if debug["channels"] and channel not in debug["channels"]:
                    return
                if debug["symbols"] and symbol not in debug["symbols"]:
                    return
                data = evt_norm.get("data")
                items = (
                    1 if isinstance(data, dict) else (len(data) if isinstance(data, list) else 0)
                )
                key = ("LINEAR", channel, symbol)
                now = time.monotonic()
                last = debug["last"].get(key, 0.0)
                if (now - last) * 1000.0 < max(0, debug["sample_ms"]):
                    return
                debug["last"][key] = now
                logger.bind(tag="WS").debug(
                    f"LINEAR normalized: channel={channel} symbol={symbol} items={items}"
                )

            async def on_message_linear(msg: dict):
                try:
                    evt_norm = shared["normalize"](msg)
                    _dbg(evt_norm)
                    shared["mux"].publish(
                        shared["WsEvent"](
                            source="LINEAR",
                            channel=str(evt_norm.get("channel") or "other"),
                            symbol=str(evt_norm.get("symbol") or ""),
                            payload=evt_norm.get("data") or {},
                            ts=evt_norm.get("ts_ms") or 0,
                        )
                    )
                    metrics.inc_linear()
                except Exception as e:
                    logger.debug(f"normalize(msg) failed (LINEAR): {e!r}")
                for item in shared["iter_ticker_entries"](msg):
                    sym = item.get("symbol")
                    mark = item.get("mark")
                    if sym and mark is not None:
                        _ = await shared["cache"].update(sym, linear_mark=mark)
                        shared["publish_bybit_ticker"](shared["mux"], "LINEAR", item)

            logger.info("LINEAR loop: connecting to {}", ws_url)
            bo.reset()
            await ws.run(on_message_linear)
            logger.warning("LINEAR loop ended without exception (socket closed). Reconnecting...")
        except Exception as e:
            delay = bo.next_delay()
            logger.exception("LINEAR loop crashed: {}. Reconnect in {:.1f}s", e, delay)
            await asyncio.sleep(delay)


async def meta_refresh_loop(shared, refresh_sec: int):
    bo = ExponentialBackoff(base=1.0, factor=2.0, cap=30.0)
    while True:
        try:
            from src.exchanges.bybit.rest import BybitRest

            client = BybitRest()
            while True:
                try:
                    spot_rows = client.get_tickers("spot") or []
                    lin_rows = client.get_tickers("linear") or []

                    def _vol_map(rows: list[dict[str, Any]]) -> dict[str, float]:
                        m: dict[str, float] = {}
                        for r in rows:
                            sym = r.get("symbol")
                            if not sym:
                                continue
                            v = r.get("turnover24h") or r.get("turnoverUsd")
                            try:
                                m[sym] = float(v) if v is not None else 0.0
                            except Exception:
                                m[sym] = 0.0
                        return m

                    spot_vol = _vol_map(spot_rows)
                    lin_vol = _vol_map(lin_rows)
                    combined = {
                        sym: min(spot_vol[sym], lin_vol[sym])
                        for sym in (set(spot_vol) & set(lin_vol))
                    }
                    await shared["cache"].update_vol24h_bulk(combined)
                    logger.bind(tag="RTMETA").info(f"Refreshed vol24h for {len(combined)} symbols")
                except Exception as e:
                    logger.bind(tag="RTMETA").warning(f"Meta refresh failed: {e!r}")
                await asyncio.sleep(max(30, int(refresh_sec)))
        except Exception as e:
            delay = bo.next_delay()
            logger.exception("Meta loop crashed: {}. Restart in {:.1f}s", e, delay)
            await asyncio.sleep(delay)


async def bot_polling_loop(metrics, allow_chat: int | None):
    bo = ExponentialBackoff(base=1.0, factor=2.0, cap=30.0)
    token = _get_token()
    if not token:
        logger.warning("Telegram token is not set. /status bot will not run.")
        return

    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.filters import Command
    from aiogram.types import Message

    while True:
        try:
            bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
            dp = Dispatcher()

            @dp.message(Command("start"))
            async def start_handler(msg: Message):
                if allow_chat is not None and msg.chat.id != allow_chat:
                    await msg.answer("Access denied: this chat is not allowlisted.")
                    return
                await msg.answer(
                    "Hi! I'm the WS status bot running in the *same process* as the supervised WS stream.\n"
                    "Commands:\n"
                    "• /status — show current WS metrics (uptime & counters)\n"
                )

            @dp.message(Command("status"))
            async def status_handler(msg: Message):
                if allow_chat is not None and msg.chat.id != allow_chat:
                    await msg.answer("Access denied: this chat is not allowlisted.")
                    return
                m = metrics.snapshot()
                lines = [
                    "🔎 *WS Status*",
                    f"• Uptime: `{m['uptime_ms']} ms`",
                    f"• Counters: `spot={m['counters']['spot']}`, `linear={m['counters']['linear']}`",
                    f"• Last Event (UTC): `{m['last_event_at_utc'] or 'n/a'}`",
                    f"• Last Spot (UTC): `{m['last_spot_at_utc'] or 'n/a'}`",
                    f"• Last Linear (UTC): `{m['last_linear_at_utc'] or 'n/a'}`",
                ]
                await msg.answer("\n".join(lines))

            bo.reset()
            logger.info("Telegram bot polling: start")
            await dp.start_polling(bot)
            logger.warning("Telegram bot polling stopped without exception. Restarting...")
        except Exception as e:
            delay = bo.next_delay()
            logger.exception("Telegram bot loop crashed: {}. Restart in {:.1f}s", e, delay)
            await asyncio.sleep(delay)


async def main() -> None:
    setup_logging(log_dir=Path("./logs"), level=os.getenv("LOG_LEVEL", "INFO"))

    s = load_settings()
    ws_cfg = _nested_bybit(s)
    ws_enabled = bool(getattr(s, "ws_enabled", True))
    allow_chat = _allowed_chat_id()

    from src.core.cache import QuoteCache
    from src.exchanges.bybit.ws import iter_ticker_entries
    from src.ws.bridge import publish_bybit_ticker
    from src.ws.multiplexer import WsEvent, WSMultiplexer
    from src.ws.normalizers.bybit_v5 import normalize
    from src.ws.subscribers.alerts_subscriber import AlertsSubscriber

    cache = QuoteCache()
    mux = WSMultiplexer(name="core")
    alerts_sub = AlertsSubscriber(mux)
    alerts_sub.start()

    metrics = MetricsRegistry.get()

    debug = {
        "enabled": _env_bool("WS_DEBUG_NORMALIZED", False),
        "channels": set(_csv_list(os.getenv("WS_DEBUG_FILTER_CHANNELS", "ticker"))),
        "symbols": set(_csv_list(os.getenv("WS_DEBUG_FILTER_SYMBOLS", ""))),
        "sample_ms": _env_int("WS_DEBUG_SAMPLE_MS", 1000),
        "last": {},  # type: ignore[var-annotated]
    }

    shared = {
        "cache": cache,
        "mux": mux,
        "WsEvent": WsEvent,
        "publish_bybit_ticker": publish_bybit_ticker,
        "normalize": normalize,
        "iter_ticker_entries": iter_ticker_entries,
    }

    tasks: list[asyncio.Task] = []

    if ws_enabled:
        if ws_cfg["url_spot"]:
            tasks.append(
                asyncio.create_task(
                    ws_spot_loop(
                        ws_cfg["url_spot"],
                        ws_cfg["topics_spot"],
                        shared,
                        metrics,
                        debug,
                    ),
                    name="ws_spot_loop",
                )
            )
        if ws_cfg["url_linear"]:
            tasks.append(
                asyncio.create_task(
                    ws_linear_loop(
                        ws_cfg["url_linear"],
                        ws_cfg["topics_linear"],
                        shared,
                        metrics,
                        debug,
                    ),
                    name="ws_linear_loop",
                )
            )
        tasks.append(
            asyncio.create_task(
                meta_refresh_loop(shared, refresh_sec=int(getattr(s, "rt_meta_refresh_sec", 30))),
                name="meta_refresh_loop",
            )
        )

    if _get_token():
        tasks.append(asyncio.create_task(bot_polling_loop(metrics, allow_chat), name="tg_polling"))

    if not tasks:
        logger.error("Nothing to run: WS disabled/unavailable and no Telegram token provided.")
        return

    logger.success("Supervisor started: {} task(s). Ctrl+C to stop.", len(tasks))
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error("Task finished with exception (already supervised): {}", r)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
