# exchanges/bybit/_http.py
from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, Optional, Protocol

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None  # Легка залежність

from .auth import canonical_json, canonical_query, sign_v5
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
            raise ImportError("httpx не встановлено. Додай пакет 'httpx' у requirements.")
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
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            if self._limiter is not None:
                await self._limiter.acquire(1)
            try:
                req_kwargs: Dict[str, Any] = {"params": params, "json": json}
                # 👇 передаємо headers тільки якщо він заданий
                if headers is not None:
                    req_kwargs["headers"] = headers

                resp = await self._client.request(method, path, **req_kwargs)
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
                    if self._is_rate_limit_retcode(data["retCode"]) and attempt < self._max_retries:
                        await self._sleep_backoff(attempt)
                        continue
                    raise map_error(data.get("retCode"), data.get("retMsg", "unknown error"))
                return data

            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self._max_retries:
                    await self._sleep_backoff(attempt)
                    continue
                raise

        if last_exc is not None:
            raise last_exc
        return {}

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return await self._request("GET", path, params=params, json=None, headers=headers)

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return await self._request("POST", path, params=None, json=json, headers=headers)

    async def close(self) -> None:
        close = getattr(self._client, "aclose", None)
        if callable(close):
            await close()


class SignedHTTPClient(HTTPClient):
    """
    Підписує запити за схемою v5: HMAC-SHA256(secret, ts + key + recvWindow + body)
    - для GET body = canonical_query(params)
    - для POST body = canonical_json(json)
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_secret: str,
        recv_window_ms: int = 5000,
        timeout: float = 10.0,
        limiter: Optional[_RateLimiterProto] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        client: Any = None,
        now_ms: Optional[Callable[[], int]] = None,  # для тестів
    ):
        super().__init__(
            base_url,
            timeout=timeout,
            limiter=limiter,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            client=client,
        )
        self._api_key = api_key
        self._api_secret = api_secret
        self._recv_window = recv_window_ms
        self._now_ms = now_ms or (lambda: int(time.time() * 1000))

    def _common_headers(
        self, timestamp_ms: str, sign: str, content_type_json: bool = False
    ) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-SIGN": sign,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": timestamp_ms,
            "X-BAPI-RECV-WINDOW": str(self._recv_window),
        }
        if content_type_json:
            headers["Content-Type"] = "application/json"
        return headers

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        ts = str(self._now_ms())
        body_str = canonical_query(params)
        sign = sign_v5(self._api_key, self._api_secret, self._recv_window, ts, body_str)
        hdrs = self._common_headers(ts, sign)
        if headers:
            hdrs.update(headers)
        return await super().get(path, params=params, headers=hdrs)

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        ts = str(self._now_ms())
        body_str = canonical_json(json)
        sign = sign_v5(self._api_key, self._api_secret, self._recv_window, ts, body_str)
        hdrs = self._common_headers(ts, sign, content_type_json=True)
        if headers:
            hdrs.update(headers)
        return await super().post(path, json=json, headers=hdrs)
