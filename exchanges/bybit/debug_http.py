# exchanges/bybit/debug_http.py
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

import httpx

from exchanges.common.redact import redact_headers, redact_json, redact_text


def make_event_hooks(
    logger: Optional[Callable[[str], None]] = None,
    include_body: bool = True,
) -> Dict[str, List]:
    """
    Повертає event_hooks для httpx.AsyncClient з редагуванням секретів.
    Використання:

        import httpx
        from exchanges.bybit.debug_http import make_event_hooks
        from exchanges.bybit._http import SignedHTTPClient

        hooks = make_event_hooks()
        client = httpx.AsyncClient(event_hooks=hooks, timeout=10)
        http = SignedHTTPClient(base_url="https://api...", api_key="...", api_secret="...", client=client)

    logger: callable(str) — куди писати (за замовчуванням print)
    include_body: логувати тіло запиту/відповіді (SANITIZED)
    """
    if logger is None:
        logger = print  # noqa: T201

    async def on_request(request: httpx.Request) -> None:
        try:
            body_preview: Any = None
            if include_body and request.content:
                try:
                    body_json = json.loads(request.content.decode("utf-8"))
                    body_preview = redact_json(body_json)
                except Exception:
                    body_preview = redact_text(request.content.decode("utf-8", errors="ignore"))
            msg = {
                "type": "request",
                "method": request.method,
                "url": str(request.url),
                "headers": redact_headers({k: v for k, v in request.headers.items()}),
                "body": body_preview,
            }
            logger(json.dumps(msg, ensure_ascii=False))
        except Exception as e:  # без зривів бізнес-логіки
            logger(json.dumps({"type": "request-log-error", "error": repr(e)}, ensure_ascii=False))

    async def on_response(response: httpx.Response) -> None:
        try:
            body_preview: Any = None
            if include_body:
                try:
                    data = response.json()
                    body_preview = redact_json(data)
                except Exception:
                    body_preview = redact_text(response.text)
            msg = {
                "type": "response",
                "status_code": response.status_code,
                "url": str(response.request.url) if response.request else None,
                "headers": redact_headers({k: v for k, v in response.headers.items()}),
                "body": body_preview,
            }
            logger(json.dumps(msg, ensure_ascii=False))
        except Exception as e:
            logger(json.dumps({"type": "response-log-error", "error": repr(e)}, ensure_ascii=False))

    return {"request": [on_request], "response": [on_response]}
