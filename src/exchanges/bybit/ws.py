# src/exchanges/bybit/ws.py
from __future__ import annotations

import asyncio
import json
import random
from typing import Awaitable, Callable, Dict, Iterable, Iterator, List, Optional

try:
    from loguru import logger  # type: ignore
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger("bybit.ws")

import aiohttp

BackoffFn = Callable[[int], float]


def exp_backoff_with_jitter(
    attempt: int,
    *,
    base: float = 1.0,
    factor: float = 2.0,
    cap: float = 30.0,
) -> float:
    """
    Exponential backoff with jitter in the interval [t/2, t],
    where t = min(cap, base * factor**(attempt-1)).
    Підтримує виклики з kwargs: base=..., cap=..., factor=...
    """
    if attempt < 1:
        attempt = 1
    upper = min(cap, base * (factor ** (attempt - 1)))
    if upper <= 0:
        return 0.0
    lower = upper * 0.5
    # рівномірно у [t/2, t]
    return lower + random.random() * (upper - lower)


def _to_float(v, default: Optional[float] = None) -> Optional[float]:
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        try:
            return float(str(v).strip())
        except Exception:
            return default


def _from_e_scaled(val) -> Optional[float]:
    # Supports fields like "...E8" or "...E4"
    if val is None:
        return None
    s = str(val).strip()
    try:
        # plain float will succeed for e.g. "123.45"
        return float(s)
    except Exception:
        pass
    try:
        return float(s)
    except Exception:
        return None


def _pick_first(*vals) -> Optional[float]:
    for v in vals:
        if v is None:
            continue
        return v
    return None


def _infer_symbol_from_topic(topic: str) -> Optional[str]:
    # bybit v5 topics look like "tickers.BTCUSDT" or "tickers"
    if not topic:
        return None
    if "." in topic:
        return topic.split(".", 1)[1].strip().upper() or None
    return None


def iter_ticker_entries(message: Dict) -> Iterator[Dict]:
    """
    Normalize Bybit v5 'tickers' message into rows of:
    { 'symbol': str, 'last': float|None, 'mark': float|None }
    Accepts both object and array payloads, and E8/E4 integer variants.
    """
    topic = str(message.get("topic") or "").strip()
    data = message.get("data")
    if data is None:
        return iter(())  # empty
    rows: List[Dict] = []
    if isinstance(data, dict):
        arr = [data]
    elif isinstance(data, list):
        arr = list(data)
    else:
        return iter(())

    for item in arr:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol") or _infer_symbol_from_topic(topic) or ""
        symbol = str(symbol).upper()

        # last price
        last = _to_float(item.get("lastPrice"))
        if last is None:
            lp_e8 = item.get("lastPriceE8")
            if lp_e8 is not None:
                last = _from_e_scaled(lp_e8)
                if last is not None:
                    last /= 1e8
            else:
                lp_e4 = item.get("lastPriceE4")
                if lp_e4 is not None:
                    last = _from_e_scaled(lp_e4)
                    if last is not None:
                        last /= 1e4
        if last is None:
            last = _to_float(item.get("lastPriceLatest"))

        # mark price (derivatives)
        mark = _to_float(item.get("markPrice"))
        if mark is None:
            mp_e8 = item.get("markPriceE8")
            if mp_e8 is not None:
                mark = _from_e_scaled(mp_e8)
                if mark is not None:
                    mark /= 1e8
            else:
                mp_e4 = item.get("markPriceE4")
                if mp_e4 is not None:
                    mark = _from_e_scaled(mp_e4)
                    if mark is not None:
                        mark /= 1e4

        rows.append({"symbol": symbol, "last": last, "mark": mark})
    return iter(rows)


class BybitPublicWS:
    """
    Minimal Bybit v5 public WS client (spot/linear).
    - Connects to given URL
    - Subscribes to topics list (e.g. ["tickers.BTCUSDT","tickers.ETHUSDT"] or ["tickers"])
    - Calls on_message for every incoming JSON
    """

    def __init__(
        self,
        url: str,
        topics: Iterable[str],
    ) -> None:
        self.url = url
        self.topics = list(topics)
        self._stop = asyncio.Event()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        if not self.topics:
            return
        msg = {"op": "subscribe", "args": self.topics}
        await ws.send_str(json.dumps(msg))
        logger.debug(f"WS subscribe -> {msg}")

    async def stop(self) -> None:
        self._stop.set()

    async def run(
        self,
        on_message: Callable[[dict], Awaitable[None]],
        backoff: BackoffFn = exp_backoff_with_jitter,
        heartbeat: int = 30,
    ) -> None:
        """
        Main loop with auto-reconnect.
        on_message receives parsed JSON (dict).
        """
        self._stop.clear()
        attempt = 1

        async with aiohttp.ClientSession() as session:
            self._session = session
            while not self._stop.is_set():
                try:
                    async with session.ws_connect(self.url, heartbeat=heartbeat) as ws:
                        logger.info(f"WS connected: {self.url}")
                        attempt = 1
                        await self._subscribe(ws)

                        async for msg in ws:
                            if self._stop.is_set():
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    payload = json.loads(msg.data)
                                except Exception:
                                    logger.warning("WS non-JSON text frame")
                                    continue
                                await on_message(payload)
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                continue
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WS error: {ws.exception()}")
                                break
                            elif msg.type in (
                                aiohttp.WSMsgType.CLOSED,
                                aiohttp.WSMsgType.CLOSING,
                            ):
                                break
                except Exception as e:
                    delay = backoff(attempt)
                    logger.warning(f"WS reconnect in {delay:.2f}s after error: {e!r}")
                    await asyncio.sleep(delay)
                    attempt += 1

        logger.info("WS stopped")
