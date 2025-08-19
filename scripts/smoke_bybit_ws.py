import asyncio
import os
from contextlib import suppress

from exchanges.bybit.ws_public import BybitWsPublic, Ticker


def _print_ticker(t: Ticker) -> None:
    print(f"WS Ticker: {t}")


async def main() -> None:
    symbol = os.getenv("BYBIT_SYMBOL", "BTCUSDT")
    category = os.getenv("BYBIT_DEFAULT_CATEGORY", "spot") or "spot"

    ws = BybitWsPublic(symbol, on_ticker=_print_ticker, category=category)

    seconds = int(os.getenv("BYBIT_WS_SMOKE_SECONDS", "12"))
    # Діагностичний заголовок (не містить секретів)
    print(
        f"[WS smoke] category={ws.category} symbol={symbol} "
        f"host={'testnet' if 'testnet' in (os.getenv('BYBIT_PUBLIC_URL', '')) else 'mainnet'} "
        f"url={getattr(ws, '_url', '?')} "
        f"duration={seconds}s"
    )

    recv_count = 0

    # Обгорнемо користувацький колбек, щоб порахувати тікери
    def _counting_cb(t: Ticker) -> None:
        nonlocal recv_count
        recv_count += 1
        _print_ticker(t)

    ws.on_ticker = _counting_cb

    task = asyncio.create_task(ws.run())
    await asyncio.sleep(seconds)

    # Плавна зупинка + чек завершення
    await ws.stop()
    with suppress(asyncio.CancelledError):
        await task

    print(f"[WS smoke] received={recv_count} tickers, done.")


if __name__ == "__main__":
    asyncio.run(main())
