"""
Призначення файлу:
- Юніт-тести для внутрішньої утиліти _parse_symbols_value у selector.
- Перевіряємо підтримку CSV/JSON/списку та різні крайні випадки.
"""

from src.core.selector import _parse_symbols_value


def test_parse_symbols_value_csv():
    """
    Тест призначений для перевірки парсингу CSV-рядка allow/deny:
    - Роздільники кома/крапка з комою;
    - Нормалізація пробілів;
    - Переведення до верхнього регістру.
    """
    s = "ethusdt,  xrpusdt ; btcusdt"
    res = _parse_symbols_value(s)
    assert res == ["ETHUSDT", "XRPUSDT", "BTCUSDT"]


def test_parse_symbols_value_json_array():
    """
    Тест перевіряє, що JSON-масив рядків коректно парситься в список.
    """
    s = '["ethusdt", "xrpusdt", "btcusdt"]'
    res = _parse_symbols_value(s)
    assert res == ["ETHUSDT", "XRPUSDT", "BTCUSDT"]


def test_parse_symbols_value_list_passthrough():
    """
    Тест на випадок, коли приходить уже готовий list:
    - Має повернутися той самий набір, нормалізований у UPPERCASE і без порожніх елементів.
    """
    res = _parse_symbols_value([" ethusdt ", "  ", "xrpusdt"])
    assert res == ["ETHUSDT", "XRPUSDT"]


def test_parse_symbols_value_empty_and_none():
    """
    Тест краєвих випадків для порожніх значень:
    - None, "", непідтримувані типи => порожній список.
    """
    assert _parse_symbols_value(None) == []
    assert _parse_symbols_value("") == []
    assert _parse_symbols_value(123) == []
