# exchanges/bybit/public_client.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from exchanges.contracts import (
    Candle,
    IExchangePublic,
    OrderBook,
    OrderBookLevel,
    Ticker,
)

from ._http import HTTPClient
from .symbol_mapper import normalize_symbol
from .types import BybitConfig, Interval


class BybitPublicClient(IExchangePublic):
    def __init__(self, cfg: BybitConfig):
        self.cfg = cfg
        self.http = HTTPClient(cfg.base_url_public)

    async def get_ticker(self, symbol: str) -> Ticker:
        # NOTE: шлях/параметри винесемо у наступному підкроці (поки — заглушка контракту)
        now = datetime.now(timezone.utc)
        return Ticker(
            symbol=normalize_symbol(symbol), bid=0.0, ask=0.0, last=0.0, ts=now
        )

    async def get_order_book(self, symbol: str, depth: int = 50) -> OrderBook:
        now = datetime.now(timezone.utc)
        return OrderBook(
            symbol=normalize_symbol(symbol),
            bids=[OrderBookLevel(0.0, 0.0)],
            asks=[OrderBookLevel(0.0, 0.0)],
            ts=now,
        )

    async def get_candles(
        self, symbol: str, interval: Interval, limit: int = 200
    ) -> List[Candle]:
        now = datetime.now(timezone.utc)
        return [
            Candle(
                symbol=normalize_symbol(symbol),
                interval=interval,
                open_time=now,
                open=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
                volume=0.0,
            )
        ]

    async def close(self) -> None:
        await self.http.close()
