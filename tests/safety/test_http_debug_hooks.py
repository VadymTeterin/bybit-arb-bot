# tests/safety/test_http_debug_hooks.py
from __future__ import annotations

import asyncio
import json

import httpx

from exchanges.bybit.debug_http import make_event_hooks


async def _fire_hooks():
    logs: list[str] = []

    hooks = make_event_hooks(logger=logs.append, include_body=True)

    # Підготовимо фейковий запит
    req = httpx.Request(
        "POST",
        "https://example.com/v5/order",
        headers={
            "X-BAPI-API-KEY": "MYSECRETKEY",
            "X-BAPI-SIGN": "SIGNATURE",
            "Content-Type": "application/json",
        },
        content=b'{"apiKey":"AAA","amount":1}',
    )
    # Викликаємо request-hook
    await hooks["request"][0](req)

    # Фейкова відповідь
    resp = httpx.Response(
        200,
        headers={"Content-Type": "application/json", "Set-Cookie": "sid=abcdef"},
        request=req,
        content=b'{"retCode":0,"retMsg":"OK","result":{"secret":"BBB","ok":true}}',
    )
    # Викликаємо response-hook
    await hooks["response"][0](resp)

    joined = "\n".join(logs)
    # секрети не повинні з’являтися
    assert "MYSECRETKEY" not in joined
    assert "SIGNATURE" not in joined
    assert "AAA" not in joined
    assert "BBB" not in joined

    # ключі заголовків мають бути присутні, регістр і нормалізація — неважливі
    low = joined.lower()
    assert "x-bapi-api-key" in low
    assert "set-cookie" in low

    # кожен лог — валідний JSON і має коректний тип
    for line in logs:
        obj = json.loads(line)
        assert obj["type"] in {"request", "response"}


def test_http_debug_hooks_run():
    asyncio.run(_fire_hooks())
