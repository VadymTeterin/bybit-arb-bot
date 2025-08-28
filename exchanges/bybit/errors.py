# exchanges/bybit/errors.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---- Unified exception hierarchy (used across all exchange clients)


class ExchangeError(Exception):
    """Generic exchange error."""


class ExchangeInvalidRequest(ExchangeError):
    """Invalid or missing parameters."""


class ExchangeAuthError(ExchangeError):
    """Authentication / permission problem (key, signature, IP whitelist)."""


class ExchangeRateLimit(ExchangeError):
    """Too many requests / rate limit reached."""


class ExchangeServerError(ExchangeError):
    """5xx or temporary server-side problem."""


class ExchangeNotFound(ExchangeError):
    """Requested resource or order not found."""


class ExchangeInsufficientFunds(ExchangeError):
    """Not enough balance to perform operation."""


# ---- Bybit-specific wrapper (optional convenience)


@dataclass(frozen=True)
class BybitError(ExchangeError):
    ret_code: int | None = None
    ret_msg: str = "unknown error"

    def __str__(self) -> str:  # noqa: D401
        return f"[Bybit retCode={self.ret_code}] {self.ret_msg}"


# ---- Mapping retCode -> unified error

# Common Bybit v5 codes (subset, safe defaults). Docs evolve; keep conservative.
_RATE_LIMIT = {"10016", "10017", "10018"}  # too many requests
_AUTH = {"10004", "10005", "10006", "130021", "130024"}  # sign/permission/ip
_INVALID = {"10001", "10002", "10003"}  # param errors
_NOT_FOUND = {"110001", "110002", "110003"}  # resource/order missing (representative)
_INSUFF_FUNDS = {"110051", "110052", "110053"}  # insufficient balance (representative)


def map_error(ret_code: Any, message: str = "unknown error") -> ExchangeError:
    """
    Convert Bybit retCode to unified exceptions.
    Falls back to BybitError if code is unknown.
    """
    code = None
    try:
        code = int(ret_code) if ret_code is not None else None
    except Exception:
        pass

    s = str(ret_code) if ret_code is not None else ""

    if s in _RATE_LIMIT:
        return ExchangeRateLimit(message)
    if s in _AUTH:
        return ExchangeAuthError(message)
    if s in _INVALID:
        return ExchangeInvalidRequest(message)
    if s in _NOT_FOUND:
        return ExchangeNotFound(message)
    if s in _INSUFF_FUNDS:
        return ExchangeInsufficientFunds(message)

    # Unknown but non-zero: wrap in BybitError to preserve details
    return BybitError(ret_code=code, ret_msg=message)
