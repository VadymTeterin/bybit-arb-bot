# tests/bybit/test_private_headers.py
from __future__ import annotations

from typing import Any

import pytest

from exchanges.bybit._http import SignedHTTPClient


class _FakeResp:
    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload

    async def aclose(self) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _CaptureClient:
    def __init__(self):
        self.last_headers: dict[str, str] = {}
        self.last_params: dict[str, Any] | None = None
        self.last_json: dict[str, Any] | None = None

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.last_params = params
        self.last_json = json
        self.last_headers = headers or {}
        return _FakeResp(200, {"retCode": 0, "result": {"ok": True}})

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_signed_get_headers_present():
    cap = _CaptureClient()
    client = SignedHTTPClient(
        base_url="http://fake",
        api_key="key",
        api_secret="secret",
        recv_window_ms=5000,
        client=cap,
        now_ms=lambda: 1700000000000,
    )
    _ = await client.get("/v5/private/test", params={"a": 1, "b": 2})
    h = cap.last_headers
    assert h.get("X-BAPI-API-KEY") == "key"
    assert h.get("X-BAPI-SIGN-TYPE") == "2"
    assert h.get("X-BAPI-TIMESTAMP") == "1700000000000"
    assert h.get("X-BAPI-RECV-WINDOW") == "5000"
    assert "X-BAPI-SIGN" in h


@pytest.mark.asyncio
async def test_signed_post_headers_present():
    cap = _CaptureClient()
    client = SignedHTTPClient(
        base_url="http://fake",
        api_key="key",
        api_secret="secret",
        recv_window_ms=5000,
        client=cap,
        now_ms=lambda: 1700000000000,
    )
    _ = await client.post("/v5/private/test", json={"x": 1})
    h = cap.last_headers
    assert h.get("Content-Type") == "application/json"
    assert h.get("X-BAPI-API-KEY") == "key"
    assert h.get("X-BAPI-SIGN-TYPE") == "2"
    assert h.get("X-BAPI-TIMESTAMP") == "1700000000000"
    assert h.get("X-BAPI-RECV-WINDOW") == "5000"
    assert "X-BAPI-SIGN" in h
