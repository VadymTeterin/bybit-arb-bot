# scripts/smoke_bybit.py
from __future__ import annotations

import asyncio
import os

from exchanges.bybit.account_client import BybitAccountClient
from exchanges.bybit.public_client import BybitPublicClient
from exchanges.bybit.types import BybitConfig


async def main() -> None:
    cfg = BybitConfig(
        enabled=True,
        base_url_public=os.getenv("BYBIT_PUBLIC_URL", "https://api.bybit.com"),
        base_url_private=os.getenv("BYBIT_PRIVATE_URL", "https://api.bybit.com"),
        default_category=os.getenv("BYBIT_DEFAULT_CATEGORY", "spot"),
    )

    # --- Public: тикер
    pub = BybitPublicClient(cfg)
    try:
        t = await pub.get_ticker("BTC/USDT")
        print("Ticker:", t)
    finally:
        await pub.close()

    # --- Private: баланси (потребує BYBIT_API_KEY/BYBIT_API_SECRET)
    acc = BybitAccountClient(cfg)
    try:
        bals = await acc.get_balances()
        print("Balances:", bals[:3])
    except RuntimeError as e:
        # Якщо ключі не задані, наш клієнт підніме помилку — просто повідомимо і підемо далі
        print("Balances skipped:", e)
    finally:
        if acc.http is not None:
            await acc.http.close()


if __name__ == "__main__":
    asyncio.run(main())
