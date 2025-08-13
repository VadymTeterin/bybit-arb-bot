# src/core/cache.py
from __future__ import annotations

import asyncio
from time import time
from typing import Dict, Optional, Tuple


class QuoteCache:
    """
    Потокобезпечний кеш останніх котирувань.
    Зберігає: symbol -> {spot, linear_mark, ts}
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._data: Dict[str, Dict[str, float]] = {}

    async def update(
        self,
        symbol: str,
        *,
        spot: Optional[float] = None,
        linear_mark: Optional[float] = None,
        ts: Optional[float] = None,
    ) -> None:
        if ts is None:
            ts = time()
        async with self._lock:
            row = self._data.setdefault(
                symbol, {"spot": float("nan"), "linear_mark": float("nan"), "ts": 0.0}
            )
            if spot is not None:
                row["spot"] = float(spot)
            if linear_mark is not None:
                row["linear_mark"] = float(linear_mark)
            row["ts"] = float(ts)

    async def snapshot(self) -> Dict[str, Tuple[float, float, float]]:
        async with self._lock:
            return {k: (v["spot"], v["linear_mark"], v["ts"]) for k, v in self._data.items()}
