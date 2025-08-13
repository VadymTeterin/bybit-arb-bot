from typing import Any

from src.telegram.formatters import format_arbitrage_alert
from src.infra.notify_telegram import send_telegram


def send_arbitrage_alert(signal: Any, enabled: bool = True) -> bool:
    """
    Акуратно формує повідомлення та надсилає його у Telegram через адаптер.
    Нічого не ламає: якщо полів не вистачає або disabled, повертає False.
    """
    if not enabled or signal is None:
        return False

    # Підстраховуємо назви полів, щоб не ламати існуючі структури
    symbol_a = getattr(signal, "symbol_a", None) or getattr(signal, "base", "")
    symbol_b = getattr(signal, "symbol_b", None) or getattr(signal, "quote", "")
    spread_pct = float(getattr(signal, "spread_pct", 0.0))
    vol_24h = float(getattr(signal, "vol_24h", 0.0))
    basis = float(getattr(signal, "basis", 0.0))

    text = format_arbitrage_alert(
        symbol_a=symbol_a,
        symbol_b=symbol_b,
        spread_pct=spread_pct,
        vol_24h=vol_24h,
        basis=basis,
    )
    return send_telegram(text, enabled=True)
