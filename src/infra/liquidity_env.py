from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LiquidityParams:
    min_vol24_usd: float = 10_000_000
    min_price_usd: float = 0.01


def _to_float(val: str | None, default: float) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val.replace("_", ""))
    except Exception:
        return default


def load_liquidity_params() -> LiquidityParams:
    """
    Пріоритет flat > nested (як у 6.1.1):
      1) MIN_VOL24_USD / MIN_PRICE_USD
      2) LIQUIDITY__MIN_VOL24_USD / LIQUIDITY__MIN_PRICE_USD
      3) дефолти: $10M і $0.01
    """
    min_vol = _to_float(
        os.getenv("MIN_VOL24_USD", os.getenv("LIQUIDITY__MIN_VOL24_USD")),
        LiquidityParams.min_vol24_usd,
    )
    min_price = _to_float(
        os.getenv("MIN_PRICE_USD", os.getenv("LIQUIDITY__MIN_PRICE_USD")),
        LiquidityParams.min_price_usd,
    )
    return LiquidityParams(min_vol24_usd=min_vol, min_price_usd=min_price)
