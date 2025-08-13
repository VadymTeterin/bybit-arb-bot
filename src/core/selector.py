from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from src.infra.config import load_settings
from src.core.filters.liquidity import enough_liquidity
from src.storage import persistence


@dataclass
class _Pair:
    symbol: str
    spot: float
    fut: float
    vol_usd: float

    @property
    def basis_pct(self) -> float:
        if self.spot <= 0:
            return 0.0
        return (self.fut / self.spot - 1.0) * 100.0


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _parse_symbols_value(v: Any) -> List[str]:
    """
    Приймає None / list / рядок з JSON-масивом або CSV.
    Повертає список аперкейс-символів без порожніх елементів.
    """
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x).strip().upper() for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        # JSON-масив
        if s.startswith("[") and s.endswith("]"):
            try:
                import json

                arr = json.loads(s)
                if isinstance(arr, list):
                    return [str(x).strip().upper() for x in arr if str(x).strip()]
            except Exception:
                # якщо не JSON — впадемо у CSV
                pass
        parts = [p.strip() for p in s.replace(";", ",").split(",") if p.strip()]
        return [p.upper() for p in parts]
    return []


def _build_pairs(
    spot_map: Mapping[str, Mapping[str, float]],
    linear_map: Mapping[str, Mapping[str, float]],
) -> List[_Pair]:
    out: List[_Pair] = []
    for sym, srow in spot_map.items():
        if sym not in linear_map:
            continue
        frow = linear_map[sym]
        out.append(
            _Pair(
                symbol=sym,
                spot=_to_float(srow.get("price", 0.0)),
                fut=_to_float(frow.get("price", 0.0)),
                vol_usd=_to_float(srow.get("turnover_usd", 0.0)),
            )
        )
    return out


def _allowed(symbol: str, allow: List[str], deny: List[str]) -> bool:
    u = symbol.upper()
    if u in (x.upper() for x in deny):
        return False
    if allow:
        return u in (x.upper() for x in allow)
    return True


def run_selection(
    *,
    min_vol: Optional[float] = None,
    min_price: Optional[float] = None,
    threshold: Optional[float] = None,
    limit: int = 3,
    cooldown_sec: Optional[int] = None,
    client: Any | None = None,
) -> List[Dict[str, Any]]:
    """
    Запускає відбір SPOT vs LINEAR, фільтрує за ціною/ліквідністю/порогом,
    застосовує allow/deny та cooldown, зберігає у БД і повертає реально збережені записи.
    """
    s = load_settings()
    min_vol = s.min_vol_24h_usd if min_vol is None else float(min_vol)
    min_price = s.min_price if min_price is None else float(min_price)
    threshold = s.alert_threshold_pct if threshold is None else float(threshold)
    cooldown_sec = s.alert_cooldown_sec if cooldown_sec is None else int(cooldown_sec)

    # підтримуємо ОБИДВА варіанти:
    # - тести можуть підмінити SimpleNamespace з list
    # - .env дає сирий рядок, який ми парсимо
    if hasattr(s, "allow_list"):
        allow: List[str] = getattr(s, "allow_list")  # type: ignore[assignment]
    else:
        raw_allow = getattr(s, "allow_symbols", "")
        allow = raw_allow if isinstance(raw_allow, list) else _parse_symbols_value(raw_allow)

    if hasattr(s, "deny_list"):
        deny: List[str] = getattr(s, "deny_list")  # type: ignore[assignment]
    else:
        raw_deny = getattr(s, "deny_symbols", "")
        deny = raw_deny if isinstance(raw_deny, list) else _parse_symbols_value(raw_deny)

    # відкладений імпорт реального клієнта
    if client is None:
        from src.exchanges.bybit.rest import BybitRest

        client = BybitRest()

    spot_map = client.get_spot_map()
    linear_map = client.get_linear_map()

    pairs = _build_pairs(spot_map, linear_map)

    # базові фільтри (ліквідність/мін.ціна/поріг + allow/deny)
    candidates: List[_Pair] = []
    for p in pairs:
        # enough_liquidity очікує мапу з ціною та обігом — формуємо ряд
        spot_row = {"price": p.spot, "turnover_usd": p.vol_usd}
        if not enough_liquidity(spot_row, min_vol, min_price):
            continue
        if p.spot < min_price or p.fut <= 0:
            continue
        if abs(p.basis_pct) < threshold:
            continue
        if not _allowed(p.symbol, allow, deny):
            continue
        candidates.append(p)

    # сортування та ліміт
    candidates.sort(key=lambda x: abs(x.basis_pct), reverse=True)
    candidates = candidates[: max(1, int(limit))]

    # збереження у БД (з урахуванням cooldown)
    persistence.init_db()
    saved: List[Dict[str, Any]] = []
    now = datetime.utcnow()
    for p in candidates:
        if persistence.recent_signal_exists(p.symbol, cooldown_sec):
            continue
        persistence.save_signal(p.symbol, p.spot, p.fut, p.basis_pct, p.vol_usd, now)
        saved.append(
            {
                "symbol": p.symbol,
                "spot_price": p.spot,
                "futures_price": p.fut,
                "basis_pct": p.basis_pct,
                "turnover_usd": p.vol_usd,
                "ts": now.isoformat(),
            }
        )
    return saved
