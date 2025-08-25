from __future__ import annotations

from typing import Any, Mapping, Optional


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _pick_first(
    m: Mapping[str, Any], *keys: str, default: Optional[float] = None
) -> Optional[float]:
    for k in keys:
        if k in m and m[k] is not None:
            return _to_float(m[k])
    return default


def enough_liquidity(
    row: Mapping[str, Any], min_vol_usd: float, min_price: float
) -> bool:
    """
    Перевіряє базову ліквідність SPOT-рядка:
      - min_price: мінімальна ціна активу (щоб відсіяти пені-коіни)
      - min_vol_usd: мінімальний 24h обіг у доларах (quote/turnover)

    Очікує ключі (гнучко): price | last | spot | close, turnover_usd | volume24h_usd | vol_usd | quoteVolume.

    Повертає True/False  селектор використовує це як фільтр.
    """
    if not isinstance(row, Mapping):
        return False

    price = _pick_first(row, "price", "last", "spot", "close", default=0.0) or 0.0
    vol_usd = (
        _pick_first(
            row,
            "turnover_usd",
            "volume24h_usd",
            "vol_usd",
            "quoteVolume",
            default=0.0,
        )
        or 0.0
    )

    if price <= 0 or vol_usd <= 0:
        return False
    if price < float(min_price):
        return False
    if vol_usd < float(min_vol_usd):
        return False
    return True
