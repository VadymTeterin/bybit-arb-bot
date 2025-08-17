import asyncio
import contextlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

import websockets


# Простий тип для уніфікованого тікера
@dataclass
class Ticker:
    symbol: str
    bid: float
    ask: float
    last: float
    ts: datetime


def _to_ms_ts(x: Any) -> Optional[int]:
    """Допоміжно: приймає int/str ms, повертає int або None."""
    if x is None:
        return None
    try:
        return int(x)
    except Exception:
        return None


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def _norm_symbol(s: str) -> str:
    # "BTCUSDT" -> "BTC/USDT"
    if "/" in s:
        return s
    if len(s) >= 6 and s.endswith("USDT"):
        return f"{s[:-4]}/USDT"
    if len(s) >= 6 and s.endswith("USDC"):
        return f"{s[:-4]}/USDC"
    # загальний випадок: останні 3-4 символи як котирувана валюта
    return f"{s[:-3]}/{s[-3:]}"


def parse_ws_ticker(payload: Dict[str, Any]) -> Optional[Ticker]:
    """
    Уніфікує Bybit WS v5 `tickers` (spot/linear) у Ticker.
    Підтримує і список у `data`, і словник.
    """
    data = payload.get("data")
    if data is None:
        return None

    rec: Dict[str, Any]
    if isinstance(data, list):
        if not data:
            return None
        rec = data[0]
        bid = rec.get("bid1Price")
        ask = rec.get("ask1Price")
        last = rec.get("lastPrice")
    elif isinstance(data, dict):
        rec = data
        bid = rec.get("bidPrice") or rec.get("bid1Price")
        ask = rec.get("askPrice") or rec.get("ask1Price")
        last = rec.get("price") or rec.get("lastPrice")
    else:
        return None

    sym = rec.get("symbol") or payload.get("symbol")
    if not sym:
        return None

    # таймстемп: пріоритет updateTime, інакше верхній ts
    ms = _to_ms_ts(rec.get("updateTime"))
    if ms is None:
        ms = _to_ms_ts(payload.get("ts"))
    if ms is None:
        return None

    def f2(x: Any) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0

    return Ticker(
        symbol=_norm_symbol(sym),
        bid=f2(bid),
        ask=f2(ask),
        last=f2(last),
        ts=_ms_to_dt(ms),
    )


@dataclass
class WsPublicConfig:
    category: str = os.getenv("BYBIT_DEFAULT_CATEGORY", "spot") or "spot"
    # інтервали/таймаути
    ping_interval_s: float = 20.0
    read_timeout_s: float = 30.0
    retry_backoff_s: float = 3.0

    # Явний URL (інакше побудується з PUBLIC_URL)
    url: Optional[str] = None


def _build_ws_url(cfg: WsPublicConfig) -> str:
    """Будуємо WS endpoint з урахуванням testnet/mainnet та категорії."""
    if cfg.url:
        return cfg.url

    http_base = os.getenv("BYBIT_PUBLIC_URL", "https://api.bybit.com").lower()
    is_testnet = "testnet" in http_base
    host = "wss://stream-testnet.bybit.com" if is_testnet else "wss://stream.bybit.com"

    cat = cfg.category.lower()
    # дозволені шляхи: spot | linear | inverse | option | spread
    return f"{host}/v5/public/{cat}"


class _WsPublic:
    """
    Легкий Bybit WS v5 клієнт лише для топіка `tickers`.
    Викликає on_ticker(Ticker) при кожному апдейті.
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        *,
        cfg: Optional[WsPublicConfig] = None,
        on_ticker: Optional[Callable[[Ticker], Awaitable[None] | None]] = None,
    ) -> None:
        self._cfg = cfg or WsPublicConfig()
        self._url = _build_ws_url(self._cfg)
        self._symbol = symbol
        self._on_ticker = on_ticker

    async def _subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        sub = {
            "op": "subscribe",
            "args": [f"tickers.{self._symbol}"],
        }
        await ws.send(json.dumps(sub))

    async def _ping_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        while True:
            await asyncio.sleep(self._cfg.ping_interval_s)
            try:
                await ws.ping()
            except Exception:
                return

    async def run(self) -> None:
        """
        Нескінченний цикл з перепідключенням.
        Закриття (1000 OK) та скасування – без стек-трейсів.
        """
        attempt = 0
        while True:
            try:
                async with websockets.connect(self._url, ping_interval=None) as ws:
                    await self._subscribe(ws)
                    ping_task = asyncio.create_task(self._ping_loop(ws))

                    try:
                        while True:
                            raw = await asyncio.wait_for(
                                ws.recv(), timeout=self._cfg.read_timeout_s
                            )
                            try:
                                msg = json.loads(raw)
                            except Exception:
                                continue

                            t = parse_ws_ticker(msg)
                            if t and self._on_ticker:
                                res = self._on_ticker(t)
                                if asyncio.iscoroutine(res):
                                    await res
                    finally:
                        # Акуратно зупиняємо пінг-луп
                        if not ping_task.done():
                            ping_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError, Exception):
                            await ping_task

                    attempt = 0  # вдале підключення – скинемо бекоф
            except websockets.exceptions.ConnectionClosedOK:
                # Нормальне закриття сервером – перезапустимо цикл
                pass
            except asyncio.CancelledError:
                # Грейсфул шутдаун – без стек-трейса
                break
            except Exception:
                # Інші помилки – дамо невеликий бекоф і повторимо
                await asyncio.sleep(
                    min(60.0, (attempt + 1) * self._cfg.retry_backoff_s)
                )
                attempt += 1


# API-аліаси, щоб не ламати існуючі імпорти
BybitWsPublic = _WsPublic
BybitPublicWS = _WsPublic
