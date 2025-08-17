# exchanges/bybit/auth.py
from __future__ import annotations

import hmac
import json
from hashlib import sha256
from typing import Any, Dict, Iterable, Tuple


def canonical_query(params: Dict[str, Any] | None) -> str:
    """Сортує та з’єднує params у 'k=v&k2=v2' (без URL-екодингу; None пропускаємо)."""
    if not params:
        return ""
    items: Iterable[Tuple[str, Any]] = (
        (k, v) for k, v in params.items() if v is not None
    )
    sorted_items = sorted(items, key=lambda kv: kv[0])
    return "&".join(f"{k}={v}" for k, v in sorted_items)


def canonical_json(body: Dict[str, Any] | None) -> str:
    """Компактизований JSON для підпису (separators без пробілів)."""
    if body is None:
        return "{}"
    return json.dumps(body, separators=(",", ":"), ensure_ascii=False)


def sign_v5(
    api_key: str, api_secret: str, recv_window_ms: int, timestamp_ms: str, body_str: str
) -> str:
    """
    Bybit v5: sign = HMAC_SHA256(secret, timestamp + api_key + recvWindow + body)
    Повертаємо hex-рядок у нижньому регістрі.
    """
    prehash = f"{timestamp_ms}{api_key}{recv_window_ms}{body_str}"
    return hmac.new(
        api_secret.encode("utf-8"), prehash.encode("utf-8"), sha256
    ).hexdigest()
