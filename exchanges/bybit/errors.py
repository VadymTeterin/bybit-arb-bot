# exchanges/bybit/errors.py
class BybitError(Exception):
    """Узагальнена помилка BYBIT."""


class BybitRateLimitError(BybitError):
    pass


class BybitAuthError(BybitError):
    pass


def map_error(code: str | int, msg: str) -> BybitError:
    code = str(code)
    if code in {"10006", "10005"}:
        return BybitAuthError(f"[{code}] {msg}")
    if code in {"10016", "10017", "10018"}:
        return BybitRateLimitError(f"[{code}] {msg}")
    return BybitError(f"[{code}] {msg}")
