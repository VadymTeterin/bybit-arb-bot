from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.core.filters.liquidity import enough_liquidity
from src.infra.config import load_settings

# Імпорт залишаємо: тести можуть monkeypatch-ити selector.has_enough_depth
try:
    from src.core.filters.depth import has_enough_depth  # type: ignore
except Exception:
    has_enough_depth = None  # type: ignore[assignment]

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


def _mget(obj: Any, key: str, default: Any = None) -> Any:
    """
    Безпечне отримання значення за ключем із Mapping або об'єкта з методом get.
    Уникаємо `dict().get`, який у mypy має Never-тизи.
    """
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    get_fn = getattr(obj, "get", None)
    if callable(get_fn):
        try:
            return get_fn(key, default)  # type: ignore[misc]
        except Exception:
            return default
    return default


def _parse_symbols_value(v: Any) -> list[str]:
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
    # Використовуємо Any, бо клієнт може повертати TypedDict/звичні dict-и з різними наборами ключів
    spot_map: Mapping[str, Any],
    linear_map: Mapping[str, Any],
) -> list[_Pair]:
    out: list[_Pair] = []
    for sym, srow in spot_map.items():
        if sym not in linear_map:
            continue
        frow = linear_map[sym]
        out.append(
            _Pair(
                symbol=sym,
                spot=_to_float(_mget(srow, "price", 0.0)),
                fut=_to_float(_mget(frow, "price", 0.0)),
                vol_usd=_to_float(_mget(srow, "turnover_usd", 0.0)),
            )
        )
    return out


def _allowed(symbol: str, allow: list[str], deny: list[str]) -> bool:
    u = symbol.upper()
    if u in (x.upper() for x in deny):
        return False
    if allow:
        return u in (x.upper() for x in allow)
    return True


def run_selection(
    *,
    min_vol: float | None = None,
    min_price: float | None = None,
    threshold: float | None = None,
    limit: int = 3,
    cooldown_sec: int | None = None,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """
    Запускає відбір SPOT vs LINEAR, фільтрує за ціною/ліквідністю/порогом,
    застосовує allow/deny та cooldown, опційно — фільтр глибини, зберігає у БД і повертає реально збережені записи.
    """
    s = load_settings()
    min_vol = s.min_vol_24h_usd if min_vol is None else float(min_vol)
    min_price = s.min_price if min_price is None else float(min_price)
    threshold = s.alert_threshold_pct if threshold is None else float(threshold)
    cooldown_sec = s.alert_cooldown_sec if cooldown_sec is None else int(cooldown_sec)

    # --- параметри depth-фільтра (беквард-сумісно) ---
    # Якщо їх немає у налаштуваннях, depth-фільтр буде вимкнений.
    min_depth_usd = getattr(s, "min_depth_usd", None)
    depth_window_pct = getattr(s, "depth_window_pct", None)
    min_depth_levels = getattr(s, "min_depth_levels", None)

    # флаг: чи можемо застосувати depth-фільтр
    depth_enabled = (
        (min_depth_usd is not None)
        and (depth_window_pct is not None)
        and (min_depth_levels is not None)
        and (has_enough_depth is not None)
    )

    # підтримуємо ОБИДВА варіанти allow/deny:
    if hasattr(s, "allow_list"):
        allow: list[str] = s.allow_list  # type: ignore[assignment]
    else:
        raw_allow = getattr(s, "allow_symbols", "")
        allow = raw_allow if isinstance(raw_allow, list) else _parse_symbols_value(raw_allow)

    if hasattr(s, "deny_list"):
        deny: list[str] = s.deny_list  # type: ignore[assignment]
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

    # чи є у клієнта методи ордербука (для depth-фільтра)?
    client_has_orderbook = all(hasattr(client, name) for name in ("get_orderbook_spot", "get_orderbook_linear"))

    candidates: list[_Pair] = []
    for p in pairs:
        # базові фільтри (ліквідність/ціна/поріг + allow/deny)
        spot_row = {"price": p.spot, "turnover_usd": p.vol_usd}
        if not enough_liquidity(spot_row, min_vol, min_price):
            continue
        if p.spot < min_price or p.fut <= 0:
            continue

        # --- опційний depth-фільтр ---
        if depth_enabled and client_has_orderbook:
            try:
                ob_spot = client.get_orderbook_spot(p.symbol, limit=200)
                ob_linear = client.get_orderbook_linear(p.symbol, limit=200)
                if not has_enough_depth(
                    ob_spot,
                    p.spot,
                    min_depth_usd=float(min_depth_usd),  # type: ignore[arg-type]
                    window_pct=float(depth_window_pct),  # type: ignore[arg-type]
                    min_levels=int(min_depth_levels),  # type: ignore[arg-type]
                ):
                    continue
                if not has_enough_depth(
                    ob_linear,
                    p.fut,
                    min_depth_usd=float(min_depth_usd),  # type: ignore[arg-type]
                    window_pct=float(depth_window_pct),  # type: ignore[arg-type]
                    min_levels=int(min_depth_levels),  # type: ignore[arg-type]
                ):
                    continue
            except Exception:
                # У випадку проблем із ордербуком — не завалюємо відбір, просто пропускаємо depth-чек.
                pass

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
    saved: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
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


# --- Phase 6.3.3: optional liquidity filter ---------------------------------


def _apply_liquidity_if_enabled(
    rows: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """
    Застосувати фільтр ліквідності, якщо він увімкнений через env.
    Безпечно: якщо вимкнено або сталася помилка — повертає rows як є.
    Toggle читається з src.infra.liquidity_env.is_liquidity_enabled().
    (На цьому кроці хелпер лише додається, у пайплайн відбору ще не підключаємо.)
    """
    try:
        from src.infra.liquidity_env import is_liquidity_enabled

        if not is_liquidity_enabled():
            return list(rows)
        from src.core.filters import make_liquidity_predicate

        pred = make_liquidity_predicate()
        return [r for r in rows if pred(r)]
    except Exception:
        # Нічого не ламаємо у проді: фільтр пропускаємо.
        return list(rows)
