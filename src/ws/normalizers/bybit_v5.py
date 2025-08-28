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
from typing import Any

BYBIT = "BYBIT"


@dataclass
class NormalizedEvent:
    exchange: str
    channel: str
    symbol: str
    event: str
    ts_ms: int
    data: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
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


def _parse_topic(topic: str) -> tuple[str, str]:
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
    # For unknown topics symbol stays empty to keep downstream logic simple
    symbol = parts[-1] if (channel != "other" and len(parts) >= 2) else ""
    return (channel, symbol)


def _event_type(raw: dict[str, Any]) -> str:
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


def _ts_ms(raw: dict[str, Any]) -> int:
    # Bybit often provides 'ts' or 'T' fields in ms; fall back to now.
    for key in ("ts", "T", "time", "sent_ts"):
        val = raw.get(key)
        if isinstance(val, (int, float)):
            return int(val)
    return _now_ms()


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
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
        out: dict[str, Any] = {
            "last_price": _safe_float(_get_first(payload, "lastPrice", "last_price")),
            "index_price": _safe_float(_get_first(payload, "indexPrice", "index_price")),
            "mark_price": _safe_float(_get_first(payload, "markPrice", "mark_price")),
            "open_interest": _safe_float(_get_first(payload, "openInterest", "open_interest")),
            "turnover_24h": _safe_float(_get_first(payload, "turnover24h")),
            "volume_24h": _safe_float(_get_first(payload, "volume24h")),
        }
    elif channel == "trade":
        # 'data' is typically a list of trades; take them all
        trades = []
        for t in payload if isinstance(payload, list) else []:
            trades.append(
                {
                    "price": _safe_float(t.get("p")) or _safe_float(t.get("price")),
                    "qty": _safe_float(t.get("v")) or _safe_float(t.get("qty")),
                    # Bybit: m=True means taker is sell
                    "side": "sell" if (t.get("m") is True) else "buy",
                    "trade_id": str(t.get("i") or t.get("tradeId") or ""),
                    "ts_ms": int(t.get("T") or t.get("ts") or ts),
                }
            )
        out = {"trades": trades}
    elif channel == "orderbook":
        # Payload may be {"a": [[px,qty],...], "b": [[px,qty],...]} or structured deltas
        asks = []
        bids = []
        if isinstance(payload, dict):
            for row in payload.get("a", []) or []:
                asks.append(_ab_row(row))
            for row in payload.get("b", []) or []:
                bids.append(_ab_row(row))
        out = {"asks": asks, "bids": bids}
    else:
        # kline/liquidation/other — keep as-is if dict, otherwise wrap as raw
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


def _get_first(d: Any, *keys: str) -> Any:
    """Return the first existing key from a dict-like payload."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d:
            return d[k]
    return None


def _safe_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _ab_row(row: Any) -> dict[str, float | None]:
    """Normalize an orderbook row.

    Accepts:
      - [price, qty]
      - {"price": ..., "qty": ...}
    """
    if isinstance(row, (list, tuple)) and len(row) >= 2:
        return {"price": _safe_float(row[0]), "qty": _safe_float(row[1])}
    if isinstance(row, dict):
        return {
            "price": _safe_float(row.get("price")),
            "qty": _safe_float(row.get("qty")),
        }
    return {"price": None, "qty": None}
