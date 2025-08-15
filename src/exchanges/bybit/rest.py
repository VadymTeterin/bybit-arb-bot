# src/exchanges/bybit/rest.py
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import requests

BASE_URL = "https://api.bybit.com"


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        try:
            return float(str(x).strip())
        except Exception:
            return default


class BybitRest:
    """
    Lightweight REST client for Bybit v5 market endpoints (public only).
    Provides helpers to build normalized maps for spot/linear tickers.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 10.0,
        ob_ttl_sec: float = 0.8,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._ob_cache: Dict[Tuple[str, str, int], Tuple[float, Dict]] = {}
        self._ob_ttl_sec = float(ob_ttl_sec)

    # ---- low-level ----
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        url = f"{self.base_url}{path}"
        resp = self._session.get(url, params=params or {}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ---- general ----
    def get_server_time(self) -> Dict:
        return self._get("/v5/market/time")

    # ---- raw tickers ----
    def get_tickers(self, category: str) -> List[Dict]:
        data = self._get("/v5/market/tickers", {"category": category})
        return data.get("result", {}).get("list", []) or []

    # ---- helpers: price/turnover ----
    @staticmethod
    def _price_for_spot(row: Dict[str, Any]) -> float:
        # for spot — prefer lastPrice; fallback to lastPriceLatest
        return _to_float(row.get("lastPrice") or row.get("lastPriceLatest"))

    @staticmethod
    def _price_for_linear(row: Dict[str, Any]) -> float:
        # for linear — prefer markPrice; fallback to lastPrice/lastPriceLatest
        return _to_float(
            row.get("markPrice") or row.get("lastPrice") or row.get("lastPriceLatest")
        )

    @staticmethod
    def _turnover_usd(row: Dict[str, Any]) -> float:
        # can be turnover24h or turnoverUsd depending on category
        return _to_float(row.get("turnover24h") or row.get("turnoverUsd"))

    # ---- aggregated maps ----
    def build_spot_map(self, rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for r in rows:
            sym = str(r.get("symbol") or "").upper()
            if not sym:
                continue
            out[sym] = {
                "price": self._price_for_spot(r),
                "turnover_usd": self._turnover_usd(r),
            }
        return out

    def build_linear_map(
        self, rows: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for r in rows:
            sym = str(r.get("symbol") or "").upper()
            if not sym:
                continue
            out[sym] = {
                "price": self._price_for_linear(r),
                "turnover_usd": self._turnover_usd(r),
            }
        return out

    # ---- orderbook ----
    def get_orderbook(self, category: str, symbol: str, limit: int = 200) -> Dict:
        """
        Fetch orderbook for SPOT or LINEAR. Cached for _ob_ttl_sec seconds to avoid rate limits.
        """
        key = (category, symbol, limit)
        now = time.time()
        if key in self._ob_cache:
            ts, cached = self._ob_cache[key]
            if now - ts <= self._ob_ttl_sec:
                return cached
        data = self._get(
            "/v5/market/orderbook",
            {"category": category, "symbol": symbol, "limit": int(limit)},
        )
        ob = data.get("result", {}) or {}
        self._ob_cache[key] = (now, ob)
        return ob
