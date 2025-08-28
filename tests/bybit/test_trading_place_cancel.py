# tests/bybit/test_trading_place_cancel.py
from __future__ import annotations

from typing import Any

import pytest

from exchanges.bybit.trading_client import BybitTradingClient
from exchanges.bybit.types import BybitConfig


class _FakeSignedHTTP:
    def __init__(self) -> None:
        self.last_path: str | None = None
        self.last_json: dict[str, Any] | None = None

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.last_path = path
        self.last_json = dict(json or {})
        # імітуємо успішну відповідь Bybit
        if path == "/v5/order/create":
            return {"retCode": 0, "result": {"orderId": "OID123"}}
        if path == "/v5/order/cancel":
            return {"retCode": 0, "result": {"success": True}}
        return {"retCode": 0, "result": {}}


@pytest.mark.asyncio
async def test_create_market_spot_minimal():
    cfg = BybitConfig(
        enabled=True,
        base_url_public="http://fake-public",
        base_url_private="http://fake-private",
        default_category="spot",
    )
    fake = _FakeSignedHTTP()
    tr = BybitTradingClient(cfg, http_client=fake)  # інжектуємо фейковий HTTP

    data = await tr.create_order(
        symbol="BTC/USDT", side="buy", type="market", qty=0.0001, market="spot"
    )
    assert data["retCode"] == 0
    assert fake.last_path == "/v5/order/create"
    assert fake.last_json is not None
    j = fake.last_json
    assert j["category"] == "spot"
    assert j["symbol"] == "BTCUSDT"
    assert j["side"] == "Buy"
    assert j["orderType"] == "Market"
    assert j["qty"] == "0.0001"
    assert "price" not in j


@pytest.mark.asyncio
async def test_create_limit_linear_requires_price_and_sets_it():
    cfg = BybitConfig(
        enabled=True,
        base_url_public="http://fake-public",
        base_url_private="http://fake-private",
        default_category="spot",  # але ми передамо market="perp"
    )
    fake = _FakeSignedHTTP()
    tr = BybitTradingClient(cfg, http_client=fake)

    # без ціни має впасти
    with pytest.raises(ValueError):
        await tr.create_order(symbol="BTC/USDT", side="sell", type="limit", qty=1, market="perp")

    # з ціною — ок
    data = await tr.create_order(
        symbol="BTC/USDT", side="sell", type="limit", qty=1, price=10000, market="perp"
    )
    assert data["retCode"] == 0
    j = fake.last_json or {}
    assert j["category"] == "linear"
    assert j["symbol"] == "BTCUSDT"
    assert j["side"] == "Sell"
    assert j["orderType"] == "Limit"
    assert j["qty"] == "1"
    assert j["price"] == "10000"


@pytest.mark.asyncio
async def test_cancel_order_by_id_spot():
    cfg = BybitConfig(
        enabled=True,
        base_url_public="http://fake-public",
        base_url_private="http://fake-private",
        default_category="spot",
    )
    fake = _FakeSignedHTTP()
    tr = BybitTradingClient(cfg, http_client=fake)

    data = await tr.cancel_order(symbol="BTC/USDT", order_id="OID123", market="spot")
    assert data["retCode"] == 0
    assert fake.last_path == "/v5/order/cancel"
    j = fake.last_json or {}
    assert j["category"] == "spot"
    assert j["symbol"] == "BTCUSDT"
    assert j["orderId"] == "OID123"
    assert "orderLinkId" not in j


@pytest.mark.asyncio
async def test_cancel_order_requires_id_or_link():
    cfg = BybitConfig(
        enabled=True,
        base_url_public="http://fake-public",
        base_url_private="http://fake-private",
        default_category="spot",
    )
    tr = BybitTradingClient(cfg, http_client=_FakeSignedHTTP())
    with pytest.raises(ValueError):
        await tr.cancel_order(symbol="BTC/USDT")
