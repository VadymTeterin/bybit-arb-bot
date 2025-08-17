import asyncio
import os

from exchanges.bybit.ws_public import BybitWsPublic


def _print_ticker(t) -> None:
    # Формат виводу залишив таким, як у прикладах вище
    print(
        f"WS Ticker: Ticker(symbol='{t.symbol}', bid={t.bid}, "
        f"ask={t.ask}, last={t.last}, ts={t.ts})"
    )


async def main() -> None:
    symbol = os.getenv("BYBIT_SYMBOL", "BTCUSDT")

    ws = BybitWsPublic(symbol, on_ticker=_print_ticker)

    task = asyncio.create_task(ws.run())
    try:
        # Дефолтно ~9 сек, можна змінити через BYBIT_SMOKE_DURATION
        await asyncio.sleep(float(os.getenv("BYBIT_SMOKE_DURATION", "9")))
    finally:
        await ws.stop()
        await task


if __name__ == "__main__":
    asyncio.run(main())
