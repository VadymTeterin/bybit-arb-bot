# src/exchanges/bybit/ws.py
from __future__ import annotations

import asyncio
import json
import random
from typing import Awaitable, Callable, Iterable, Optional

import aiohttp
from loguru import logger


def exp_backoff_with_jitter(attempt: int, base: float = 1.0, cap: float = 30.0) -> float:
    """
    Експоненціальний backoff з невеликим jitter.
    attempt: 1,2,3... -> ~1,2,4,8,... (обмежено cap)
    """
    if attempt < 1:
        attempt = 1
    delay = min(cap, base * (2 ** (attempt - 1)))
    # jitter в [0, delay/2]
    return delay - (delay * 0.5 * random.random())


class BybitWS:
    """
    Легкий WS‑клієнт Bybit v5 (public).
    Очікує список топіків формату "tickers.BTCUSDT" або "tickers".
    """

    def __init__(self, url: str, topics: Iterable[str]) -> None:
        self.url = url
        self.topics = list(topics)
        self._stop = asyncio.Event()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        if not self.topics:
            logger.bind(tag="WS").warning("No topics provided, skipping subscribe")
            return
        payload = {"op": "subscribe", "args": self.topics}
        await ws.send_str(json.dumps(payload))
        logger.bind(tag="WS").info(f"Subscribed to {len(self.topics)} topics")

    async def run(
        self,
        on_message: Callable[[dict], Awaitable[None]],
        backoff: Callable[[int], float] = exp_backoff_with_jitter,
        heartbeat: int = 30,
    ) -> None:
        """
        Головний цикл WS з автоперепідключенням.
        on_message: корутина, що приймає dict (розпарсений JSON повідомлення).
        """
        self._stop.clear()
        attempt = 1

        async with aiohttp.ClientSession() as session:
            self._session = session

            while not self._stop.is_set():
                try:
                    logger.bind(tag="WS").info(f"Connecting to {self.url}")
                    async with session.ws_connect(self.url, heartbeat=heartbeat) as ws:
                        attempt = 1  # успішне підключення — скидаємо лічильник
                        await self._subscribe(ws)

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    data = json.loads(msg.data)
                                except Exception:
                                    logger.bind(tag="WS").warning("Non‑JSON message, skipped")
                                    continue
                                await on_message(data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                raise ConnectionError("WebSocket closed or error state")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    delay = backoff(attempt)
                    attempt += 1
                    logger.bind(tag="RECONNECT").warning(
                        f"WS error: {e!r}. Reconnect in {delay:.1f}s (attempt {attempt-1})"
                    )
                    try:
                        await asyncio.wait_for(self._stop.wait(), timeout=delay)
                    except asyncio.TimeoutError:
                        pass  # таймаут минув — пробуємо знову

    async def stop(self) -> None:
        self._stop.set()
        if self._session and not self._session.closed:
            await self._session.close()
