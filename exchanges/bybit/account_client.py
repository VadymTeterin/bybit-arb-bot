# exchanges/bybit/account_client.py
from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from exchanges.contracts import Balance, IAccountClient

from ._http import SignedHTTPClient
from .types import BybitConfig


class BybitAccountClient(IAccountClient):
    def __init__(self, cfg: BybitConfig):
        self.cfg = cfg
        api_key = os.getenv("BYBIT_API_KEY", "")
        api_secret = os.getenv("BYBIT_API_SECRET", "")
        if not api_key or not api_secret:
            # Дамо можливість створювати клієнт без ключів, але виклики впадуть у runtime, якщо їх нема.
            self.http: SignedHTTPClient | None = None
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

    async def get_balances(self, assets: Iterable[str] | None = None) -> list[Balance]:
        http = await self._ensure_http()
        # За замовчуванням — spot/unified. Можна параметризувати через cfg.extra згодом.
        params: dict[str, Any] = {"accountType": "UNIFIED"}
        data = await http.get("/v5/account/wallet-balance", params=params)
        result = data.get("result", {}) or {}
        list_ = result.get("list") or []
        out: list[Balance] = []
        for acc in list_:
            coins = acc.get("coin", []) or []
            for c in coins:
                asset = c.get("coin")
                free = float(c.get("walletBalance") or 0.0)
                locked = float(c.get("locked") or 0.0)
                if assets and asset not in assets:
                    continue
                out.append(Balance(asset=asset, free=free, locked=locked))
        return out

    async def get_fees(self) -> dict[str, Any]:
        # У v5 немає єдиного "get fees" для spot, доведеться читати per-symbol або налаштування.
        # Тут повернемо заглушку з result для узгодженості, а реальні ендпоінти додамо пізніше.
        return {"maker": None, "taker": None}
