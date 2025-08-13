from __future__ import annotations

from typing import Any, Mapping


def _get_float(d: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    """Дістає перше доступне числове значення по списку ключів."""
    for k in keys:
        if k in d and d[k] is not None:
            try:
                return float(d[k])
            except (TypeError, ValueError):
                continue
    return float(default)


def enough_liquidity(
    row: Mapping[str, Any], min_vol_usd: float, min_price: float
) -> bool:
    """
    Перевіряє, що інструмент ліквідний за двома критеріями:
      1) ціна >= min_price
      2) 24h обіг у $ >= min_vol_usd

    Підтримує кілька варіантів ключів:
      - ціна: "lastPrice", "lastPriceLatest", "price"
      - обіг: "turnoverUsd", "turnover_usd", "turnover24h"
    """
    price = _get_float(row, "lastPrice", "lastPriceLatest", "price")
    vol_usd = _get_float(row, "turnoverUsd", "turnover_usd", "turnover24h")

    if price <= 0 or vol_usd < 0:
        return False

    return (price >= float(min_price)) and (vol_usd >= float(min_vol_usd))
