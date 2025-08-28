"""
Призначення файлу:
- Інтеграційний тест: селектор повинен відсікати інструменти з недостатньою глибиною стакану.
- Працює без мережі: мокаються orderbook-и та конфіг.
"""

from types import SimpleNamespace

from src.core import selector


class _FakeBybitRest:
    """
    Фейковий клієнт Bybit REST:
    - дає мінімально потрібні мапи ціни/обігу;
    - надає orderbook-методи, щоб selector увімкнув depth-фільтр.
    """

    def __init__(self):
        self._spot = {
            "AAAUSDT": {"price": 100.0, "turnover_usd": 20_000_000},
            "BBBUSDT": {"price": 5.0, "turnover_usd": 25_000_000},
        }
        self._linear = {
            "AAAUSDT": {"price": 101.0, "turnover_usd": 22_000_000},
            "BBBUSDT": {"price": 5.05, "turnover_usd": 26_000_000},
        }
        # довільні "порожні" книги — реальний результат підміняємо monkeypatch-ом has_enough_depth
        self._ob = {"b": [], "a": []}

    def get_spot_map(self):
        return self._spot

    def get_linear_map(self):
        return self._linear

    def get_orderbook_spot(self, symbol: str, limit: int = 200):
        return self._ob

    def get_orderbook_linear(self, symbol: str, limit: int = 200):
        return self._ob


def test_selector_filters_by_depth(monkeypatch):
    """
    Якщо has_enough_depth повертає False для будь-якого з ринків — пара має бути відсіяна.
    Тут ми штучно примушуємо has_enough_depth = True для AAAUSDT, а = False для BBBUSDT.
    """

    fake_settings = SimpleNamespace(
        min_vol_24h_usd=10_000_000,
        min_price=0.001,
        alert_threshold_pct=0.5,
        alert_cooldown_sec=0,
        allow_symbols=[],
        deny_symbols=[],
        db_path=":memory:",
        # ДОДАНО: параметри depth-фільтра, щоб він увімкнувся
        min_depth_usd=1_000,
        depth_window_pct=0.5,
        min_depth_levels=1,
    )
    monkeypatch.setattr(selector, "load_settings", lambda: fake_settings)

    # Відключаємо реальну БД
    saved = []
    monkeypatch.setattr(selector.persistence, "init_db", lambda: None)
    monkeypatch.setattr(
        selector.persistence, "recent_signal_exists", lambda symbol, cooldown_sec: False
    )
    monkeypatch.setattr(selector.persistence, "save_signal", lambda *a, **k: saved.append(a))

    # Мокаємо has_enough_depth так, щоб:
    #  - для AAAUSDT → True (mid_price ~100)
    #  - для BBBUSDT → False (mid_price ~5)
    def fake_has_enough_depth(orderbook, mid_price, **kwargs):
        return mid_price >= 100.0

    monkeypatch.setattr(selector, "has_enough_depth", fake_has_enough_depth, raising=False)

    fake = _FakeBybitRest()
    res = selector.run_selection(limit=5, client=fake)

    symbols = [r["symbol"] for r in res]
    # Очікуємо: залишився лише AAAUSDT (BBB відсіяний depth-фільтром)
    assert symbols == ["AAAUSDT"]
