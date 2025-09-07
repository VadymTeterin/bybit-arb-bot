import asyncio
import os
from contextlib import suppress
from typing import Optional

from exchanges.bybit.ws_public import BybitWsPublic, Ticker

def _print_ticker(t: Ticker) -> None:
    print(f"WS Ticker: {t}")

def _detect_host_label(base_http: str) -> str:
    b = (base_http or "").lower()
    if "api-testnet.bybit.com" in b:
        return "testnet"
    if "api-demo.bybit.com" in b or "demo" in b:
        return "demo"
    return "mainnet"

def _ws_url_for(category: str, host_label: str) -> str:
    # Allow explicit overrides
    if category == "spot":
        override = os.getenv("WS_PUBLIC_URL_SPOT") or os.getenv("WS_PUBLIC_URL")
        if override:
            return override
    else:
        override = os.getenv("WS_PUBLIC_URL_LINEAR") or os.getenv("WS_PUBLIC_URL")
        if override:
            return override

    # Fallbacks based on host label
    if host_label == "testnet":
        return f"wss://stream-testnet.bybit.com/v5/public/{category}"
    if host_label == "demo":
        return f"wss://stream-demo.bybit.com/v5/public/{category}"
    # mainnet default
    return f"wss://stream.bybit.com/v5/public/{category}"

async def main() -> None:
    symbol = os.getenv("BYBIT_SYMBOL", "BTCUSDT")
    category = os.getenv("BYBIT_DEFAULT_CATEGORY", "spot") or "spot"
    seconds = int(os.getenv("WS_SMOKE_DURATION_SEC", os.getenv("BYBIT_WS_SMOKE_DURATION_SEC", "12")))

    base_http = os.getenv("BYBIT_PUBLIC_URL") or os.getenv("BYBIT_PRIVATE_URL") or ""
    host_label = _detect_host_label(base_http)
    ws_url = _ws_url_for(category, host_label)

    # Header
    print(f"[WS smoke] category={category} symbol={symbol} host={host_label} url={ws_url} duration={seconds}s")

    recv_count = 0
    def on_ticker(t: Ticker) -> None:
        nonlocal recv_count
        recv_count += 1
        _print_ticker(t)

    ws = BybitWsPublic(symbol, on_ticker=on_ticker, category=category)

    task = asyncio.create_task(ws.run())
    try:
        await asyncio.sleep(seconds)
    finally:
        # Плавна зупинка + чек завершення
        await ws.stop()
        with suppress(asyncio.CancelledError):
            await task

    print(f"[WS smoke] received={recv_count} tickers, done.")

if __name__ == "__main__":
    asyncio.run(main())
