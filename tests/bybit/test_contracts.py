# tests/bybit/test_contracts.py
import pytest

from exchanges.bybit.factory import create_bybit_client
from exchanges.bybit.types import BybitConfig
from exchanges.contracts import (
    IAccountClient,
    IExchangeClient,
    IExchangePublic,
    ITradingClient,
)


@pytest.mark.asyncio
async def test_bybit_client_shapes():
    cfg = BybitConfig(enabled=True)
    client = create_bybit_client(cfg)
    assert isinstance(client.public, IExchangePublic)
    assert isinstance(client.trading, ITradingClient)
    assert isinstance(client.account, IAccountClient)
    assert isinstance(client, IExchangeClient)
