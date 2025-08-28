from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from src.infra.liquidity_env import load_liquidity_params

from .liquidity import enough_liquidity


def make_liquidity_predicate(
    min_vol_usd: float | None = None, min_price_usd: float | None = None
) -> Callable[[Mapping[str, Any]], bool]:
    """
    Повертає функцію-предикат row -> bool.
    Якщо параметри не передані, беруться з env (див. load_liquidity_params()).
    """
    params = load_liquidity_params()
    mv = params.min_vol24_usd if min_vol_usd is None else float(min_vol_usd)
    mp = params.min_price_usd if min_price_usd is None else float(min_price_usd)
    return lambda row: enough_liquidity(row, mv, mp)
