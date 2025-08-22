# tests/test_gh_digest_send_mock.py
from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from scripts.gh_daily_digest import (
    _mark_sent_today,
    _send_telegram,
    _should_send_today,
    _throttle_stamp_path,
)

RUN_DIR = Path("run")


class DummyResp:
    def __init__(self, ok=True):
        self._ok = ok

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": self._ok}


def test_send_telegram_happy_path(monkeypatch, tmp_path):
    # Set env
    monkeypatch.setenv("TG_BOT_TOKEN", "x" * 10)
    monkeypatch.setenv("TG_CHAT_ID", "123456")

    # Monkeypatch httpx.Client.post
    calls = {"n": 0}

    class DummyClient:
        def __init__(self, timeout=10.0):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, data=None):
            calls["n"] += 1
            assert "sendMessage" in url
            assert isinstance(data, dict)
            return DummyResp(ok=True)

    import scripts.gh_daily_digest as mod

    monkeypatch.setattr(mod, "httpx", SimpleNamespace(Client=DummyClient))

    _send_telegram("hello world")
    assert calls["n"] == 1


def test_daily_throttle(tmp_path, monkeypatch):
    d = date(2025, 8, 22)
    # Ensure clean state for the test
    p = _throttle_stamp_path(d)
    if p.exists():
        p.unlink()
    assert _should_send_today(d) is True
    _mark_sent_today(d)
    assert _should_send_today(d) is False
