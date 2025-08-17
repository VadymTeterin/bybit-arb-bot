# scripts/smoke_bybit_ws.py
from __future__ import annotations

import asyncio
import os
from typing import List

from exchanges.bybit.ws_public import BybitWsPublic, WsConfig
from exchanges.contracts import Ticker


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v else default


async def main() -> None:
    # категорія з env (spot|linear)
    category = _env("BYBIT_DEFAULT_CATEGORY", "spot").lower()

    # демонстраційний список символів
    symbols: List[str] = ["BTCUSDT"]

    # збираємо тікери перші кілька подій і завершуємо
    got: List[Ticker] = []

    def on_ticker(t: Ticker) -> None:
        print(f"WS Ticker: {t}")  # noqa: T201
        got.append(t)

    cfg = WsConfig(category=category, symbols=tuple(symbols))
    ws = BybitWsPublic(cfg, on_ticker=on_ticker)

    # запускаємо і чекаємо перших 3-5 повідомлень або таймаут 15с
    task = asyncio.create_task(ws.run())
    try:
        for _ in range(15):
            await asyncio.sleep(1.0)
            if len(got) >= 3:
                break
    finally:
        await ws.close()
        await asyncio.sleep(0.1)
        task.cancel()
        with contextlib.suppress(Exception):
            await task

    if not got:
        print("No WS tickers received (try again or check network).")  # noqa: T201


if __name__ == "__main__":
    import contextlib

    asyncio.run(main())
