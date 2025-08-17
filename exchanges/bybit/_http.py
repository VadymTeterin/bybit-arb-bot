# exchanges/bybit/_http.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Protocol

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None  # Легка залежність

from .errors import map_error


class _RateLimiterProto(Protocol):
    async def acquire(self, tokens: int = 1) -> None: ...


class HTTPClient:
    """
    Обгортка над httpx.AsyncClient з експоненційними ретраями та опціональним rate-лімітером.
    - ретраї по 429/5xx/мережевих помилках
    - ретраї по BYBIT retCode, що відповідають rate-limit
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        limiter: Optional[_RateLimiterProto] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        client: Any = None,  # для тестів можна передати фейковий клієнт із методом .request()
    ):
        if httpx is None and client is None:
            raise ImportError(
                "httpx не встановлено. Додай пакет 'httpx' у requirements."
            )
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._limiter = limiter
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    async def _sleep_backoff(self, attempt: int) -> None:
        delay = self._backoff_factor * (2**attempt)
        await asyncio.sleep(delay)

    def _should_retry_status(self, status_code: int) -> bool:
        return status_code == 429 or status_code >= 500

    def _is_rate_limit_retcode(self, ret_code: Any) -> bool:
        code = str(ret_code)
        # Типові rate-limit коди BYBIT
        return code in {"10016", "10017", "10018"}

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            if self._limiter is not None:
                await self._limiter.acquire(1)
            try:
                resp = await self._client.request(
                    method, path, params=params, json=json
                )
                status = getattr(resp, "status_code", 200)
                # 429/5xx — повтор
                if self._should_retry_status(status):
                    if attempt < self._max_retries:
                        await self._sleep_backoff(attempt)
                        continue
                    resp.raise_for_status()

                # 4xx (окрім 429) — одразу піднімаємо
                if status >= 400 and status != 429:
                    resp.raise_for_status()

                data: Dict[str, Any] = resp.json() if hasattr(resp, "json") else {}
                # BYBIT retCode != 0
                if "retCode" in data and int(data["retCode"]) != 0:
                    if (
                        self._is_rate_limit_retcode(data["retCode"])
                        and attempt < self._max_retries
                    ):
                        await self._sleep_backoff(attempt)
                        continue
                    raise map_error(
                        data.get("retCode"), data.get("retMsg", "unknown error")
                    )
                return data

            except (  # мережеві помилки httpx — ретраї
                Exception
            ) as exc:
                # Якщо це httpx і можна дізнатись статус — вже обробили вище
                last_exc = exc
                if attempt < self._max_retries:
                    await self._sleep_backoff(attempt)
                    continue
                raise

        # Якщо цикл завершився без return/raise у середині
        if last_exc is not None:
            raise last_exc
        return {}

    async def get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return await self._request("GET", path, params=params, json=None)

    async def post(
        self, path: str, json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return await self._request("POST", path, params=None, json=json)

    async def close(self) -> None:
        # У тестах фейковий клієнт може не мати aclose
        close = getattr(self._client, "aclose", None)
        if callable(close):
            await close()
