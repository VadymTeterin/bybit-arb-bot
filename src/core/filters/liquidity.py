from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _norm_key(k: str) -> str:
    # уніфікуємо ключ: нижній регістр + забираємо все не [a-z0-9]
    return re.sub(r"[^a-z0-9]", "", str(k).lower())


def _pick_first(m: Mapping[str, Any], *keys: str, default: float | None = None) -> float | None:
    # 1) спроба точних збігів (щоб не втратити вже існуючі ключі)
    for k in keys:
        if k in m and m[k] is not None:
            return _to_float(m[k])

    # 2) гнучкий пошук: нормалізовані ключі (lastPrice -> lastprice, quoteVolume -> quotevolume, тощо)
    norm_map = {_norm_key(k): v for k, v in m.items() if v is not None}
    for k in keys:
        nk = _norm_key(k)
        if nk in norm_map:
            return _to_float(norm_map[nk])

    return default


def enough_liquidity(row: Mapping[str, Any], min_vol_usd: float, min_price: float) -> bool:
    """
    Перевіряє базову ліквідність SPOT-рядка:
      - min_price: мінімальна ціна активу (щоб відсіяти пені-коіни)
      - min_vol_usd: мінімальний 24h обіг у доларах (quote/turnover)

    Підтримувані ключі (гнучко, без регістру/підкреслень):
      Ціна: price, last, last_price, lastPrice, spot, close, markPrice, indexPrice
      Обіг: turnover_usd, volume24h_usd, vol_usd, quoteVolume, quote_volume, turnover24h, turnover24h_usd
    """
    if not isinstance(row, Mapping):
        return False

    price = (
        _pick_first(
            row,
            "price",
            "last",
            "last_price",
            "lastPrice",
            "spot",
            "close",
            "markPrice",
            "indexPrice",
            default=0.0,
        )
        or 0.0
    )

    vol_usd = (
        _pick_first(
            row,
            "turnover_usd",
            "volume24h_usd",
            "vol_usd",
            "quoteVolume",
            "quote_volume",
            "turnover24h",
            "turnover24h_usd",
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
