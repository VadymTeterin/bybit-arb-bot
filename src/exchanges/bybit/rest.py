from __future__ import annotations

from typing import Dict, Optional

import requests


BASE_URL = "https://api.bybit.com"


class BybitRest:
    """
    Простий клієнт для Bybit REST v5 (публічні ендпоінти).
    """

    def __init__(self, base_url: str = BASE_URL, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict:
        url = f"{self.base_url}{path}"
        r = requests.get(url, params=params or {}, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        # Bybit v5 повертає retCode=0 при успіху
        if isinstance(data, dict) and data.get("retCode") not in (0, "0", None):
            raise RuntimeError(f"Bybit error: {data}")
        return data

    # ---- час сервера ----
    def get_server_time(self) -> Dict:
        """
        /v5/market/time — повертає {'retCode':0, 'result':{'timeSecond': '...', 'timeNano': '...'}}
        """
        return self._get("/v5/market/time")

    # ---- 24h тікери для категорії (наприклад, 'spot') ----
    def get_tickers(self, category: str = "spot") -> Dict:
        """
        /v5/market/tickers?category=spot — список інструментів із 24h статистикою.
        """
        return self._get("/v5/market/tickers", {"category": category})
