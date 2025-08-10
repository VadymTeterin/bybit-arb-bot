from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from src.infra.config import load_settings
from src.core.filters.liquidity import enough_liquidity
from src.exchanges.bybit.rest import BybitRest
from src.storage import persistence


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _pick_float(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for k in keys:
        if k in row and row[k] is not None:
            try:
                return float(row[k])
            except Exception:
                continue
    return float(default)


@dataclass
class SelectionItem:
    symbol: str
    spot_price: float
    futures_price: float
    basis_pct: float
    volume_24h_usd: float


def _basis_candidates(
    client: BybitRest,
    min_price: float,
    min_vol_usd: float,
    threshold_pct: float,
) -> List[SelectionItem]:
    """
    Формуємо список кандидатів для збереження:
      - перетин SPOT/LINEAR
      - фільтр ліквідності (min_price, min_vol_usd)
      - поріг |basis| >= threshold_pct
      - сортуємо за abs(basis) (спадно)
    """
    spot_map: Dict[str, Dict[str, Any]] = client.get_spot_map()
    lin_map: Dict[str, Dict[str, Any]] = client.get_linear_map()

    out: List[SelectionItem] = []
    for sym in set(spot_map.keys()) & set(lin_map.keys()):
        sp = spot_map[sym]
        ln = lin_map[sym]

        # нормалізуємо ціну/обіг
        spot_price = _pick_float(sp, "lastPrice", "lastPriceLatest", "price")
        fut_price = _pick_float(ln, "lastPrice", "lastPriceLatest", "price")
        spot_vol = _pick_float(sp, "turnoverUsd", "turnover_usd", "turnover24h")
        lin_vol = _pick_float(ln, "turnoverUsd", "turnover_usd", "turnover24h")
        vol_min = min(spot_vol, lin_vol)

        # фільтр ліквідності
        syn = {"price": spot_price, "turnover_usd": vol_min}
        if not enough_liquidity(syn, min_vol_usd=min_vol_usd, min_price=min_price):
            continue

        if spot_price <= 0 or fut_price <= 0:
            continue

        basis_pct = (fut_price - spot_price) / spot_price * 100.0
        if abs(basis_pct) < float(threshold_pct):
            continue

        out.append(
            SelectionItem(
                symbol=sym,
                spot_price=spot_price,
                futures_price=fut_price,
                basis_pct=basis_pct,
                volume_24h_usd=vol_min,
            )
        )

    out.sort(key=lambda it: abs(it.basis_pct), reverse=True)
    return out


def run_selection(
    min_vol: Optional[float] = None,
    min_price: Optional[float] = None,
    threshold: Optional[float] = None,
    limit: int = 3,
    *,
    cooldown_sec: Optional[int] = None,
    client: Optional[BybitRest] = None,
) -> List[Dict[str, Any]]:
    """
    Запускає відбір, зберігає у БД лише ті, що не під cooldown, і повертає
    список **реально збережених** записів у вигляді dict.
    """
    s = load_settings()
    min_vol = float(min_vol if min_vol is not None else s.min_vol_24h_usd)
    min_price = float(min_price if min_price is not None else s.min_price)
    threshold = float(threshold if threshold is not None else s.alert_threshold_pct)
    cooldown_sec = int(cooldown_sec if cooldown_sec is not None else s.alert_cooldown_sec)
    limit = int(limit)

    # гарантуємо, що схема є
    persistence.init_db()

    api = client or BybitRest()
    candidates = _basis_candidates(api, min_price=min_price, min_vol_usd=min_vol, threshold_pct=threshold)
    if not candidates:
        return []

    # --- НОВЕ: фільтри allow/deny ---
    allow = set(getattr(s, "allow_symbols", []) or [])
    deny = set(getattr(s, "deny_symbols", []) or [])
    if allow:
        candidates = [it for it in candidates if it.symbol in allow]
    if deny:
        candidates = [it for it in candidates if it.symbol not in deny]
    # ---------------------------------

    saved: List[Dict[str, Any]] = []
    for it in candidates[:limit]:
        # перевіряємо cooldown
        if persistence.recent_signal_exists(it.symbol, cooldown_sec=cooldown_sec):
            continue

        # зберігаємо
        now = datetime.utcnow()
        persistence.save_signal(
            it.symbol,
            it.spot_price,
            it.futures_price,
            it.basis_pct,
            it.volume_24h_usd,
            now,
        )
        saved.append(
            {
                "symbol": it.symbol,
                "spot_price": it.spot_price,
                "futures_price": it.futures_price,
                "basis_pct": it.basis_pct,
                "volume_24h_usd": it.volume_24h_usd,
                "timestamp": now.isoformat(timespec="seconds"),
            }
        )

    return saved
