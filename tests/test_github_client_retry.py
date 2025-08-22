import time

import httpx
import pytest

from src.github.client import GitHubClient


class DummySleeper:
    """Helper to avoid real sleep in tests and capture delays."""

    def __init__(self) -> None:
        self.calls = []

    def __call__(self, delay: float) -> None:  # pragma: no cover - trivial
        self.calls.append(delay)


def make_response(status: int, json=None, headers=None):
    return httpx.Response(
        status_code=status,
        headers=headers or {},
        json=json if json is not None else {},
        request=httpx.Request("GET", "https://api.github.test/resource"),
    )


def test_retry_on_500_then_success():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return make_response(500)
        return make_response(200, json=[{"ok": True}])

    transport = httpx.MockTransport(handler)
    client = GitHubClient(client=httpx.Client(transport=transport))
    client._sleep = DummySleeper()  # avoid real sleep

    resp = client._request("GET", "/any")
    assert resp.status_code == 200
    assert calls["n"] == 2  # one retry occurred


def test_retry_on_429_respects_retry_after():
    calls = {"n": 0}
    sleeper = DummySleeper()

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return make_response(429, headers={"Retry-After": "0"})
        return make_response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = GitHubClient(client=httpx.Client(transport=transport))
    client._sleep = sleeper

    resp = client._request("GET", "/any")
    assert resp.status_code == 200
    # Ensure sleep was invoked at least once due to Retry-After
    assert len(sleeper.calls) >= 1


def test_rate_limit_reset_header_triggers_wait_then_succeeds(monkeypatch):
    now = int(time.time())
    sequence = [
        make_response(
            403,
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(now)},
        ),
        make_response(200, json={"ok": True}),
    ]
    calls = {"i": 0}
    sleeper = DummySleeper()

    def handler(request: httpx.Request) -> httpx.Response:
        idx = calls["i"]
        calls["i"] += 1
        return sequence[idx]

    transport = httpx.MockTransport(handler)
    client = GitHubClient(
        client=httpx.Client(transport=transport), max_retries=2, max_sleep_on_reset=1
    )
    client._sleep = sleeper

    resp = client._request("GET", "/any")
    assert resp.status_code == 200
    # One sleep due to reset header
    assert len(sleeper.calls) == 1
    assert calls["i"] == 2


def test_unretryable_400_raises_immediately():
    def handler(request: httpx.Request) -> httpx.Response:
        return make_response(400)

    transport = httpx.MockTransport(handler)
    client = GitHubClient(client=httpx.Client(transport=transport), max_retries=3)
    client._sleep = DummySleeper()

    with pytest.raises(httpx.HTTPStatusError):
        client._request("GET", "/any")
