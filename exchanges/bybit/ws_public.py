from __future__ import annotations

import asyncio
import contextlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional


# ---- Модель тікера ---------------------------------------------------------
@dataclass
class Ticker:
    symbol: str
    bid: float
    ask: float
    last: float
    ts: datetime


def _pair_from_bybit_symbol(sym: str) -> str:
    # "BTCUSDT" -> "BTC/USDT", "BTCUSD" -> "BTC/USD"
    if len(sym) > 4 and sym.endswith("USDT"):
        return f"{sym[:-4]}/USDT"
    if len(sym) > 3 and sym.endswith("USD"):
        return f"{sym[:-3]}/USD"
    return sym


def _to_float(x: Any) -> float:
    if x is None or x == "":
        return 0.0
    try:
        return float(x)
    except Exception:
        return 0.0


def _dt_from_ms(ms: int | float | None) -> datetime:
    if not ms:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)


# ---- Парсер WS-повідомлень tickers ----------------------------------------
def parse_ws_ticker(payload: dict[str, Any]) -> Optional[Ticker]:
    """
    Підтримує два формати data:
      1) list[dict] (type: snapshot)
      2) dict       (type: delta)

    ВАЖЛИВО: у проді Bybit часто шле topic як "tickers.BTCUSDT".
             Приймаємо як "tickers", так і "tickers.*".
    """
    topic = str(payload.get("topic", ""))
    if not (topic == "tickers" or topic.startswith("tickers.")):
        return None

    data = payload.get("data")
    if isinstance(data, list):
        if not data:
            return None
        d = data[0]
        symbol = _pair_from_bybit_symbol(str(d.get("symbol", "")))
        # snapshot (spot): bid1Price/ask1Price/lastPrice
        bid = _to_float(d.get("bid1Price"))
        ask = _to_float(d.get("ask1Price"))
        last = _to_float(d.get("lastPrice"))
        ts = _dt_from_ms(d.get("updateTime") or payload.get("ts"))
        return Ticker(symbol=symbol, bid=bid, ask=ask, last=last, ts=ts)

    if isinstance(data, dict):
        d = data
        symbol = _pair_from_bybit_symbol(str(d.get("symbol", "")))
        # delta (деривативи/спот мають різні ключі)
        bid = _to_float(d.get("bidPrice") or d.get("bid1Price"))
        ask = _to_float(d.get("askPrice") or d.get("ask1Price"))
        last = _to_float(d.get("price") or d.get("lastPrice"))
        ts = _dt_from_ms(d.get("updateTime") or payload.get("ts"))
        return Ticker(symbol=symbol, bid=bid, ask=ask, last=last, ts=ts)

    return None


# ---- Парсер топу книги (orderbook.1.*) ------------------------------------
def parse_ws_orderbook_top(
    payload: dict[str, Any],
) -> Optional[tuple[str, float, float, datetime]]:
    """
    Витягає best bid/ask з orderbook.1.<SYMBOL>
    Формати:
      snapshot: data: [ { "s": "BTCUSDT", "b": [["65000","0.1"], ...], "a": [["65010","0.2"], ...] } ]
      delta:    data: { "s": "BTCUSDT", "b": [["65001","0.1"]], "a": [["65009","0.1"]] }
    Повертає: (symbol_pair, best_bid, best_ask, ts)
    """
    topic = str(payload.get("topic", ""))
    if not topic.startswith("orderbook."):
        return None

    data = payload.get("data")
    if isinstance(data, list):
        if not data:
            return None
        d = data[0]
    elif isinstance(data, dict):
        d = data
    else:
        return None

    raw_sym = str(d.get("s") or d.get("symbol") or "")
    symbol = _pair_from_bybit_symbol(raw_sym) if raw_sym else ""

    def _first_price(levels: Any) -> float:
        # очікуємо [["price","qty"], ...]
        if isinstance(levels, list) and levels and isinstance(levels[0], list) and levels[0]:
            return _to_float(levels[0][0])
        return 0.0

    best_bid = _first_price(d.get("b"))
    best_ask = _first_price(d.get("a"))
    ts = _dt_from_ms(payload.get("ts") or d.get("ts") or d.get("u"))

    if not symbol or (best_bid == 0.0 and best_ask == 0.0):
        # іноді може прилетіти лише одна сторона — все одно повернемо, щоб оновити частково
        pass

    return symbol or "", best_bid, best_ask, ts


# ---- WS клієнт (public) ----------------------------------------------------
_OnTicker = Optional[Callable[[Ticker], Any]]


class _WsPublic:
    """
    Легковаговий WS-клієнт Bybit (public v5) для потоків:
      - tickers.<SYMBOL>
      - orderbook.1.<SYMBOL> (опційно, щоб мати реальні bid/ask на testnet)
    Плавне завершення через stop()/close().
    """

    def __init__(
        self,
        symbol: str,
        on_ticker: _OnTicker = None,
        category: Optional[str] = None,
        read_timeout_s: float = 30.0,
        retry_backoff_s: float = 5.0,
        ping_interval_s: float = 20.0,
        use_orderbook_top: Optional[bool] = None,
    ) -> None:
        self.symbol = symbol
        self.on_ticker = on_ticker
        self.category = (category or os.getenv("BYBIT_DEFAULT_CATEGORY", "spot") or "spot").lower()

        # Визначаємо testnet/mainnet за REST-URL з env
        public_url = os.getenv("BYBIT_PUBLIC_URL", "https://api.bybit.com")
        is_testnet = "testnet" in public_url.lower()

        host = "wss://stream-testnet.bybit.com" if is_testnet else "wss://stream.bybit.com"
        self._url = f"{host}/v5/public/{self.category}"

        self._read_timeout_s = read_timeout_s
        self._retry_backoff_s = retry_backoff_s
        self._ping_interval_s = ping_interval_s

        if use_orderbook_top is None:
            # За замовчуванням вмикаємо на testnet (де tickers часто без bid/ask)
            env_flag = os.getenv("BYBIT_WS_USE_ORDERBOOK_TOP")
            self._use_ob = (env_flag == "1") if env_flag is not None else True
        else:
            self._use_ob = bool(use_orderbook_top)

        self._stop_event = asyncio.Event()
        self._ws: Any = None
        self._ping_task: Optional[asyncio.Task] = None

        # останній відомий last (щоб у тікері з ордербука не було 0.0)
        self._last_price: float = 0.0
        self._last_ts: datetime = _dt_from_ms(None)

    async def _ping_loop(self) -> None:
        # Власний ping, бо ping_interval=None у websockets
        while not self._stop_event.is_set():
            await asyncio.sleep(self._ping_interval_s)
            if self._ws is not None:
                with contextlib.suppress(Exception):
                    await self._ws.send(json.dumps({"op": "ping"}))

    async def _cancel_ping_task(self) -> None:
        """Скасувати і коректно дочекатися ping-loop, подавивши CancelledError."""
        t = self._ping_task
        self._ping_task = None
        if t:
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await t

    async def _wait_sub_ack(self, ws, timeout: float = 5.0) -> None:
        """
        Коротке очікування ACK після subscribe.
        Якщо під час очікування прилітають події — одразу обробляємо.
        """
        end = asyncio.get_event_loop().time() + timeout
        while not self._stop_event.is_set() and asyncio.get_event_loop().time() < end:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            msg = json.loads(raw)
            # ACK Bybit: {"op":"subscribe","success":true,...} або retCode=0
            if msg.get("op") == "subscribe" and (
                msg.get("success") is True or msg.get("retCode") == 0
            ):
                return

            # Може прилетіти перший тікер/ордербук ще до ACK
            await self._handle_message(msg)

    async def _handle_message(self, msg: dict[str, Any]) -> None:
        # tickers
        t = parse_ws_ticker(msg)
        if t:
            self._last_price = t.last or self._last_price
            self._last_ts = t.ts or self._last_ts
            if self.on_ticker:
                if asyncio.iscoroutinefunction(self.on_ticker):  # type: ignore[arg-type]
                    await self.on_ticker(t)  # type: ignore[misc]
                else:
                    self.on_ticker(t)
            return

        # orderbook top
        ob = parse_ws_orderbook_top(msg)
        if ob:
            symbol, best_bid, best_ask, ts = ob
            if not symbol:
                return
            out = Ticker(
                symbol=symbol,
                bid=best_bid,
                ask=best_ask,
                last=self._last_price,  # підставляємо останній last з tickers
                ts=ts or self._last_ts,
            )
            if self.on_ticker:
                if asyncio.iscoroutinefunction(self.on_ticker):  # type: ignore[arg-type]
                    await self.on_ticker(out)  # type: ignore[misc]
                else:
                    self.on_ticker(out)

    async def run(self) -> None:
        import websockets

        attempt = 0
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    self._url,
                    ping_interval=None,  # самі пінгуємо
                    close_timeout=3,
                    max_queue=None,
                ) as ws:
                    self._ws = ws

                    args = [f"tickers.{self.symbol}"]
                    if self._use_ob:
                        args.append(f"orderbook.1.{self.symbol}")

                    sub = {"op": "subscribe", "args": args}
                    await ws.send(json.dumps(sub))

                    # зачекаємо коротко на ACK (не блокує отримання перших повідомлень)
                    await self._wait_sub_ack(ws, timeout=5.0)

                    # пінг-потік
                    self._ping_task = asyncio.create_task(self._ping_loop())

                    # прийом повідомлень
                    while not self._stop_event.is_set():
                        raw = await asyncio.wait_for(ws.recv(), timeout=self._read_timeout_s)
                        msg = json.loads(raw)
                        await self._handle_message(msg)

                # нормальне закриття сокета — виходимо з циклу
                break

            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                attempt += 1
                await self._cancel_ping_task()
                await asyncio.sleep(min(60.0, attempt * self._retry_backoff_s))
                continue

            except Exception:
                attempt += 1
                await self._cancel_ping_task()
                await asyncio.sleep(min(60.0, attempt * self._retry_backoff_s))
                continue

            finally:
                await self._cancel_ping_task()
                self._ws = None

    async def stop(self) -> None:
        """Плавно зупиняє клієнт: сигнал, зупинка пінгу, закриття сокета."""
        self._stop_event.set()
        await self._cancel_ping_task()
        with contextlib.suppress(Exception):
            if self._ws is not None:
                await asyncio.wait_for(self._ws.close(), timeout=2)

    # Сумісність: підтримати close() як синонім stop()
    async def close(self) -> None:  # noqa: D401
        await self.stop()


# Публічний клас (експорт)
class BybitWsPublic(_WsPublic):
    pass
