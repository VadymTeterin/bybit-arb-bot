from __future__ import annotations

from typing import Any, Dict

from src.infra.notify_telegram import send_telegram
from src.telegram.formatters import format_arbitrage_alert


def _to_float(value: Any, default: float = 0.0) -> float:
    """Безпечне перетворення у float з дефолтом."""
    try:
        if value is None:
            return default
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _to_str(value: Any, default: str = "") -> str:
    """Безпечне перетворення у str з дефолтом."""
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def send_arbitrage_alert(signal: Any, enabled: bool = True) -> bool:
    """
    Акуратно формує повідомлення та надсилає його у Telegram через адаптер.
    Нічого не ламає: якщо полів не вистачає або disabled, повертає False.

    Очікувані поля у форматтері:
      - symbol_spot: str
      - symbol_linear: str
      - spread_pct: float
      - vol_24h: float
      - basis: float
    Ми ж підстраховуємося і збираємо їх із різних можливих назв.
    """
    if not enabled or signal is None:
        return False

    # Спробуємо зібрати імена інструментів під очікувані параметри форматтера
    # Припускаємо, що старі назви могли бути: symbol_a/base та symbol_b/quote
    symbol_spot = (
        getattr(signal, "symbol_spot", None)
        or getattr(signal, "symbol_a", None)
        or getattr(signal, "base", None)
        or ""
    )
    symbol_linear = (
        getattr(signal, "symbol_linear", None)
        or getattr(signal, "symbol_b", None)
        or getattr(signal, "quote", None)
        or ""
    )

    spread_pct = _to_float(getattr(signal, "spread_pct", 0.0), 0.0)
    vol_24h = _to_float(getattr(signal, "vol_24h", getattr(signal, "vol24h", 0.0)), 0.0)
    basis = _to_float(getattr(signal, "basis", getattr(signal, "basis_pct", 0.0)), 0.0)

    # Пакуємо параметри у dict[str, Any] — це зручно і не заважає mypy при **kwargs
    params: Dict[str, Any] = {
        "symbol_spot": _to_str(symbol_spot),
        "symbol_linear": _to_str(symbol_linear),
        "spread_pct": spread_pct,
        "vol_24h": vol_24h,
        "basis": basis,
    }

    # Важливо: format_arbitrage_alert очікує саме symbol_spot / symbol_linear
    text = format_arbitrage_alert(**params)  # type: ignore[call-arg]

    return send_telegram(text, enabled=True)
