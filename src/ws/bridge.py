# src/ws/bridge.py
from __future__ import annotations

import time
from typing import Any, Dict

from src.ws.multiplexer import WsEvent, WSMultiplexer


def publish_bybit_ticker(
    mux: WSMultiplexer,
    source: str,
    item: Dict[str, Any],
    *,
    channel: str = "tickers",
    ts: float | None = None,
) -> int:
    """
    Minimal bridge: adapt Bybit ticker dict -> WsEvent and publish to mux.
    Returns number of handlers fired.
    """
    if mux is None or item is None:
        return 0
    sym = (item.get("symbol") or "").upper()
    if not sym:
        return 0
    evt = WsEvent(
        source=source,
        channel=channel,
        symbol=sym,
        payload=item,
        ts=(ts if ts is not None else time.time()),
    )
    return mux.publish(evt)
