# src/exchanges/bybit/ws.py
from __future__ import annotations

import asyncio
import json
import random
from typing import Awaitable, Callable, Dict, Iterable, Iterator, List, Optional

import aiohttp
from loguru import logger

BackoffFn = Callable[[int], float]


def exp_backoff_with_jitter(
    attempt: int, *, base: float = 1.0, cap: float = 30.0
) -> float:
    """
    Експоненціальний backoff з легким jitter.
    attempt: 1,2,3,... -> ~1,2,4,8,... (обмежено cap)
    Повертає затримку у секундах.
    """
    if attempt < 1:
        attempt = 1
    delay = min(cap, base * (2 ** (attempt - 1)))
    # jitter у [delay/2, delay] -> щоб уникати "thundering herd"
    jitter = delay * (0.5 * random.random())
    return delay - jitter


class BybitWS:
    """
    Полегшений клієнт Bybit v5 (public WS).
    Очікує topics типу: "tickers" або "tickers.BTCUSDT".
    """

    def __init__(self, url: str, topics: Iterable[str]) -> None:
        self.url = url
        self.topics = list(topics)
        self._stop = asyncio.Event()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        if not self.topics:
            logger.bind(tag="WS").warning("No topics provided; skipping subscribe")
            return
        payload = {"op": "subscribe", "args": self.topics}
        await ws.send_str(json.dumps(payload))
        logger.bind(tag="WS").info(f"Subscribed to {len(self.topics)} topic(s)")

    async def run(
        self,
        on_message: Callable[[dict], Awaitable[None]],
        backoff: BackoffFn = exp_backoff_with_jitter,
        heartbeat: int = 30,
    ) -> None:
        """
        Головний цикл з автоперепідключенням.
        on_message отримує розпарсений JSON (dict).
        """
        self._stop.clear()
        attempt = 1

        async with aiohttp.ClientSession() as session:
            self._session = session
            while not self._stop.is_set():
                try:
                    logger.bind(tag="WS").info(f"Connecting to {self.url}")
                    async with session.ws_connect(self.url, heartbeat=heartbeat) as ws:
                        attempt = 1  # успіх — скидаємо лічильник
                        await self._subscribe(ws)

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    data = json.loads(msg.data)
                                except Exception:
                                    logger.bind(tag="WS").warning(
                                        "Non‑JSON message skipped"
                                    )
                                    continue
                                await on_message(data)
                            elif msg.type in (
                                aiohttp.WSMsgType.CLOSED,
                                aiohttp.WSMsgType.ERROR,
                            ):
                                raise ConnectionError("WebSocket closed or error state")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    delay = backoff(attempt)
                    logger.bind(tag="RECONNECT").warning(
                        f"WS error: {e!r}. Reconnect in {delay:.1f}s (attempt {attempt})"
                    )
                    attempt += 1
                    try:
                        await asyncio.wait_for(self._stop.wait(), timeout=delay)
                    except asyncio.TimeoutError:
                        # минув таймаут — пробуємо знову
                        pass

    async def stop(self) -> None:
        self._stop.set()
        if self._session and not self._session.closed:
            await self._session.close()


# ---------------------------
#   УТИЛІТИ ПАРСИНГУ TICKERS
# ---------------------------


def _to_float(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _scale_from_key(key: str) -> float:
    # ..E4 -> 1e-4, ..E8 -> 1e-8
    k = key.lower()
    if k.endswith("e4"):
        return 1e-4
    if k.endswith("e8"):
        return 1e-8
    return 1.0


def _extract_first_number(obj: Dict, keys: List[str]) -> Optional[float]:
    """
    Повертає перше знайдене числове значення за списком ключів.
    Підтримує *_E4/*_E8 (ділення на 1e4/1e8).
    """
    for k in keys:
        if k in obj and obj[k] is not None:
            val = obj[k]
            scale = _scale_from_key(k)
            f = _to_float(val)
            if f is not None:
                return f * scale
    return None


def _symbol_from_topic(topic: str) -> Optional[str]:
    # "tickers.BTCUSDT" -> "BTCUSDT"
    if not topic:
        return None
    parts = topic.split(".")
    return parts[-1] if len(parts) > 1 else None


def iter_ticker_entries(msg: Dict) -> Iterator[Dict[str, Optional[float]]]:
    """
    Генерує елементи виду {"symbol": str, "last": float|None, "mark": float|None}
    з повідомлення Bybit v5 для теми tickers.* (spot/linear).
    """
    if not isinstance(msg, dict):
        return
    topic = msg.get("topic", "") or ""
    data = msg.get("data")

    # Деякі повідомлення мають data як список, інші — як dict
    rows: List[Dict] = []
    if isinstance(data, list):
        rows = [d for d in data if isinstance(d, dict)]
    elif isinstance(data, dict):
        rows = [data]

    for row in rows:
        sym = row.get("symbol") or _symbol_from_topic(topic)
        last = _extract_first_number(row, ["lastPrice", "lastPriceE4", "lastPriceE8"])
        mark = _extract_first_number(row, ["markPrice", "markPriceE4", "markPriceE8"])
        if sym:
            yield {"symbol": sym, "last": last, "mark": mark}


__all__ = [
    "BybitWS",
    "exp_backoff_with_jitter",
    "iter_ticker_entries",
]
