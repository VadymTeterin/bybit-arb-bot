from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


def _to_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _levels_in_window(levels: Iterable[Tuple[float, float]], lo: float, hi: float) -> List[Tuple[float, float]]:
    """Фільтрує рівні книги за ціновим вікном [lo, hi]."""
    out: List[Tuple[float, float]] = []
    for p, q in levels:
        fp, fq = _to_float(p), _to_float(q)
        if fp >= lo and fp <= hi:
            out.append((fp, fq))
    return out


def _sum_notional(levels: Iterable[Tuple[float, float]]) -> float:
    """Сума ціна*кількість по рівнях."""
    s = 0.0
    for p, q in levels:
        s += _to_float(p) * _to_float(q)
    return s


def _normalize_ob(orderbook: Dict) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Нормалізує формат книги до двох списків bids/asks у вигляді [(price, qty), ...].
    Підтримує варіанти:
      - Bybit REST/WS: {"b": [["price","qty"], ...], "a": [["price","qty"], ...]}
      - Узагальнено:  {"bids": [[p,q],...], "asks": [[p,q],...]}
    """
    bids_raw = orderbook.get("b") or orderbook.get("bids") or []
    asks_raw = orderbook.get("a") or orderbook.get("asks") or []
    bids = [( _to_float(r[0]), _to_float(r[1]) ) for r in bids_raw if isinstance(r, (list, tuple)) and len(r) >= 2]
    asks = [( _to_float(r[0]), _to_float(r[1]) ) for r in asks_raw if isinstance(r, (list, tuple)) and len(r) >= 2]
    return bids, asks


def calc_window_depth_usd(orderbook: Dict, mid_price: float, window_pct: float) -> Tuple[float, float, int]:
    """
    Розраховує сумарний нотіонал у межах ±window_pct від mid_price.
    Повертає: (bid_usd, ask_usd, levels_in_window_total).
    """
    mp = _to_float(mid_price)
    if mp <= 0:
        return 0.0, 0.0, 0

    bids, asks = _normalize_ob(orderbook)

    lo_bid = mp * (1.0 - _to_float(window_pct) / 100.0)
    hi_bid = mp  # bids не вище mid
    lo_ask = mp
    hi_ask = mp * (1.0 + _to_float(window_pct) / 100.0)

    bids_w = _levels_in_window(bids, lo_bid, hi_bid)
    asks_w = _levels_in_window(asks, lo_ask, hi_ask)

    bid_usd = _sum_notional(bids_w)
    ask_usd = _sum_notional(asks_w)
    levels_total = len(bids_w) + len(asks_w)

    return bid_usd, ask_usd, levels_total


def has_enough_depth(
    orderbook: Dict,
    mid_price: float,
    *,
    min_depth_usd: float,
    window_pct: float,
    min_levels: int,
) -> bool:
    """
    Перевірка, що в межах ±window_pct від mid_price є достатня глибина:
      - min(bid_usd, ask_usd) >= min_depth_usd
      - загальна кількість рівнів у вікні >= min_levels
    """
    bid_usd, ask_usd, levels = calc_window_depth_usd(orderbook, mid_price, window_pct)
    if bid_usd <= 0 or ask_usd <= 0:
        return False
    if min(bid_usd, ask_usd) < float(min_depth_usd):
        return False
    if levels < int(min_levels):
        return False
    return True
