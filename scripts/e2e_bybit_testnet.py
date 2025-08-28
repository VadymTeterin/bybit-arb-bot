# scripts/e2e_bybit_testnet.py
from __future__ import annotations

import asyncio
import os

from exchanges.bybit.account_client import BybitAccountClient
from exchanges.bybit.trading_client import BybitTradingClient
from exchanges.bybit.types import BybitConfig


async def main() -> None:
    cfg = BybitConfig(
        enabled=True,
        base_url_public=os.getenv("BYBIT_PUBLIC_URL", "https://api-testnet.bybit.com"),
        base_url_private=os.getenv("BYBIT_PRIVATE_URL", "https://api-testnet.bybit.com"),
        default_category=os.getenv("BYBIT_DEFAULT_CATEGORY", "spot"),
    )

    print("== E2E Testnet: balances ==")
    acc = BybitAccountClient(cfg)
    try:
        bals = await acc.get_balances()
        print(f"Balances: {bals[:5]}")
    except Exception as e:  # noqa: BLE001
        print("Balances error:", e)
    finally:
        if acc.http is not None:
            await acc.http.close()

    if os.getenv("BYBIT_PLACE_ORDER") != "1":
        print("== Skipping order create/cancel (set BYBIT_PLACE_ORDER=1 to try) ==")
        return

    symbol = os.getenv("BYBIT_ORDER_SYMBOL", "BTC/USDT")
    market = os.getenv("BYBIT_ORDER_MARKET", "spot")  # "spot" or "perp"
    side = os.getenv("BYBIT_ORDER_SIDE", "buy")  # "buy" or "sell"
    order_type = os.getenv("BYBIT_ORDER_TYPE", "limit")  # "limit" or "market"
    qty = float(os.getenv("BYBIT_ORDER_QTY", "0.0001"))
    price_env = os.getenv("BYBIT_ORDER_PRICE")
    price = float(price_env) if price_env else None

    print("== E2E Testnet: create/cancel order ==")
    tr = BybitTradingClient(cfg)
    try:
        created = await tr.create_order(
            symbol=symbol,
            side=side,  # type: ignore[arg-type]
            type=order_type,  # type: ignore[arg-type]
            qty=qty,
            price=price,
            market=market,  # type: ignore[arg-type]
        )
        print("Create result:", created)
        order_id = (created.get("result") or {}).get("orderId")
        if order_id:
            canceled = await tr.cancel_order(symbol=symbol, order_id=order_id, market=market)  # type: ignore[arg-type]
            print("Cancel result:", canceled)
        else:
            print("No orderId returned; cannot cancel.")
    except Exception as e:  # noqa: BLE001
        print("Order error:", e)
    finally:
        if tr.http is not None:
            await tr.http.close()


if __name__ == "__main__":
    asyncio.run(main())
