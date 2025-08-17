# exchanges/bybit/factory.py
from __future__ import annotations

from dataclasses import dataclass

from exchanges.contracts import IExchangeClient

from .account_client import BybitAccountClient
from .public_client import BybitPublicClient
from .trading_client import BybitTradingClient
from .types import BybitConfig


@dataclass
class BybitClient(IExchangeClient):
    public: BybitPublicClient
    trading: BybitTradingClient
    account: BybitAccountClient


def create_bybit_client(cfg: BybitConfig) -> BybitClient:
    """Єдиний спосіб створення агрегованого клієнта BYBIT."""
    pub = BybitPublicClient(cfg)
    trd = BybitTradingClient(cfg)
    acc = BybitAccountClient(cfg)
    return BybitClient(public=pub, trading=trd, account=acc)
