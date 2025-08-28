# tests/bybit/test_private_e2e.py
from __future__ import annotations

import os

import pytest

from exchanges.bybit.account_client import BybitAccountClient
from exchanges.bybit.types import BybitConfig

E2E = os.getenv("BYBIT_E2E") == "1"


@pytest.mark.asyncio
@pytest.mark.skipif(not E2E, reason="set BYBIT_E2E=1 to run e2e testnet smoke")
async def test_e2e_wallet_balances_smoke():
    cfg = BybitConfig(
        enabled=True,
        base_url_public=os.getenv("BYBIT_PUBLIC_URL", "https://api-testnet.bybit.com"),
        base_url_private=os.getenv("BYBIT_PRIVATE_URL", "https://api-testnet.bybit.com"),
        default_category=os.getenv("BYBIT_DEFAULT_CATEGORY", "spot"),
    )
    acc = BybitAccountClient(cfg)
    try:
        bals = await acc.get_balances()
        assert isinstance(bals, list)
    finally:
        if acc.http is not None:
            await acc.http.close()
