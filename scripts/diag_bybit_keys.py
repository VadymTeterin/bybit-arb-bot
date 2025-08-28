# scripts/diag_bybit_keys.py
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from exchanges.bybit._http import SignedHTTPClient
from exchanges.bybit.types import BybitConfig


def _mask(s: str) -> str:
    if not s:
        return ""
    return (s[:4] + "…" + s[-4:]) if len(s) > 8 else "****"


async def main() -> None:
    api_key = os.getenv("BYBIT_API_KEY", "")
    api_secret = os.getenv("BYBIT_API_SECRET", "")
    base = os.getenv("BYBIT_PRIVATE_URL", "https://api.bybit.com")
    pub = os.getenv("BYBIT_PUBLIC_URL", base)
    category = os.getenv("BYBIT_DEFAULT_CATEGORY", "spot")

    print("== ENV CHECK (masked) ==")
    print("BYBIT_PUBLIC_URL       =", pub)
    print("BYBIT_PRIVATE_URL      =", base)
    print("BYBIT_DEFAULT_CATEGORY =", category)
    print("BYBIT_API_KEY          =", _mask(api_key))
    print("BYBIT_API_SECRET       =", _mask(api_secret))
    print()

    if not api_key or not api_secret:
        print("ERR: BYBIT_API_KEY/BYBIT_API_SECRET не задані у середовищі.")
        return

    cfg = BybitConfig(
        enabled=True,
        base_url_public=pub,
        base_url_private=base,
        default_category=category,
    )

    http = SignedHTTPClient(
        base_url=cfg.base_url_private,
        api_key=api_key,
        api_secret=api_secret,
        recv_window_ms=cfg.recv_window_ms,
    )

    print("== /v5/user/query-api (перевірка ключа) ==")
    try:
        data: dict[str, Any] = await http.get("/v5/user/query-api")
        # Показуємо лише суть, без зайвих полів
        print(
            json.dumps(
                {"retCode": data.get("retCode"), "retMsg": data.get("retMsg")},
                ensure_ascii=False,
            )
        )
    except Exception as e:
        print("HTTP/Sign error:", repr(e))
    finally:
        await http.close()

    print("\n== /v5/account/wallet-balance (швидка перевірка) ==")
    account_type = os.getenv("BYBIT_BAL_ACCOUNT_TYPE", "UNIFIED")  # SPOT|UNIFIED|CONTRACT
    http = SignedHTTPClient(
        base_url=cfg.base_url_private,
        api_key=api_key,
        api_secret=api_secret,
        recv_window_ms=cfg.recv_window_ms,
    )
    try:
        data = await http.get("/v5/account/wallet-balance", params={"accountType": account_type})
        # Скорочений підсумок: скільки активів ненульові
        result = data.get("result") or {}
        list_ = result.get("list") or []
        nonzero = 0
        assets_preview = []
        for acc in list_:
            coin_list = acc.get("coin", [])
            for c in coin_list:
                try:
                    total = float(c.get("walletBalance") or 0)
                except Exception:
                    total = 0.0
                if total:
                    nonzero += 1
                    if len(assets_preview) < 5:
                        assets_preview.append({"coin": c.get("coin"), "balance": total})
        print(
            json.dumps(
                {
                    "retCode": data.get("retCode"),
                    "retMsg": data.get("retMsg"),
                    "accountType": account_type,
                    "nonzero_assets": nonzero,
                    "preview": assets_preview,
                },
                ensure_ascii=False,
            )
        )
    except Exception as e:
        print("HTTP/Balance error:", repr(e))
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
