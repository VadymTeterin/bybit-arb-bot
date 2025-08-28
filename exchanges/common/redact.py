# exchanges/common/redact.py
from __future__ import annotations

import json
import re
from typing import Any, Mapping

# Ключі/заголовки, які треба маскувати
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(api[_-]?key|api[_-]?secret|secret|signature|sign|authorization|"
    r"x-bapi-[a-z0-9\-]+|access[_-]?key|bearer|set-cookie|cookie)"
)

# Патерни для маскування в сирому тексті (логи, дампи)
_TEXT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r'(?i)("?(x-bapi-[a-z0-9\-]+|authorization|api-?key|api[_-]?secret|signature)"?\s*[:=]\s*")([^"]+)(")'
    ),
    re.compile(r"(?i)\b(api_key|apiSecret|signature|api-secret|api-key)\s*=\s*([^\s&]+)"),
    re.compile(r"(?i)\b(BEARER|Bearer)\s+([A-Za-z0-9\.\-_]+)"),
]

_MASK = "****"


def _redact_value(value: str | bytes | None) -> str:
    if value is None:
        return _MASK
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            return _MASK
    v = str(value)
    if len(v) <= 8:
        return _MASK
    return v[:4] + "…" + v[-4:]


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in headers.items():
        if _SENSITIVE_KEY_RE.search(k):
            out[k] = _redact_value(v)
        else:
            out[k] = v
    return out


def redact_json(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        result: dict[str, Any] = {}
        for k, v in obj.items():
            if _SENSITIVE_KEY_RE.search(str(k)):
                result[str(k)] = _redact_value(
                    v if isinstance(v, (str, bytes)) else json.dumps(v, ensure_ascii=False)
                )
            else:
                result[str(k)] = redact_json(v)
        return result
    if isinstance(obj, list):
        return [redact_json(v) for v in obj]
    return obj


def redact_text(text: str) -> str:
    s = text
    # Маскуємо ключі/підписи у форматах JSON та key=value
    s = _TEXT_PATTERNS[0].sub(r"\1" + _MASK + r"\4", s)
    s = _TEXT_PATTERNS[1].sub(r"\1=" + _MASK, s)
    s = _TEXT_PATTERNS[2].sub(r"\1 " + _MASK, s)
    return s
