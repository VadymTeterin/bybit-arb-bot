# exchanges/bybit/public_client.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from exchanges.contracts import (
    Candle,
    IExchangePublic,
    OrderBook,
    OrderBookLevel,
    Ticker,
)

from ._http import HTTPClient
from .errors import map_error
from .rate_limiter import AsyncTokenBucket
from .symbol_mapper import normalize_symbol, to_bybit_symbol
from .types import BybitConfig, Interval


def _to_dt(ms: int | str) -> datetime:
    ms_int = int(ms)
    return datetime.fromtimestamp(ms_int / 1000.0, tz=timezone.utc)


_INTERVAL_MAP: Dict[Interval, str] = {
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
}


def parse_ticker(payload: Dict[str, Any], symbol_req: str) -> Ticker:
    if int(payload.get("retCode", -1)) != 0:
        raise map_error(payload.get("retCode"), payload.get("retMsg", "unknown error"))

    result = payload.get("result") or {}
    lst = result.get("list") or []
    if not lst:
        raise ValueError("Empty tickers list")

    t = lst[0]
    bid = float(t.get("bid1Price") or 0.0)
    ask = float(t.get("ask1Price") or 0.0)
    last = float(t.get("lastPrice") or 0.0)

    # Fallback for testnet/v5 where updateTime/result.ts may be missing:
    raw_ts = t.get("updateTime") or result.get("ts") or payload.get("time") or 0
    ts = _to_dt(raw_ts)

    return Ticker(symbol=normalize_symbol(symbol_req), bid=bid, ask=ask, last=last, ts=ts)


def parse_order_book(payload: Dict[str, Any], symbol_req: str) -> OrderBook:
    if int(payload.get("retCode", -1)) != 0:
        raise map_error(payload.get("retCode"), payload.get("retMsg", "unknown error"))

    result = payload.get("result") or {}
    bids_raw = result.get("b") or []
    asks_raw = result.get("a") or []
    ts = _to_dt(result.get("ts") or 0)

    bids = [OrderBookLevel(price=float(p), qty=float(q)) for p, q in bids_raw]
    asks = [OrderBookLevel(price=float(p), qty=float(q)) for p, q in asks_raw]

    return OrderBook(symbol=normalize_symbol(symbol_req), bids=bids, asks=asks, ts=ts)


def parse_candles(payload: Dict[str, Any], symbol_req: str, interval: Interval) -> List[Candle]:
    if int(payload.get("retCode", -1)) != 0:
        raise map_error(payload.get("retCode"), payload.get("retMsg", "unknown error"))

    result = payload.get("result") or {}
    lst = result.get("list") or []
    out: List[Candle] = []
    for row in lst:
        open_time = _to_dt(row[0])
        open_ = float(row[1])
        high = float(row[2])
        low = float(row[3])
        close = float(row[4])
        volume = float(row[5])
        out.append(
            Candle(
                symbol=normalize_symbol(symbol_req),
                interval=interval,
                open_time=open_time,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return out


class BybitPublicClient(IExchangePublic):
    def __init__(
        self,
        cfg: BybitConfig,
        limiter: Optional[AsyncTokenBucket] = None,
        http_client: Optional[HTTPClient] = None,  # тестовий інжект
    ):
        self.cfg = cfg
        self.limiter = limiter or AsyncTokenBucket(rate_per_sec=10, burst=20)
        self.http = http_client or HTTPClient(cfg.base_url_public, limiter=self.limiter)

    @property
    def _category(self) -> str:
        # Використовуємо дефолт з конфігу; якщо треба перпи — встановлюємо "linear"
        return self.cfg.default_category

    async def get_ticker(self, symbol: str) -> Ticker:
        params = {
            "category": self._category,
            "symbol": to_bybit_symbol(symbol),
        }
        data = await self.http.get("/v5/market/tickers", params=params)
        return parse_ticker(data, symbol)

    async def get_order_book(self, symbol: str, depth: int = 50) -> OrderBook:
        params = {
            "category": self._category,
            "symbol": to_bybit_symbol(symbol),
            "limit": depth,
        }
        data = await self.http.get("/v5/market/orderbook", params=params)
        return parse_order_book(data, symbol)

    async def get_candles(self, symbol: str, interval: Interval, limit: int = 200) -> List[Candle]:
        bybit_interval = _INTERVAL_MAP[interval]
        params = {
            "category": self._category,
            "symbol": to_bybit_symbol(symbol),
            "interval": bybit_interval,
            "limit": min(max(int(limit), 1), 1000),
        }
        data = await self.http.get("/v5/market/kline", params=params)
        return parse_candles(data, symbol, interval)

    async def close(self) -> None:
        await self.http.close()
