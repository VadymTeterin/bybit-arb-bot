# exchanges/bybit/_http.py
from __future__ import annotations

from typing import Any, Dict, Optional

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None  # Легка залежність


class HTTPClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        if httpx is None:
            raise ImportError(
                "httpx не встановлено. Додай пакет 'httpx' у requirements."
            )
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def post(
        self, path: str, json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = await self._client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
