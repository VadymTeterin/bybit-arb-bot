"""
Призначення файлу:
- Додатково перевірити роботу фільтра ліквідності enough_liquidity на типових кейсах.
- Тести не торкаються мережі; працюють зі штучними рядами (dict).
"""

from src.core.filters.liquidity import enough_liquidity


def test_enough_liquidity_passes_when_price_and_volume_ok():
    """
    Тест призначений для перевірки ПОЗИТИВНОГО кейсу:
    - Ціна >= min_price
    - Добовий обіг >= min_vol
    Очікування: функція повертає True (ряд ліквідний).
    """
    row = {"price": 2.5, "turnover_usd": 15_000_000}
    assert enough_liquidity(row, 10_000_000, 0.001) is True


def test_enough_liquidity_fails_when_volume_low():
    """
    Тест перевіряє ВІДСІК за низьким обігом:
    - Обіг < min_vol при нормальній ціні.
    Очікування: False.
    """
    row = {"price": 10.0, "turnover_usd": 500_000}
    assert enough_liquidity(row, 1_000_000, 0.001) is False


def test_enough_liquidity_fails_when_price_low():
    """
    Тест перевіряє ВІДСІК за низькою ціною:
    - Ціна < min_price, навіть при великому обігу.
    Очікування: False.
    """
    row = {"price": 0.0005, "turnover_usd": 50_000_000}
    assert enough_liquidity(row, 1_000_000, 0.001) is False


def test_enough_liquidity_handles_missing_keys_gracefully():
    """
    Тест на стійкість до відсутніх ключів:
    - Немає price, проте є lastPrice.
    Очікування: функція правильно зчитає альтернативний ключ і поверне True.
    """
    row = {"lastPrice": 1.1, "turnover_usd": 12_000_000}
    assert enough_liquidity(row, 10_000_000, 0.001) is True
