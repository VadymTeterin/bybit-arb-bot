# exchanges/bybit/symbol_mapper.py
from __future__ import annotations

# Список відомих квот — можна розширювати за потреби
_KNOWN_QUOTES = ("USDT", "USDC", "BTC", "USD", "EUR")


def normalize_symbol(symbol: str) -> str:
    """
    Нормалізує символ до вигляду BASE/QUOTE.
    Приклади:
      - "BTCUSDT"   -> "BTC/USDT"
      - "BTC/USDT"  -> "BTC/USDT"
      - "btc_usdt"  -> "BTC/USDT"
      - "btc-usdt"  -> "BTC/USDT"
    """
    s = symbol.strip().upper().replace("-", "/").replace("_", "/")

    # Якщо вже є слеш — просто привести до "BASE/QUOTE"
    if "/" in s:
        base, quote = s.split("/", 1)
        return f"{base}/{quote}"

    # Якщо слеша немає — спробувати виділити квоту за відомим списком
    for q in _KNOWN_QUOTES:
        if s.endswith(q):
            base = s[: -len(q)]
            return f"{base}/{q}"

    # Фолбек — повертаємо як є (краще так, ніж зламати формат)
    return s


def to_bybit_symbol(symbol: str) -> str:
    """
    Перетворює внутрішній формат "BASE/QUOTE" у BYBIT-формат "BASEQUOTE".
    """
    s = symbol.strip().upper()
    if "/" in s:
        base, quote = s.split("/", 1)
        return f"{base}{quote}"
    return s.replace("-", "").replace("_", "")
