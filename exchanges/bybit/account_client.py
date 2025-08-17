# exchanges/bybit/account_client.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from exchanges.contracts import Balance, IAccountClient

from ._http import HTTPClient
from .types import BybitConfig


class BybitAccountClient(IAccountClient):
    def __init__(self, cfg: BybitConfig):
        self.cfg = cfg
        self.http = HTTPClient(cfg.base_url_private)

    async def get_balances(
        self, assets: Optional[Iterable[str]] = None
    ) -> List[Balance]:
        return []

    async def get_fees(self) -> Dict[str, Any]:
        return {}

    async def close(self) -> None:
        await self.http.close()
