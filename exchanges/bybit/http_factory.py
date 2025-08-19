# exchanges/bybit/http_factory.py
from __future__ import annotations

import os
from typing import Dict, List

import httpx

from exchanges.bybit.debug_http import make_event_hooks


def _flag(name: str, default: str = "0") -> bool:
    val = os.getenv(name, default)
    return str(val).lower() not in ("", "0", "false", "no", "off")


def build_async_client() -> httpx.AsyncClient:
    """
    Створює httpx.AsyncClient.
    Якщо BYBIT_DEBUG_HTTP=1 — підключає безпечні event_hooks з маскуванням секретів.
    Додатково: BYBIT_DEBUG_BODY=1 — логувати SANITIZED body.
    """
    debug_http = _flag("BYBIT_DEBUG_HTTP")
    debug_body = _flag("BYBIT_DEBUG_BODY")

    event_hooks: Dict[str, List] = {}
    if debug_http:
        event_hooks = make_event_hooks(include_body=debug_body)

    timeout = httpx.Timeout(connect=10.0, read=20.0, write=20.0, pool=None)
    limits = httpx.Limits(
        max_connections=50,
        max_keepalive_connections=20,
        keepalive_expiry=45.0,
    )

    # Примітка: verify=True за замовч., HTTP/2 не вимагаємо.
    return httpx.AsyncClient(timeout=timeout, limits=limits, event_hooks=event_hooks)
