# scripts/ws_bot_runner.py
"""
Run WebSocket streaming and Telegram /status bot in a single asyncio process.
- WS handlers increment MetricsRegistry counters.
- Telegram /status reads the same MetricsRegistry (same process).

Run:
    python -m scripts.ws_bot_runner

Env:
    WS_ENABLED=1                          # to run WS (optional; defaults True in settings)
    TELEGRAM__BOT_TOKEN=<token>           # required to run Telegram bot
    TELEGRAM__ALERT_CHAT_ID=<chat_id>     # optional allowlisted chat (int)
    # Debug knobs (optional):
    WS_DEBUG_NORMALIZED=1
    WS_DEBUG_FILTER_CHANNELS=ticker
    WS_DEBUG_FILTER_SYMBOLS=BTCUSDT,ETHUSDT
    WS_DEBUG_SAMPLE_MS=1000
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.infra.logging import setup_logging
from src.main import load_settings  # reuse settings loader
from src.ws.health import MetricsRegistry


# --- Utils (mirrored locally to avoid importing internals) --------------------
def _csv_list(x: Any) -> List[str]:
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


def _nested_bybit(s):
    by = getattr(s, "bybit", None)
    url_linear = None
    url_spot = None
    topics_linear: List[str] = []
    topics_spot: List[str] = []

    if by is not None:
        url_linear = getattr(by, "ws_public_url_linear", None)
        url_spot = getattr(by, "ws_public_url_spot", None)
        topics_linear = _csv_list(getattr(by, "ws_sub_topics_linear", None))
        topics_spot = _csv_list(getattr(by, "ws_sub_topics_spot", None))

    url_linear = url_linear or getattr(s, "ws_public_url_linear", None)
    url_spot = url_spot or getattr(s, "ws_public_url_spot", None)
    topics_linear = topics_linear or _csv_list(
        getattr(s, "ws_topics_list_linear", None)
    )
    topics_spot = topics_spot or _csv_list(getattr(s, "ws_topics_list_spot", None))

    return {
        "url_linear": url_linear,
        "url_spot": url_spot,
        "topics_linear": topics_linear,
        "topics_spot": topics_spot,
    }


def _allowed_chat_id() -> Optional[int]:
    cid = os.getenv("TELEGRAM__ALERT_CHAT_ID") or os.getenv("TELEGRAM__CHAT_ID") or ""
    cid = cid.strip()
    try:
        return int(cid) if cid else None
    except Exception:
        return None


def _get_token() -> Optional[str]:
    tok = os.getenv("TELEGRAM__BOT_TOKEN") or os.getenv("TELEGRAM__TOKEN") or ""
    tok = tok.strip()
    return tok or None


# --- Main async runner --------------------------------------------------------
async def main() -> None:
    # logging (Path is required by setup_logging)
    setup_logging(log_dir=Path("./logs"), level=os.getenv("LOG_LEVEL", "INFO"))

    # settings
    s = load_settings()
    ws_cfg = _nested_bybit(s)
    ws_enabled = bool(getattr(s, "ws_enabled", True))
    metrics = MetricsRegistry.get()

    # optional WS debug knobs
    debug_norm = _env_bool("WS_DEBUG_NORMALIZED", False)
    debug_channels = set(_csv_list(os.getenv("WS_DEBUG_FILTER_CHANNELS", "ticker")))
    debug_symbols = set(_csv_list(os.getenv("WS_DEBUG_FILTER_SYMBOLS", "")))
    debug_sample_ms = _env_int("WS_DEBUG_SAMPLE_MS", 1000)
    _last_log: Dict[Tuple[str, str, str], float] = {}

    # Try imports of WS components
    try:
        from src.core.cache import QuoteCache
        from src.exchanges.bybit.ws import BybitWS, iter_ticker_entries
        from src.ws.bridge import publish_bybit_ticker
        from src.ws.multiplexer import WsEvent, WSMultiplexer
        from src.ws.normalizers.bybit_v5 import normalize
        from src.ws.subscribers.alerts_subscriber import AlertsSubscriber

        ws_available = True
    except Exception as e:  # noqa: BLE001
        logger.warning("WS components unavailable: {}", e)
        ws_available = False

    # Telegram bot (optional)
    token = _get_token()
    allow_chat = _allowed_chat_id()
    bot_available = token is not None
    if not bot_available:
        logger.warning("Telegram token is not set. /status bot will not run.")

    tasks: List[asyncio.Task] = []

    # --- WS setup (if available & enabled) ---
    if ws_available and ws_enabled:
        cache = QuoteCache()
        ws_linear = (
            BybitWS(ws_cfg["url_linear"], ws_cfg["topics_linear"] or ["tickers"])
            if ws_cfg["url_linear"]
            else None
        )
        ws_spot = (
            BybitWS(ws_cfg["url_spot"], ws_cfg["topics_spot"] or ["tickers"])
            if ws_cfg["url_spot"]
            else None
        )
        if not ws_linear and not ws_spot:
            logger.warning(
                "WS config has neither LINEAR nor SPOT endpoints/topics configured."
            )
        mux = WSMultiplexer(name="core")
        alerts_sub = AlertsSubscriber(mux)
        alerts_sub.start()

        def _debug_log_normalized(source: str, evt_norm: dict) -> None:
            if not debug_norm:
                return
            import time as _t  # local to avoid global import at module import

            channel = str(evt_norm.get("channel") or "")
            symbol = str(evt_norm.get("symbol") or "")
            if not channel or channel == "other":
                return
            if not symbol:
                return
            if debug_channels and channel not in debug_channels:
                return
            if debug_symbols and symbol not in debug_symbols:
                return
            data = evt_norm.get("data")
            items = (
                1
                if isinstance(data, dict)
                else (len(data) if isinstance(data, list) else 0)
            )
            key = (source, channel, symbol)
            now = _t.monotonic()
            last = _last_log.get(key, 0.0)
            if (now - last) * 1000.0 < max(0, debug_sample_ms):
                return
            _last_log[key] = now
            logger.bind(tag="WS").debug(
                f"{source} normalized: channel={channel} symbol={symbol} items={items}"
            )

        async def on_message_spot(msg: dict):
            # Publish normalized event + increment metrics
            try:
                evt_norm = normalize(msg)
                _debug_log_normalized("SPOT", evt_norm)
                mux.publish(
                    WsEvent(
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

            # Compatibility path
            for item in iter_ticker_entries(msg):
                sym = item.get("symbol")
                last = item.get("last")
                if sym and last is not None:
                    _ = await cache.update(sym, spot=last)
                    publish_bybit_ticker(mux, "SPOT", item)

        async def on_message_linear(msg: dict):
            # Publish normalized event + increment metrics
            try:
                evt_norm = normalize(msg)
                _debug_log_normalized("LINEAR", evt_norm)
                mux.publish(
                    WsEvent(
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

            # Compatibility path
            for item in iter_ticker_entries(msg):
                sym = item.get("symbol")
                mark = item.get("mark")
                if sym and mark is not None:
                    _ = await cache.update(sym, linear_mark=mark)
                    publish_bybit_ticker(mux, "LINEAR", item)

        async def refresh_meta_task():
            from src.exchanges.bybit.rest import BybitRest

            client = BybitRest()
            while True:
                try:
                    spot_rows = client.get_tickers("spot") or []
                    lin_rows = client.get_tickers("linear") or []

                    def _vol_map(rows: List[Dict[str, Any]]) -> Dict[str, float]:
                        m: Dict[str, float] = {}
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
                    await cache.update_vol24h_bulk(combined)
                    logger.bind(tag="RTMETA").info(
                        f"Refreshed vol24h for {len(combined)} symbols"
                    )
                except Exception as e:
                    logger.bind(tag="RTMETA").warning(f"Meta refresh failed: {e!r}")
                await asyncio.sleep(max(30, int(getattr(s, "rt_meta_refresh_sec", 30))))

        # Schedule WS tasks
        if ws_spot:
            tasks.append(
                asyncio.create_task(ws_spot.run(on_message_spot), name="ws_spot")
            )
        if ws_linear:
            tasks.append(
                asyncio.create_task(ws_linear.run(on_message_linear), name="ws_linear")
            )
        tasks.append(asyncio.create_task(refresh_meta_task(), name="rt_meta"))

    # --- Telegram bot setup (if token provided) ---
    if bot_available:
        try:
            # aiogram v3 imports
            from aiogram import Bot, Dispatcher
            from aiogram.filters import Command
            from aiogram.types import Message
        except Exception as e:  # noqa: BLE001
            logger.error("aiogram is not available: {}", e)
        else:
            bot = Bot(token=token, parse_mode="Markdown")
            dp = Dispatcher()

            @dp.message(Command("start"))
            async def start_handler(msg: Message):
                if allow_chat is not None and msg.chat.id != allow_chat:
                    await msg.answer("Access denied: this chat is not allowlisted.")
                    return
                text = (
                    "Hi! I'm the WS status bot running in the *same process* as the WS stream.\n"
                    "Commands:\n"
                    "• /status — show current WS metrics (uptime & counters)\n"
                )
                await msg.answer(text)

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

            tasks.append(asyncio.create_task(dp.start_polling(bot), name="tg_polling"))

    if not tasks:
        logger.error(
            "Nothing to run: WS disabled/unavailable and no Telegram token provided."
        )
        return

    logger.success("Runner started: {} task(s). Ctrl+C to stop.", len(tasks))
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Cancelled.")
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:  # noqa: BLE001
        logger.exception("Runner failed: {}", e)
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
