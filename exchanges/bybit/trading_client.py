# exchanges/bybit/trading_client.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from exchanges.contracts import ITradingClient  # ✅ наслідуємо контракт

from ._http import SignedHTTPClient
from .symbol_mapper import to_bybit_symbol
from .types import BybitConfig


def _ensure_str_num(x: float | int | str | None) -> Optional[str]:
    if x is None:
        return None
    # Bybit очікує числа як рядки
    return str(x)


def _side_to_bybit(side: str) -> str:
    s = side.strip().lower()
    if s == "buy":
        return "Buy"
    if s == "sell":
        return "Sell"
    raise ValueError(f"Unsupported side: {side!r}")


def _type_to_bybit(order_type: str) -> str:
    t = order_type.strip().lower()
    if t == "limit":
        return "Limit"
    if t == "market":
        return "Market"
    raise ValueError(f"Unsupported order type: {order_type!r}")


def _market_to_category(market: str, default_category: str) -> str:
    """
    market: "spot" або "perp" (перп = linear), для зворотної сумісності.
    Якщо market не заданий, беремо cfg.default_category.
    """
    m = (market or "").strip().lower()
    if m in ("", None):
        return default_category
    if m == "spot":
        return "spot"
    if m in ("perp", "linear"):
        return "linear"
    # залишимо дефолт, щоб не ламати потік
    return default_category


class BybitTradingClient(ITradingClient):
    """
    Приватний клієнт для створення/скасування ордерів (Bybit v5).
    Працює і для spot, і для linear (перпети).
    """

    def __init__(
        self,
        cfg: BybitConfig,
        http_client: Optional[SignedHTTPClient] = None,  # інжект для тестів
    ):
        self.cfg = cfg
        if http_client is not None:
            self.http: Optional[SignedHTTPClient] = http_client
        else:
            api_key = os.getenv("BYBIT_API_KEY", "")
            api_secret = os.getenv("BYBIT_API_SECRET", "")
            if not api_key or not api_secret:
                self.http = None
            else:
                self.http = SignedHTTPClient(
                    base_url=cfg.base_url_private,
                    api_key=api_key,
                    api_secret=api_secret,
                    recv_window_ms=cfg.recv_window_ms,
                )

    async def _ensure_http(self) -> SignedHTTPClient:
        if self.http is None:
            raise RuntimeError("BYBIT ключі не задані (BYBIT_API_KEY/BYBIT_API_SECRET).")
        return self.http

    async def create_order(
        self,
        *,
        symbol: str,
        side: str,  # "buy" | "sell"
        type: str,  # "limit" | "market"
        qty: float,
        price: Optional[float] = None,
        market: str = "spot",  # "spot" | "perp" (alias "linear")
        time_in_force: str = "GTC",
        order_link_id: Optional[str] = None,
        reduce_only: Optional[bool] = None,  # для перпів
    ) -> Dict[str, Any]:
        """
        POST /v5/order/create
        Мінімальний набір полів для spot/linear.
        """
        http = await self._ensure_http()

        category = _market_to_category(market, self.cfg.default_category)
        bybit_side = _side_to_bybit(side)
        bybit_type = _type_to_bybit(type)

        if bybit_type == "Limit" and price is None:
            raise ValueError("price is required for limit orders")

        payload: Dict[str, Any] = {
            "category": category,
            "symbol": to_bybit_symbol(symbol),
            "side": bybit_side,
            "orderType": bybit_type,
            "qty": _ensure_str_num(qty),
            "timeInForce": time_in_force,
        }
        if price is not None:
            payload["price"] = _ensure_str_num(price)
        if order_link_id:
            payload["orderLinkId"] = order_link_id
        if reduce_only is not None:
            payload["reduceOnly"] = bool(reduce_only)

        # HTTPClient/SignedHTTPClient вже робить валідацію retCode
        data = await http.post("/v5/order/create", json=payload)
        return data

    async def cancel_order(
        self,
        *,
        symbol: str,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        market: str = "spot",
    ) -> Dict[str, Any]:
        """
        POST /v5/order/cancel
        Потрібен або orderId, або orderLinkId.
        """
        http = await self._ensure_http()

        if not order_id and not order_link_id:
            raise ValueError("order_id or order_link_id is required")

        category = _market_to_category(market, self.cfg.default_category)

        payload: Dict[str, Any] = {
            "category": category,
            "symbol": to_bybit_symbol(symbol),
        }
        if order_id:
            payload["orderId"] = order_id
        if order_link_id:
            payload["orderLinkId"] = order_link_id

        data = await http.post("/v5/order/cancel", json=payload)
        return data

    async def close(self) -> None:
        """Закриває внутрішній HTTP-клієнт, якщо він створений."""
        if self.http is not None:
            await self.http.close()
