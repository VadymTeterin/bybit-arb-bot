from __future__ import annotations

import os
import random
import time
from typing import Any, Dict, List, Optional

import httpx

DEFAULT_BASE_URL = "https://api.github.com"
DEFAULT_UA = "bybit-arb-bot/0.6 (+github-digest)"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GitHubClient:
    """
    Minimal GitHub REST v3 client with safe defaults:
      * Auth via GH_TOKEN / GITHUB_TOKEN (optional for public repos)
      * Sensible timeouts (connect/read/write/overall)
      * Retries with exponential backoff + jitter on 429/5xx and transport errors
      * Basic rate-limit guard (403 with X-RateLimit-Remaining: 0)
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | httpx.Timeout = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        max_sleep_on_reset: int = 60,
        client: Optional[httpx.Client] = None,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.timeout = (
            timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
        )
        self.max_retries = max(1, int(max_retries))
        self.backoff_factor = float(backoff_factor)
        self.max_sleep_on_reset = int(max_sleep_on_reset)
        self._sleep = time.sleep  # injectable for tests

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": user_agent,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Використовуємо переданий клієнт або створюємо свій з base_url
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers,
        )

    # -------------- helpers --------------

    def _calc_backoff(self, attempt: int) -> float:
        # exponential backoff with small jitter
        base = self.backoff_factor * (2 ** (attempt - 1))
        return base + random.uniform(0, 0.1)

    def _absolute(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if not url.startswith("/"):
            url = "/" + url
        return f"{self.base_url}{url}"

    def _handle_rate_limit_reset(self, resp: httpx.Response, attempt: int) -> bool:
        """
        Return True if we should sleep and retry due to 403 rate limit,
        otherwise False.
        """
        if resp.status_code != 403:
            return False
        if resp.headers.get("X-RateLimit-Remaining") not in {None, "0"}:
            return False

        try:
            reset_epoch = int(resp.headers.get("X-RateLimit-Reset", "0"))
        except ValueError:
            reset_epoch = 0

        now = int(time.time())
        delay = max(0, reset_epoch - now)
        if delay > self.max_sleep_on_reset:
            delay = self.max_sleep_on_reset

        if attempt < self.max_retries:
            self._sleep(delay or self._calc_backoff(attempt))
            return True
        return False

    # -------------- low-level --------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        last_exc: Optional[Exception] = None
        full_url = self._absolute(url)

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._client.request(method, full_url, params=params)
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise
                self._sleep(self._calc_backoff(attempt))
                continue

            # Success
            if 200 <= resp.status_code < 300:
                return resp

            # Hard stop on unretryable 4xx (але дозволяємо guard для 403 rate-limit)
            if resp.status_code not in RETRYABLE_STATUS:
                if self._handle_rate_limit_reset(resp, attempt):
                    continue
                resp.raise_for_status()

            # Retryable status
            if attempt < self.max_retries:
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(0.0, float(retry_after))
                    except ValueError:
                        delay = self._calc_backoff(attempt)
                else:
                    delay = self._calc_backoff(attempt)
                self._sleep(delay)
                continue

            # No attempts left
            resp.raise_for_status()

        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected request loop exit")

    # -------------- high-level --------------

    def list_commits(
        self,
        owner: str,
        repo: str,
        *,
        since: Optional[str] = None,
        until: Optional[str] = None,
        per_page: int = 100,
        max_pages: int = 3,
        sha: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent commits (paginated; limited by max_pages)."""
        out: List[Dict[str, Any]] = []
        params: Dict[str, Any] = {"per_page": per_page}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if sha:
            params["sha"] = sha

        for page in range(1, max_pages + 1):
            params["page"] = page
            resp = self._request("GET", f"/repos/{owner}/{repo}/commits", params=params)
            batch = resp.json()
            if not isinstance(batch, list) or not batch:
                break
            out.extend(batch)
            if len(batch) < per_page:
                break
        return out

    def list_pulls(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "closed",
        sort: str = "updated",
        direction: str = "desc",
        per_page: int = 100,
        max_pages: int = 3,
        base: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return pull requests (by default 'closed', sorted by 'updated')."""
        out: List[Dict[str, Any]] = []
        params: Dict[str, Any] = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
        }
        if base:
            params["base"] = base

        for page in range(1, max_pages + 1):
            params["page"] = page
            resp = self._request("GET", f"/repos/{owner}/{repo}/pulls", params=params)
            batch = resp.json()
            if not isinstance(batch, list) or not batch:
                break
            out.extend(batch)
            if len(batch) < per_page:
                break
        return out

    def list_tags(
        self,
        owner: str,
        repo: str,
        *,
        per_page: int = 100,
        max_pages: int = 2,
    ) -> List[Dict[str, Any]]:
        """Return tags (lightweight)."""
        out: List[Dict[str, Any]] = []
        params: Dict[str, Any] = {"per_page": per_page}
        for page in range(1, max_pages + 1):
            params["page"] = page
            resp = self._request("GET", f"/repos/{owner}/{repo}/tags", params=params)
            batch = resp.json()
            if not isinstance(batch, list) or not batch:
                break
            out.extend(batch)
            if len(batch) < per_page:
                break
        return out

    # -------------- lifecycle --------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()
