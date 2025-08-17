# exchanges/bybit/trading_client.py
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Literal, Optional

from exchanges.contracts import ITradingClient, Position

from ._http import SignedHTTPClient
from .types import BybitConfig, MarketType


class BybitTradingClient(ITradingClient):
    def __init__(self, cfg: BybitConfig):
        self.cfg = cfg
        api_key = os.getenv("BYBIT_API_KEY", "")
        api_secret = os.getenv("BYBIT_API_SECRET", "")
        if not api_key or not api_secret:
            self.http: Optional[SignedHTTPClient] = None
        else:
            self.http = SignedHTTPClient(
                base_url=cfg.base_url_private,
                api_key=api_key,
                api_secret=api_secret,
                recv_window_ms=cfg.recv_window_ms,
            )

    async def _ensure_http(self) -> SignedHTTPClient:
        if self.http is None:
            raise RuntimeError(
                "BYBIT ключі не задані (BYBIT_API_KEY/BYBIT_API_SECRET)."
            )
        return self.http

    def _category_for_market(self, market: MarketType) -> str:
        if market == "perp":
            return "linear"  # USDT-перпи
        return "spot"

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
        http = await self._ensure_http()
        category = self._category_for_market(market)
        body: Dict[str, Any] = {
            "category": category,
            "symbol": symbol.replace("/", ""),  # BYBIT очікує BTCUSDT
            "side": "Buy" if side == "buy" else "Sell",
            "orderType": "Limit" if type == "limit" else "Market",
            "qty": str(qty),
            "reduceOnly": reduce_only,
        }
        if price is not None:
            body["price"] = str(price)
        if extra:
            body.update(extra)
        # v5: POST /v5/order/create
        data = await http.post("/v5/order/create", json=body)
        return {
            "status": "submitted",
            "exchange": "bybit",
            "result": data.get("result"),
        }

    async def cancel_order(
        self, symbol: str, order_id: str, market: MarketType = "spot"
    ) -> Dict[str, Any]:
        http = await self._ensure_http()
        category = self._category_for_market(market)
        body: Dict[str, Any] = {
            "category": category,
            "symbol": symbol.replace("/", ""),
            "orderId": order_id,
        }
        data = await http.post("/v5/order/cancel", json=body)
        return {
            "status": "cancel_submitted",
            "exchange": "bybit",
            "result": data.get("result"),
        }

    async def get_positions(
        self, symbols: Optional[Iterable[str]] = None
    ) -> List[Position]:
        # Для spot позицій нема; для перпів: /v5/position/list (category=linear)
        return []

    async def set_leverage(self, symbol: str, leverage: float) -> None:
        # Для перпів: /v5/position/set-leverage — додамо на кроці трейдингу
        return None
