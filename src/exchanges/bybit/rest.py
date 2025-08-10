from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

BASE_URL = "https://api.bybit.com"


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


class BybitRest:
    """
    Простий клієнт для Bybit REST v5 (публічні ендпоінти).
    Дає зручні мапи для SPOT та LINEAR з уже підготовленими числовими полями.
    """

    def __init__(self, base_url: str = BASE_URL, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict:
        url = f"{self.base_url}{path}"
        r = requests.get(url, params=params or {}, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        # Bybit v5: retCode == 0 => OK
        if isinstance(data, dict) and data.get("retCode") not in (0, "0", None):
            raise RuntimeError(f"Bybit error: {data}")
        return data

    # ---- час сервера ----
    def get_server_time(self) -> Dict:
        return self._get("/v5/market/time")

    # ---- сирі тікери ----
    def get_tickers(self, category: str) -> List[Dict]:
        data = self._get("/v5/market/tickers", {"category": category})
        return data.get("result", {}).get("list", []) or []

    # ---- допоміжне: вибір ціни ----
    @staticmethod
    def _price_for_spot(row: Dict[str, Any]) -> float:
        # для spot — беремо lastPrice (або lastPriceLatest як запасний)
        return _to_float(row.get("lastPrice") or row.get("lastPriceLatest"))

    @staticmethod
    def _price_for_linear(row: Dict[str, Any]) -> float:
        # для linear — пріоритет markPrice; якщо нема, fallback на lastPrice/lastPriceLatest
        return _to_float(row.get("markPrice") or row.get("lastPrice") or row.get("lastPriceLatest"))

    @staticmethod
    def _turnover_usd(row: Dict[str, Any]) -> float:
        # у різних категорій поле може називатись turnover24h або turnoverUsd
        return _to_float(row.get("turnover24h") or row.get("turnoverUsd"))

    # ---- агреговані мапи ----
    def get_spot_map(self) -> Dict[str, Dict[str, float]]:
        """
        Повертає {symbol: {price, turnover_usd}} для SPOT (price = lastPrice).
        """
        rows = self.get_tickers("spot")
        out: Dict[str, Dict[str, float]] = {}
        for r in rows:
            sym = r.get("symbol")
            if not sym:
                continue
            out[sym] = {
                "price": self._price_for_spot(r),
                "turnover_usd": self._turnover_usd(r),
            }
        return out

    def get_linear_map(self) -> Dict[str, Dict[str, float]]:
        """
        Повертає {symbol: {price, turnover_usd}} для USDT‑перпетуалів (LINEAR).
        Для ціни використовуємо markPrice, якщо він є (інакше lastPrice).
        """
        rows = self.get_tickers("linear")
        out: Dict[str, Dict[str, float]] = {}
        for r in rows:
            sym = r.get("symbol")
            if not sym:
                continue
            out[sym] = {
                "price": self._price_for_linear(r),
                "turnover_usd": self._turnover_usd(r),
            }
        return out
