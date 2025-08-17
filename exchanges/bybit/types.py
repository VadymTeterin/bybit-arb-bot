# exchanges/bybit/types.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional


@dataclass(frozen=True)
class BybitCredentials:
    api_key: str
    api_secret: str


@dataclass(frozen=True)
class BybitConfig:
    enabled: bool = False
    ws_enabled: bool = False
    perp_enabled: bool = False
    recv_window_ms: int = 5000
    base_url_public: str = "https://api.bybit.com"
    base_url_private: str = "https://api.bybit.com"
    testnet: bool = False
    extra: Optional[Dict[str, Any]] = None


Interval = Literal["15m", "30m", "1h", "4h"]
MarketType = Literal["spot", "perp", "margin"]
