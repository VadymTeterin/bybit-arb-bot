# exchanges/bybit/trading_client.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal, Optional

from exchanges.contracts import ITradingClient, Position

from ._http import HTTPClient
from .types import BybitConfig, MarketType


class BybitTradingClient(ITradingClient):
    def __init__(self, cfg: BybitConfig):
        self.cfg = cfg
        self.http = HTTPClient(cfg.base_url_private)

    async def create_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        type: Literal["limit", "market"],
        qty: float,
        price: Optional[float] = None,
        reduce_only: bool = False,
        market: MarketType = "spot",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {"status": "stub", "symbol": symbol, "market": market}

    async def cancel_order(
        self, symbol: str, order_id: str, market: MarketType = "spot"
    ) -> Dict[str, Any]:
        return {
            "status": "stub",
            "symbol": symbol,
            "order_id": order_id,
            "market": market,
        }

    async def get_positions(
        self, symbols: Optional[Iterable[str]] = None
    ) -> List[Position]:
        return []

    async def set_leverage(self, symbol: str, leverage: float) -> None:
        return None

    async def close(self) -> None:
        await self.http.close()
