# tests/bybit/test_http_retry.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import pytest

from exchanges.bybit._http import HTTPClient


class _FakeResp:
    def __init__(self, status_code: int, payload: Dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Dict[str, Any]:
        return self._payload

    async def aclose(self) -> None:  # для сумісності, хоча не використовується тут
        return None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeClient:
    """Імітує послідовність відповідей на .request()."""

    def __init__(self, sequence: list[_FakeResp]):
        self.sequence = sequence
        self.calls = 0

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> _FakeResp:
        idx = min(self.calls, len(self.sequence) - 1)
        self.calls += 1
        await asyncio.sleep(0)  # віддати керування циклу подій
        return self.sequence[idx]

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_retry_on_status_429():
    # 1-й виклик: 429, 2-й: успіх
    seq = [
        _FakeResp(429, {"retCode": 0, "result": {}}),
        _FakeResp(200, {"retCode": 0, "result": {"ok": True}}),
    ]
    client = HTTPClient(
        base_url="http://fake",
        client=_FakeClient(seq),
        max_retries=2,
        backoff_factor=0.0,
    )
    data = await client.get("/v5/market/tickers", params={})
    assert data.get("result", {}).get("ok") is True


@pytest.mark.asyncio
async def test_retry_on_rate_limit_retcode():
    # 1-й виклик: retCode rate-limit, 2-й: успіх
    seq = [
        _FakeResp(200, {"retCode": 10016, "retMsg": "rate limit"}),
        _FakeResp(200, {"retCode": 0, "result": {"ok": True}}),
    ]
    client = HTTPClient(
        base_url="http://fake",
        client=_FakeClient(seq),
        max_retries=2,
        backoff_factor=0.0,
    )
    data = await client.get("/v5/market/tickers", params={})
    assert data.get("result", {}).get("ok") is True
