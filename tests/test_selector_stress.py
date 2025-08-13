"""
Призначення файлу:
- Стрес-тест селектора з великою кількістю пар (200+).
- Перевірка, що він коректно сортує за |basis| і поважає параметр limit.
"""

from types import SimpleNamespace
from src.core import selector


class _FakeBybitRest:
    """
    Фейковий клієнт Bybit REST:
    - Генерує N пар зі зростаючим basis, щоб було легко перевірити сортування і limit.
    """

    def __init__(self, n=250):
        self.n = n
        self._spot = {}
        self._linear = {}
        # будуємо штучний ринок: S1..Sn з лінійною різницею
        price = 1.0
        for i in range(1, n + 1):
            sym = f"S{i}USDT"
            spot_p = price
            fut_p = price * (1 + i / 10_000)  # дедалі більший basis
            vol = 20_000_000 + i * 1_000      # всі проходять min_vol
            self._spot[sym] = {"price": spot_p, "turnover_usd": vol}
            self._linear[sym] = {"price": fut_p, "turnover_usd": vol}
            price += 0.01

    def get_spot_map(self):
        return self._spot

    def get_linear_map(self):
        return self._linear


def test_selector_stress_sorted_and_limited(monkeypatch):
    """
    Тест призначений для перевірки:
    1) Коректності сортування кандидатів за абсолютним basis (спадаючий порядок).
    2) Поваги до параметра limit (беремо рівно top-K).
    3) Відсутності падінь на великих N (стрес).
    """

    # штучні налаштування із зниженими порогами
    fake_settings = SimpleNamespace(
        min_vol_24h_usd=10_000_000,
        min_price=0.001,
        alert_threshold_pct=0.2,   # щоб більшість пар пройшли
        alert_cooldown_sec=0,
        allow_symbols=[],
        deny_symbols=[],
        db_path=":memory:",
    )
    monkeypatch.setattr(selector, "load_settings", lambda: fake_settings)

    # відключаємо реальну БД
    saved = []
    monkeypatch.setattr(selector.persistence, "init_db", lambda: None)
    monkeypatch.setattr(selector.persistence, "recent_signal_exists", lambda symbol, cooldown_sec: False)
    monkeypatch.setattr(selector.persistence, "save_signal", lambda *args, **kwargs: saved.append(args))

    fake = _FakeBybitRest(n=240)
    res = selector.run_selection(limit=7, client=fake)

    # очікуємо рівно 7 елементів
    assert len(res) == 7

    # перевіряємо, що basis впорядкований за спаданням за модулем
    basis_list = [abs(x["basis_pct"]) for x in res]
    assert basis_list == sorted(basis_list, reverse=True)

    # перевіряємо, що збережено також рівно 7
    assert len(saved) == 7
