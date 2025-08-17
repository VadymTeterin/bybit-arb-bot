# tests/bybit/test_errors_map.py
from __future__ import annotations

from exchanges.bybit.errors import (
    BybitError,
    ExchangeAuthError,
    ExchangeInvalidRequest,
    ExchangeRateLimit,
    map_error,
)


def test_map_error_rate_limit():
    exc = map_error(10016, "rate limit")
    assert isinstance(exc, ExchangeRateLimit)


def test_map_error_auth():
    exc = map_error(10004, "signature error")
    assert isinstance(exc, ExchangeAuthError)


def test_map_error_invalid():
    exc = map_error(10003, "param error")
    assert isinstance(exc, ExchangeInvalidRequest)


def test_map_error_unknown_wraps_bybit_error():
    exc = map_error(99999, "strange")
    assert isinstance(exc, BybitError)
    assert "99999" in str(exc)
