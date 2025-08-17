# tests/bybit/test_public_category.py
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from exchanges.bybit.public_client import BybitPublicClient
from exchanges.bybit.types import BybitConfig


class _FakeHTTP:
    def __init__(self):
        self.last_params: Dict[str, Any] = {}

    async def get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        self.last_params = params or {}
        # Повертаємо валідний payload для парсерів тикера
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "bid1Price": "1",
                        "ask1Price": "2",
                        "lastPrice": "1.5",
                        "updateTime": 1739900000000,
                    }
                ]
            },
        }

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_category_linear_used_in_params():
    cfg = BybitConfig(enabled=True, perp_enabled=True, default_category="linear")
    client = BybitPublicClient(cfg, http_client=None)
    # підміняємо HTTP на фейковий, щоб перехопити params
    client.http = _FakeHTTP()
    _ = await client.get_ticker("BTC/USDT")
    assert client.http.last_params.get("category") == "linear"
