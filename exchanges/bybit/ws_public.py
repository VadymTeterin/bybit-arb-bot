# exchanges/bybit/ws_public.py
from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional

import websockets

from exchanges.bybit.symbol_mapper import normalize_symbol
from exchanges.contracts import Ticker


@dataclass
class WsConfig:
    category: str = "spot"  # 'spot' | 'linear'
    url: Optional[str] = None  # якщо None — виберемо за категорією
    symbols: tuple[str, ...] = ("BTCUSDT",)  # біржовий формат без слеша
    ping_interval_s: float = 15.0
    connect_timeout_s: float = 10.0
    read_timeout_s: float = 30.0
    max_retries: int = 5
    retry_backoff_s: float = 2.0  # збільшується лінійно: n*retry_backoff_s


def _endpoint_for_category(category: str) -> str:
    cat = (category or "spot").lower()
    if cat == "linear":
        return "wss://stream.bybit.com/v5/public/linear"
    # дефолт
    return "wss://stream.bybit.com/v5/public/spot"


def _ms_to_dt(ms: int | float | None) -> datetime:
    if not ms:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    # Bybit дає мс
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)


def _build_sub_args(symbols: Iterable[str]) -> list[str]:
    return [f"tickers.{s}" for s in symbols]


def parse_ws_ticker(
    payload: Dict[str, Any], symbol_hint: Optional[str] = None
) -> Optional[Ticker]:
    """
    Нормалізує WS-повідомлення Bybit 'tickers.*' -> contracts.Ticker
    Підтримує data як dict або list[dict].
    """
    data = payload.get("data")
    if data is None:
        return None

    row: Dict[str, Any]
    if isinstance(data, dict):
        row = data
    elif isinstance(data, list) and data:
        row = data[0]
    else:
        return None

    exch_sym = row.get("symbol") or (symbol_hint or "")
    symbol = normalize_symbol(exch_sym)

    # У різних режимах поля можуть бути bid1Price/ask1Price/lastPrice або bidPrice/askPrice/price
    bid = float(row.get("bid1Price") or row.get("bidPrice") or 0.0)
    ask = float(row.get("ask1Price") or row.get("askPrice") or 0.0)
    last = float(row.get("lastPrice") or row.get("price") or 0.0)

    # Джерела часу: updateTime > payload.ts > payload.T
    ts_ms = row.get("updateTime") or payload.get("ts") or payload.get("T") or 0
    dt = _ms_to_dt(ts_ms)

    return Ticker(symbol=symbol, bid=bid, ask=ask, last=last, ts=dt)


class BybitWsPublic:
    """
    Легкий WS-клієнт для топіку tickers.* (public).
    """

    def __init__(
        self,
        cfg: WsConfig,
        on_ticker: Optional[Callable[[Ticker], None]] = None,
    ) -> None:
        self._cfg = cfg
        self._on_ticker = on_ticker or (lambda _t: None)
        self._stop = asyncio.Event()
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

    async def close(self) -> None:
        self._stop.set()
        if self._ws and not self._ws.closed:
            await self._ws.close()

    async def run(self) -> None:
        """
        Основний цикл із перепідключенням та пінгом.
        """
        url = self._cfg.url or _endpoint_for_category(self._cfg.category)
        subs = _build_sub_args(self._cfg.symbols)

        attempt = 0
        while not self._stop.is_set():
            try:
                attempt += 1
                async with websockets.connect(
                    url,
                    ping_interval=None,  # самі шлемо "ping" у payload
                    open_timeout=self._cfg.connect_timeout_s,
                    close_timeout=5.0,
                    max_size=2**20,
                ) as ws:
                    self._ws = ws
                    # subscribe
                    sub_msg = {"op": "subscribe", "args": subs}
                    await ws.send(json.dumps(sub_msg))

                    # паралельно: пінги
                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    try:
                        while not self._stop.is_set():
                            raw = await asyncio.wait_for(
                                ws.recv(), timeout=self._cfg.read_timeout_s
                            )
                            if not isinstance(raw, (str, bytes)):
                                continue
                            try:
                                obj = json.loads(
                                    raw if isinstance(raw, str) else raw.decode("utf-8")
                                )
                            except Exception:
                                continue

                            # серверні ping/pong/confirmation
                            if obj.get("op") in ("pong", "subscribe", "ping"):
                                continue

                            t = parse_ws_ticker(obj)
                            if t:
                                self._on_ticker(t)
                    finally:
                        ping_task.cancel()
                        with contextlib.suppress(Exception):
                            await ping_task
                    # якщо вийшли з циклу без помилки — значить закрили самі
                    if self._stop.is_set():
                        break
            except Exception:
                # backoff та повтор
                if attempt > self._cfg.max_retries and self._cfg.max_retries >= 0:
                    # вичерпали ретраї — завершуємо
                    break
                await asyncio.sleep(min(60.0, attempt * self._cfg.retry_backoff_s))

    async def _ping_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        while not self._stop.is_set() and not ws.closed:
            try:
                await ws.send(json.dumps({"op": "ping"}))
            except Exception:
                return
            await asyncio.sleep(self._cfg.ping_interval_s)
