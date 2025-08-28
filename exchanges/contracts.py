# exchanges/contracts.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Protocol,
    runtime_checkable,
)

MarketType = Literal["spot", "perp", "margin"]


@dataclass(frozen=True)
class Ticker:
    symbol: str
    bid: float
    ask: float
    last: float
    ts: datetime


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    qty: float


@dataclass(frozen=True)
class OrderBook:
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    ts: datetime


@dataclass(frozen=True)
class Candle:
    symbol: str
    interval: Literal["15m", "30m", "1h", "4h"]
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Position:
    symbol: str
    qty: float
    entry_price: float
    leverage: Optional[float] = None
    side: Literal["long", "short", "flat"] = "flat"


@dataclass(frozen=True)
class Balance:
    asset: str
    free: float
    locked: float = 0.0


@runtime_checkable
class IExchangePublic(Protocol):
    """Маркет-дані: тикери, книги, трейди, свічки."""

    async def get_ticker(self, symbol: str) -> Ticker: ...
    async def get_order_book(self, symbol: str, depth: int = 50) -> OrderBook: ...
    async def get_candles(
        self, symbol: str, interval: Literal["15m", "30m", "1h", "4h"], limit: int = 200
    ) -> List[Candle]: ...


@runtime_checkable
class ITradingClient(Protocol):
    """Торгівля: створення/скасування ордерів, читання статусів/позицій."""

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
    ) -> Dict[str, Any]: ...
    async def cancel_order(
        self, symbol: str, order_id: str, market: MarketType = "spot"
    ) -> Dict[str, Any]: ...
    async def get_positions(self, symbols: Optional[Iterable[str]] = None) -> List[Position]: ...
    async def set_leverage(self, symbol: str, leverage: float) -> None: ...


@runtime_checkable
class IAccountClient(Protocol):
    """Акаунтинг: баланси, комісії тощо."""

    async def get_balances(self, assets: Optional[Iterable[str]] = None) -> List[Balance]: ...
    async def get_fees(self) -> Dict[str, Any]: ...


@runtime_checkable
class IExchangeClient(Protocol):
    """Фасад конкретної біржі, який агрегує публічний/трейдинг/акаунт."""

    public: IExchangePublic
    trading: ITradingClient
    account: IAccountClient
