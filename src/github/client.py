# src/github/client.py
# (c) Bybit Arb Bot — GitHub Daily Digest client scaffold
from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, Optional

import httpx


class RateLimitError(RuntimeError):
    """Raised when GitHub API rate limit is reached."""


class GitHubClient:
    """
    Minimal GitHub REST client (sync) with:
      - httpx.Client
      - Auth via GH_TOKEN/GITHUB_TOKEN (Bearer)
      - Timeouts
      - Basic retries with backoff
      - Simple rate-limit guard (X-RateLimit-Remaining/Reset)
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
        timeout_sec: float = 10.0,
        max_retries: int = 3,
        backoff_sec: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        self.timeout = httpx.Timeout(timeout_sec)
        self.max_retries = max_retries
        self.backoff_sec = backoff_sec
        self._client = httpx.Client(timeout=self.timeout, headers=self._make_headers())

    def _make_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "bybit-arb-bot-gh-digest/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def close(self) -> None:
        self._client.close()

    # -------- Core HTTP ----------
    def _request(
        self, method: str, path: str, params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.request(method, url, params=params)
                # Rate-limit guard
                rem = resp.headers.get("X-RateLimit-Remaining")
                if rem is not None and rem.isdigit() and int(rem) <= 0:
                    reset = resp.headers.get("X-RateLimit-Reset")
                    raise RateLimitError(f"GitHub rate limit reached; reset={reset}")

                if resp.status_code == 403 and "rate limit" in resp.text.lower():
                    reset = resp.headers.get("X-RateLimit-Reset")
                    raise RateLimitError(f"GitHub rate limit (403); reset={reset}")

                if resp.status_code >= 500:
                    # transient server errors -> retry
                    raise httpx.HTTPStatusError(
                        f"{resp.status_code} server error",
                        request=resp.request,
                        response=resp,
                    )

                resp.raise_for_status()
                return resp
            except (
                httpx.ConnectError,
                httpx.ReadError,
                httpx.TimeoutException,
                httpx.HTTPStatusError,
            ) as e:
                last_error = e
                if attempt >= self.max_retries:
                    break
                # Exponential backoff
                time.sleep(self.backoff_sec * (2**attempt))
        # If we are here — retries exhausted
        if isinstance(last_error, RateLimitError):
            raise last_error
        raise RuntimeError(f"GitHub request failed after retries: {last_error}")

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = self._request("GET", path, params=params)
        return resp.json()

    # -------- Convenience endpoints (not used by tests; kept for future steps) ----------
    def list_commits(
        self,
        owner: str,
        repo: str,
        *,
        since_iso: str,
        until_iso: Optional[str] = None,
        per_page: int = 100,
    ) -> Iterable[Dict[str, Any]]:
        """
        Yields commits within a time window. Note: GitHub 'until' is supported via 'until' param.
        """
        page = 1
        while True:
            params = {"since": since_iso, "per_page": per_page, "page": page}
            if until_iso:
                params["until"] = until_iso
            data = self.get_json(f"/repos/{owner}/{repo}/commits", params=params)
            if not data:
                break
            for item in data:
                yield item
            if len(data) < per_page:
                break
            page += 1

    def list_pulls_merged(
        self, owner: str, repo: str, *, state: str = "closed", per_page: int = 100
    ) -> Iterable[Dict[str, Any]]:
        """
        Yields recently updated PRs; caller must filter merged_at window.
        """
        page = 1
        while True:
            params = {
                "state": state,
                "sort": "updated",
                "direction": "desc",
                "per_page": per_page,
                "page": page,
            }
            data = self.get_json(f"/repos/{owner}/{repo}/pulls", params=params)
            if not data:
                break
            for item in data:
                yield item
            if len(data) < per_page:
                break
            page += 1

    def list_tags(
        self, owner: str, repo: str, *, per_page: int = 100
    ) -> Iterable[Dict[str, Any]]:
        """
        Yields tags (lightweight annotated). No server-side date filter; caller filters by commit date.
        """
        page = 1
        while True:
            params = {"per_page": per_page, "page": page}
            data = self.get_json(f"/repos/{owner}/{repo}/tags", params=params)
            if not data:
                break
            for item in data:
                yield item
            if len(data) < per_page:
                break
            page += 1
