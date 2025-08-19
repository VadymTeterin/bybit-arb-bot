# src/ws/normalizers/bybit_v5.py
"""Bybit v5 WebSocket normalizer to a single internal event format.

Output (dict):
    {
        "exchange": "BYBIT",
        "channel": <"ticker" | "trade" | "orderbook" | "kline" | "liquidation" | "other">,
        "symbol": "BTCUSDT",
        "event": <"snapshot" | "delta" | "subscribed" | "pong" | "unknown">,
        "ts_ms": 1700000000000,  # message ts in ms if available, else now
        "data": <payload-specific dict>,
    }

This module is intentionally dependency-free so it can be used from any WS client/bridge.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

BYBIT = "BYBIT"


@dataclass
class NormalizedEvent:
    exchange: str
    channel: str
    symbol: str
    event: str
    ts_ms: int
    data: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "channel": self.channel,
            "symbol": self.symbol,
            "event": self.event,
            "ts_ms": self.ts_ms,
            "data": self.data,
        }


def _now_ms() -> int:
    return int(time.time() * 1000)


def _parse_topic(topic: str) -> Tuple[str, str]:
    """Parse Bybit v5 topic into (channel, symbol).

    Examples:
        'tickers.BTCUSDT' -> ('ticker', 'BTCUSDT')
        'publicTrade.BTCUSDT' -> ('trade', 'BTCUSDT')
        'orderbook.1.BTCUSDT' -> ('orderbook', 'BTCUSDT')
        'kline.1.BTCUSDT' -> ('kline', 'BTCUSDT')
    """
    if not topic or "." not in topic:
        return ("other", "")
    parts = topic.split(".")
    head = parts[0]

    mapping = {
        "tickers": "ticker",
        "publicTrade": "trade",
        "orderbook": "orderbook",
        "kline": "kline",
        "liquidation": "liquidation",
    }
    channel = mapping.get(head, "other")
    # IMPORTANT: for unknown topics we must NOT attempt to parse symbol; tests expect empty symbol
    symbol = parts[-1] if (channel != "other" and len(parts) >= 2) else ""
    return (channel, symbol)


def _event_type(raw: Dict[str, Any]) -> str:
    # Prefer explicit type field if present
    evt = str(raw.get("type", "")).lower()
    if evt in {"snapshot", "delta"}:
        return evt
    # Subscription acks
    if raw.get("success") is True or raw.get("ret_msg") in {"OK", "SUCCESS"}:
        return "subscribed"
    # Heartbeat handling (pong)
    op = str(raw.get("op", "")).lower()
    if op == "pong" or raw.get("event") == "pong":
        return "pong"
    return "unknown"


def _ts_ms(raw: Dict[str, Any]) -> int:
    # Bybit often provides 'ts' or 'T' fields in ms; fall back to now.
    for key in ("ts", "T", "time", "sent_ts"):
        val = raw.get(key)
        if isinstance(val, (int, float)):
            return int(val)
    return _now_ms()


def normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single Bybit WS message.

    The function is resilient to minor schema differences between channels.
    """
    if not isinstance(raw, dict):
        raise TypeError("raw must be a dict")

    topic = str(raw.get("topic", ""))
    channel, symbol = _parse_topic(topic)
    evt = _event_type(raw)
    ts = _ts_ms(raw)

    # Data extraction varies by channel
    payload = raw.get("data", {})

    if channel == "ticker":
        # 'data' may be list with a single dict or a dict
        if isinstance(payload, list) and payload:
            payload = payload[0]
        out = {
            "last_price": _safe_float(payload.get("lastPrice")),
            "index_price": _safe_float(payload.get("indexPrice")),
            "mark_price": _safe_float(payload.get("markPrice")),
            "open_interest": _safe_float(payload.get("openInterest")),
            "turnover_24h": _safe_float(payload.get("turnover24h")),
            "volume_24h": _safe_float(payload.get("volume24h")),
        }
    elif channel == "trade":
        # 'data' is typically a list of trades; take them all
        trades = []
        for t in payload if isinstance(payload, list) else []:
            trades.append(
                {
                    "price": _safe_float(t.get("p")) or _safe_float(t.get("price")),
                    "qty": _safe_float(t.get("v")) or _safe_float(t.get("qty")),
                    "side": (
                        "sell" if (t.get("m") is True) else "buy"
                    ),  # Bybit: m=True means taker is sell
                    "trade_id": str(t.get("i") or t.get("tradeId") or ""),
                    "ts_ms": int(t.get("T") or t.get("ts") or ts),
                }
            )
        out = {"trades": trades}
    elif channel == "orderbook":
        # Payload may be {"a": [[px,qty],...], "b": [[px,qty],...]} or a list of deltas
        asks = []
        bids = []
        if isinstance(payload, dict):
            for row in payload.get("a", []) or []:
                asks.append(_ab_row(row))
            for row in payload.get("b", []) or []:
                bids.append(_ab_row(row))
        out = {"asks": asks, "bids": bids}
    else:
        out = payload if isinstance(payload, dict) else {"raw": payload}

    normalized = NormalizedEvent(
        exchange=BYBIT,
        channel=channel,
        symbol=symbol,
        event=evt,
        ts_ms=ts,
        data=out,
    )
    return normalized.as_dict()


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _ab_row(row: Any) -> Dict[str, Optional[float]]:
    # Accept [price, qty] or {"price":..., "qty":...}
    if isinstance(row, (list, tuple)) and len(row) >= 2:
        return {"price": _safe_float(row[0]), "qty": _safe_float(row[1])}
    if isinstance(row, dict):
        return {
            "price": _safe_float(row.get("price")),
            "qty": _safe_float(row.get("qty")),
        }
    return {"price": None, "qty": None}
