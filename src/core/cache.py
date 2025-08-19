# src/core/cache.py
from __future__ import annotations

import asyncio
import math
from time import time
from typing import Dict, List, Optional, Tuple


class QuoteCache:
    """
    Асинхронний потокобезпечний кеш котирувань та мета-даних.
    Зберігає для кожного символу:
      - spot: остання ціна споту
      - linear_mark: остання mark ціна ф'ючерса (linear)
      - basis_pct: (linear_mark - spot) / spot * 100, якщо обидві ціни відомі
      - ts_spot / ts_linear / ts_basis: таймстемпи останніх оновлень
      - vol24h_usd: останній відомий 24h turnover у $, для фільтра по ліквідності

    ВАЖЛИВО: метод snapshot() зберігає зворотну сумісність і повертає
    саме 3‑кортеж (spot, linear_mark, ts), як очікують наявні тести.
    Розширені дані доступні через snapshot_extended().
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._data: Dict[str, Dict[str, float]] = {}
        self._vol24h: Dict[str, float] = {}

    async def update(
        self,
        symbol: str,
        *,
        spot: Optional[float] = None,
        linear_mark: Optional[float] = None,
        ts: Optional[float] = None,
    ) -> float:
        """
        Оновлює spot/linear_mark. Повертає поточний basis_pct (або NaN, якщо його ще не можна порахувати).
        """
        if ts is None:
            ts = time()
        async with self._lock:
            row = self._data.setdefault(
                symbol,
                {
                    "spot": math.nan,
                    "linear_mark": math.nan,
                    "basis_pct": math.nan,
                    "ts_spot": 0.0,
                    "ts_linear": 0.0,
                    "ts_basis": 0.0,
                },
            )
            if spot is not None:
                row["spot"] = float(spot)
                row["ts_spot"] = float(ts)
            if linear_mark is not None:
                row["linear_mark"] = float(linear_mark)
                row["ts_linear"] = float(ts)

            # перерахунок basis, якщо можливо
            if row["spot"] and row["linear_mark"] and row["spot"] > 0:
                row["basis_pct"] = (
                    (row["linear_mark"] - row["spot"]) / row["spot"] * 100.0
                )
                row["ts_basis"] = float(ts)
            return row["basis_pct"]

    async def update_vol24h(self, symbol: str, vol_usd: Optional[float]) -> None:
        async with self._lock:
            if vol_usd is None:
                self._vol24h.pop(symbol, None)
            else:
                self._vol24h[symbol] = float(vol_usd)

    async def update_vol24h_bulk(self, vol_map: Dict[str, float]) -> None:
        async with self._lock:
            for k, v in vol_map.items():
                self._vol24h[k] = float(v)

    async def get_row(self, symbol: str) -> Dict[str, float]:
        async with self._lock:
            row = self._data.get(symbol, None)
            if row is None:
                return {
                    "spot": math.nan,
                    "linear_mark": math.nan,
                    "basis_pct": math.nan,
                    "ts_spot": 0.0,
                    "ts_linear": 0.0,
                    "ts_basis": 0.0,
                }
            return dict(row)

    async def snapshot(self) -> Dict[str, Tuple[float, float, float]]:
        """
        BACKWARD‑COMPAT: повертає {symbol: (spot, linear_mark, ts)}
        де ts = max(ts_spot, ts_linear, ts_basis).
        """
        async with self._lock:
            out: Dict[str, Tuple[float, float, float]] = {}
            for k, v in self._data.items():
                ts = max(
                    float(v.get("ts_spot", 0.0)),
                    float(v.get("ts_linear", 0.0)),
                    float(v.get("ts_basis", 0.0)),
                )
                out[k] = (
                    float(v.get("spot", math.nan)),
                    float(v.get("linear_mark", math.nan)),
                    ts,
                )
            return out

    async def snapshot_extended(
        self,
    ) -> Dict[str, Tuple[float, float, float, float, float, float]]:
        """
        Розширена версія снапшоту: {symbol: (spot, linear_mark, basis_pct, ts_spot, ts_linear, ts_basis)}
        """
        async with self._lock:
            out: Dict[str, Tuple[float, float, float, float, float, float]] = {}
            for k, v in self._data.items():
                out[k] = (
                    float(v.get("spot", math.nan)),
                    float(v.get("linear_mark", math.nan)),
                    float(v.get("basis_pct", math.nan)),
                    float(v.get("ts_spot", 0.0)),
                    float(v.get("ts_linear", 0.0)),
                    float(v.get("ts_basis", 0.0)),
                )
            return out

    async def candidates(
        self,
        *,
        threshold_pct: float,
        min_price: float = 0.0,
        min_vol24h_usd: float = 0.0,
        allow: Optional[List[str]] = None,
        deny: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Повертає список (symbol, basis_pct), що проходять фільтри:
          - abs(basis_pct) >= threshold_pct
          - spot >= min_price
          - vol24h_usd >= min_vol24h_usd (якщо відоме)
          - allow/deny списки
        Список відсортовано за |basis_pct| спадаючим.
        """
        async with self._lock:
            rows = []
            allow_set = set(allow or [])
            deny_set = set(deny or [])
            for sym, v in self._data.items():
                if allow_set and sym not in allow_set:
                    continue
                if sym in deny_set:
                    continue
                spot = float(v.get("spot", math.nan))
                basis = float(v.get("basis_pct", math.nan))
                if math.isnan(spot) or math.isnan(basis):
                    continue
                if spot < float(min_price):
                    continue
                if abs(basis) < float(threshold_pct):
                    continue
                vol = self._vol24h.get(sym, None)
                if vol is not None and vol < float(min_vol24h_usd):
                    continue
                rows.append((sym, basis))
            rows.sort(key=lambda x: abs(x[1]), reverse=True)
            return rows
