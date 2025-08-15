"""
Призначення файлу:
- "End-to-end" (інтеграційний) тест для run_selection без мережі:
  * Перевіряє послідовність: build_pairs -> фільтри -> сортування -> збереження.
  * Переконується, що cooldown працює (завдяки recent_signal_exists).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.core import selector


class _FakeBybitRest:
    """
    Фейковий клієнт Bybit REST з мінімальним набором даних для інтеграційного проходу.
    """

    def __init__(self):
        self._spot = {
            "AAAUSDT": {"price": 2.0, "turnover_usd": 12_000_000},
            "BBBUSDT": {"price": 5.0, "turnover_usd": 25_000_000},
            "PENNYUSDT": {
                "price": 0.0009,
                "turnover_usd": 50_000,
            },  # має відсіктись за ціною/обігом
        }
        self._linear = {
            "AAAUSDT": {"price": 2.04, "turnover_usd": 11_000_000},  # ~2%
            "BBBUSDT": {"price": 5.10, "turnover_usd": 26_000_000},  # ~2%
            "PENNYUSDT": {"price": 0.0010, "turnover_usd": 60_000},
        }

    def get_spot_map(self):
        return self._spot

    def get_linear_map(self):
        return self._linear


def test_selector_end_to_end_with_cooldown(monkeypatch):
    """
    Тест призначений для перевірки:
    - Повного проходу run_selection.
    - Відсікання неліківідної/занадто дешевої монети.
    - Поваги cooldown: якщо для символу є свіжий запис, він не буде збережений вдруге.
    """
    fake_settings = SimpleNamespace(
        min_vol_24h_usd=10_000_000,
        min_price=0.001,
        alert_threshold_pct=1.0,
        alert_cooldown_sec=300,  # 5 хв
        allow_symbols=[],
        deny_symbols=[],
        db_path=":memory:",
    )
    monkeypatch.setattr(selector, "load_settings", lambda: fake_settings)

    # Імітуємо БД: AAA — наче вже збережена 2 хв тому (ще під cooldown)
    saved = []
    now = datetime.now(timezone.utc)
    recently_saved = {"AAAUSDT": now - timedelta(seconds=120)}  # 2 хв тому

    def fake_init_db():
        return None

    def fake_recent_signal_exists(symbol, cooldown_sec):
        ts = recently_saved.get(symbol)
        if not ts:
            return False
        return (now - ts).total_seconds() < cooldown_sec

    def fake_save_signal(*args, **kwargs):
        saved.append(args)

    monkeypatch.setattr(selector.persistence, "init_db", fake_init_db)
    monkeypatch.setattr(
        selector.persistence, "recent_signal_exists", fake_recent_signal_exists
    )
    monkeypatch.setattr(selector.persistence, "save_signal", fake_save_signal)

    fake = _FakeBybitRest()
    res = selector.run_selection(limit=5, client=fake)

    # AAA повинна відсіятись кулдауном, BBB — пройти, PENNY — ні (дешева/неліквідна)
    symbols = [r["symbol"] for r in res]
    assert "BBBUSDT" in symbols
    assert "AAAUSDT" not in symbols
    assert "PENNYUSDT" not in symbols

    # Переконуємося, що збережено лише BBB
    assert len(saved) == 1
    assert saved[0][0] == "BBBUSDT"
