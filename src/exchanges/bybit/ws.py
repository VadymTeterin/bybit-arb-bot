# src/exchanges/bybit/ws.py
# English-only comments per project rules.
from __future__ import annotations

import asyncio
import json
import random
from typing import (
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Protocol,
)

import aiohttp

# Reconnect/backoff helpers (project-wide, exchange-agnostic)
from src.ws.reconnect import ReconnectPolicy

# Health metrics (optional singleton). If unavailable, we no-op.
try:
    from src.ws.health import MetricsRegistry  # type: ignore
except Exception:  # pragma: no cover
    MetricsRegistry = None  # type: ignore


# ---- Logger (loguru if available; falls back to stdlib logging) ----
class _LoggerLike(Protocol):
    def debug(self, msg: str, *args, **kwargs) -> None: ...
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...


try:
    from loguru import logger as _loguru_logger  # type: ignore

    logger: _LoggerLike = _loguru_logger  # structural type compatible
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger("bybit.ws")


# ---- Legacy-compatible exponential backoff with jitter --------------
def exp_backoff_with_jitter(
    attempt: int,
    *,
    base: float = 0.5,
    factor: float = 2.0,
    cap: Optional[float] = None,
    max_delay: Optional[float] = None,
    jitter: float = 0.1,
) -> float:
    """
    Legacy-compatible exponential backoff with jitter.

    - Tests may call with 'cap=' -> accept as alias for max delay.
    - attempt is 1-based: attempt=1 -> base, attempt=2 -> base*factor, ...
    - Never overshoot the unclamped target after jitter (upper clamp).
    """
    # Resolve cap/max_delay to a single upper bound
    if cap is not None and max_delay is not None:
        max_d = min(cap, max_delay)
    else:
        max_d = cap if cap is not None else (max_delay if max_delay is not None else float("inf"))

    k = max(0, int(attempt) - 1)  # 1-based -> 0-based exponent
    nominal = base * (factor**k)
    clipped = min(max_d, nominal)

    span = max(0.0, jitter) * clipped
    jittered = clipped + random.uniform(-span, span)

    # do not exceed unclamped target after jitter
    delay = min(clipped, jittered)
    return max(0.0, delay)


# ---- Parsing helpers -------------------------------------------------
def _to_float(v: object, default: Optional[float] = None) -> Optional[float]:
    """Try to convert arbitrary value to float; return default if impossible."""
    if v is None:
        return default
    try:
        return float(v)  # fast path (floats/ints/str-numeric)
    except Exception:
        try:
            return float(str(v).strip())
        except Exception:
            return default


def _from_scaled(v: object, scale: int) -> Optional[float]:
    """
    Convert scaled integers (E4/E8 etc.) to float.
    Example: 345678901 with scale=4 => 34567.8901
    """
    f = _to_float(v)
    return None if f is None else f / (10**scale)


def _infer_symbol_from_topic(topic: str) -> Optional[str]:
    # Bybit v5 topics look like "tickers.BTCUSDT" or just "tickers"
    if not topic:
        return None
    if "." in topic:
        return topic.split(".", 1)[1].strip().upper() or None
    return None


# ---- Public parser API ----------------------------------------------
def iter_ticker_entries(message: Dict) -> Iterator[Dict]:
    """
    Normalize Bybit v5 'tickers' WS message into rows:
      { 'symbol': str, 'last': float|None, 'mark': float|None, 'index': float|None }

    Supports:
      - 'data' as dict (single row) or list of dicts
      - scaled numeric fields E4/E8 (e.g., lastPriceE8, markPriceE4, indexPriceE8)
      - symbol fallback from 'topic' when missing in 'data'
      - legacy fields like 'last' or 'lastPriceLatest'
    """
    topic = str(message.get("topic") or "").strip()
    data = message.get("data")
    if data is None:
        return iter(())  # empty iterator

    if isinstance(data, dict):
        arr: List[Dict] = [data]
    elif isinstance(data, list):
        arr = [x for x in data if isinstance(x, dict)]
    else:
        return iter(())

    out_rows: List[Dict] = []
    for item in arr:
        symbol = item.get("symbol") or _infer_symbol_from_topic(topic) or ""
        symbol = str(symbol).upper()

        # last price: plain or scaled or legacy
        last = (
            _to_float(item.get("lastPrice"))
            or _from_scaled(item.get("lastPriceE8"), 8)
            or _from_scaled(item.get("lastPriceE4"), 4)
            or _to_float(item.get("last"))
            or _to_float(item.get("lastPriceLatest"))
        )

        # mark price (derivatives): plain or scaled
        mark = (
            _to_float(item.get("markPrice"))
            or _from_scaled(item.get("markPriceE8"), 8)
            or _from_scaled(item.get("markPriceE4"), 4)
        )

        # index price: plain or scaled
        index = (
            _to_float(item.get("indexPrice"))
            or _from_scaled(item.get("indexPriceE8"), 8)
            or _from_scaled(item.get("indexPriceE4"), 4)
        )

        # Always include expected keys; values may be None
        out_rows.append({"symbol": symbol, "last": last, "mark": mark, "index": index})

    return iter(out_rows)


# ---- Public WS client -----------------------------------------------
class BybitPublicWS:
    """
    Minimal Bybit v5 public WS client (spot/linear).
    - Connects to given URL
    - Subscribes to topics list (e.g. ["tickers.BTCUSDT","tickers.ETHUSDT"] or ["tickers"])
    - Calls on_message for every incoming JSON
    - Uses ReconnectPolicy (exponential backoff with jitter) between reconnects
    - Optionally increments WS health metrics (SPOT/LINEAR) on each non-ping payload
    """

    def __init__(
        self,
        url: str,
        topics: Iterable[str],
        *,
        metrics_source: Optional[str] = None,  # "SPOT" | "LINEAR" | None
    ) -> None:
        self.url = url
        self.topics = list(topics)
        self._stop = asyncio.Event()
        self._session: Optional[aiohttp.ClientSession] = None
        self._metrics_source = (metrics_source or "").upper() or None

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        if not self.topics:
            return
        msg = {"op": "subscribe", "args": self.topics}
        await ws.send_str(json.dumps(msg))
        logger.debug(f"WS subscribe -> {msg}")

    async def stop(self) -> None:
        self._stop.set()

    async def run(
        self,
        on_message: Callable[[dict], Awaitable[None]],
        *,
        heartbeat: int = 30,
    ) -> None:
        """
        Main loop with auto-reconnect using ReconnectPolicy.
        on_message receives parsed JSON (dict).
        """
        self._stop.clear()
        policy = ReconnectPolicy()  # base=0.5, factor=2.0, max=30.0 by default

        async with aiohttp.ClientSession() as session:
            self._session = session
            while not self._stop.is_set():
                try:
                    async with session.ws_connect(self.url, heartbeat=heartbeat) as ws:
                        logger.info(f"WS connected: {self.url}")
                        policy.reset()  # successful connect
                        await self._subscribe(ws)

                        async for msg in ws:
                            if self._stop.is_set():
                                break

                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    payload = json.loads(msg.data)
                                except Exception:
                                    logger.warning("WS non-JSON text frame")
                                    continue

                                # reset backoff on any valid message
                                policy.reset()

                                # Skip pongs/keepalives that some Bybit edges send as JSON
                                if isinstance(payload, dict) and (
                                    str(payload.get("op", "")).lower() == "pong"
                                    or str(payload.get("event", "")).lower() == "pong"
                                ):
                                    continue

                                # Health metrics (optional)
                                try:
                                    if MetricsRegistry and self._metrics_source:
                                        reg = MetricsRegistry.get()
                                        if self._metrics_source == "SPOT":
                                            reg.inc_spot(1)
                                        elif self._metrics_source == "LINEAR":
                                            reg.inc_linear(1)
                                except Exception:
                                    # metrics must never break the WS loop
                                    pass

                                await on_message(payload)

                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                # Bybit public streams are text JSON; ignore binary frames
                                continue
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WS error: {ws.exception()}")
                                break
                            elif msg.type in (
                                aiohttp.WSMsgType.CLOSED,
                                aiohttp.WSMsgType.CLOSING,
                            ):
                                break

                except Exception as e:
                    # Exponential backoff between reconnect attempts
                    delay = policy.next_delay()
                    logger.warning(f"WS reconnect in {delay:.2f}s after error: {e!r}")
                    await asyncio.sleep(delay)

        logger.info("WS stopped")


# Backward-compatible alias
BybitWS = BybitPublicWS
