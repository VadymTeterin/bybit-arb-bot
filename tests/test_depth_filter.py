"""
Призначення файлу:
- Юніт-тести для фільтра глибини стакану (calc_window_depth_usd / has_enough_depth).
- Перевіряємо позитивні/негативні кейси, крайні випадки, різні формати книги.
"""

from src.core.filters.depth import calc_window_depth_usd, has_enough_depth


def _mk_book(bids, asks):
    # приймає рівні у форматі [(price, qty), ...] і повертає book у стилі Bybit
    return {
        "b": [[str(p), str(q)] for p, q in bids],
        "a": [[str(p), str(q)] for p, q in asks],
    }


def test_calc_window_depth_basic():
    """
    Перевіряє коректний підрахунок нотіоналу у межах ±0.5% від mid_price.
    """
    mp = 100.0
    bids = [
        (99.8, 10),
        (99.4, 10),
        (98.0, 999),
    ]  # тільки 99.8 потрапляє у вікно [99.5..100]
    asks = [(100.1, 5), (100.6, 10)]  # тільки 100.1 потрапляє у вікно [100..100.5]
    ob = _mk_book(bids, asks)

    bid_usd, ask_usd, levels = calc_window_depth_usd(ob, mp, 0.5)
    assert round(bid_usd, 2) == round(99.8 * 10, 2)
    assert round(ask_usd, 2) == round(100.1 * 5, 2)
    assert levels == 2  # 1 рівень bid + 1 рівень ask


def test_has_enough_depth_positive():
    """
    Позитивний кейс: достатній нотіонал і кількість рівнів.
    """
    mp = 50.0
    bids = [(49.9, 100), (49.8, 100)]
    asks = [(50.1, 100), (50.2, 100)]
    ob = _mk_book(bids, asks)
    assert has_enough_depth(ob, mp, min_depth_usd=3_000, window_pct=0.5, min_levels=2) is True


def test_has_enough_depth_not_enough_usd():
    """
    Відсікання за недостатнім нотіоналом на одній зі сторін.
    """
    mp = 10.0
    bids = [(9.95, 10)]  # ~99.5$
    asks = [(10.02, 10)]  # ~100.2$
    ob = _mk_book(bids, asks)
    assert has_enough_depth(ob, mp, min_depth_usd=500, window_pct=0.5, min_levels=2) is False


def test_has_enough_depth_not_enough_levels():
    """
    Відсікання за малою кількістю рівнів у вікні.
    """
    mp = 10.0
    bids = [(9.96, 1000)]
    asks = [(10.01, 1000)]
    ob = _mk_book(bids, asks)
    # нотіонал великий, але рівнів мало (2 < 3)
    assert has_enough_depth(ob, mp, min_depth_usd=1_000, window_pct=0.5, min_levels=3) is False


def test_handles_alt_format_keys():
    """
    Підтримка альтернативних ключів ("bids"/"asks").
    """
    ob = {"bids": [[99.9, 100]], "asks": [[100.1, 200]]}
    bid_usd, ask_usd, levels = calc_window_depth_usd(ob, 100.0, 0.5)
    assert bid_usd > 0 and ask_usd > 0 and levels == 2
