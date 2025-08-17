# exchanges/bybit/rate_limiter.py
from __future__ import annotations

import asyncio
import threading
import time


class TokenBucket:
    """Синхронний токен-бакет (може застосовуватись у не-async ділянках)."""

    def __init__(self, rate_per_sec: float, burst: int):
        self.rate = rate_per_sec
        self.capacity = burst
        self._tokens = float(burst)
        self._ts = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._ts
            self._ts = now
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            if self._tokens < tokens:
                wait = (tokens - self._tokens) / self.rate
                time.sleep(max(0.0, wait))
                self._tokens = 0.0
            else:
                self._tokens -= tokens


class AsyncTokenBucket:
    """Async варіант токен-бакету для використання з async HTTP."""

    def __init__(self, rate_per_sec: float, burst: int):
        self.rate = rate_per_sec
        self.capacity = float(burst)
        self._tokens = float(burst)
        self._ts = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._ts
            self._ts = now
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            if self._tokens < tokens:
                wait = (tokens - self._tokens) / self.rate
                await asyncio.sleep(max(0.0, wait))
                self._tokens = 0.0
            else:
                self._tokens -= tokens
