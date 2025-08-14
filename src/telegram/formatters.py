# src/telegram/formatters.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def _fmt_usd(x: Optional[float]) -> str:
    if x is None:
        return "n/a"
    try:
        x = float(x)
    except Exception:
        return "n/a"
    if x >= 1_000_000_000:
        return f"${x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"${x/1_000:.2f}K"
    return f"${x:.2f}"


def _fmt_price(x: Optional[float]) -> str:
    if x is None:
        return "n/a"
    try:
        x = float(x)
    except Exception:
        return "n/a"
    if x >= 1000:
        return f"{x:,.2f}"
    if x >= 1:
        return f"{x:.2f}"
    return f"{x:.6f}"


def _fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "n/a"
    try:
        return f"{float(x)*100:.2f}%"
    except Exception:
        return "n/a"


def _fmt_ts(ts_unix: Optional[float]) -> str:
    if not ts_unix:
        return "n/a"
    try:
        ts = float(ts_unix)
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return "n/a"


def format_signal(
    *,
    symbol_spot: str,
    symbol_linear: str,
    spread_pct: float,
    spot_price: float,
    mark_price: float,
    vol_24h: Optional[float],
    basis: float,
    funding_rate: Optional[float] = None,
    next_funding_time: Optional[float] = None,
) -> str:
    """
    Базовий форматер повідомлення (Markdown) для Telegram/CLI.
    Поля funding опційні: якщо даних немає — рядки не показуються.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "*Arbitrage Signal*",
        f"`{ts}`",
        f"Pair: *{symbol_spot}*  ↔  *{symbol_linear}*",
        f"Spread: *{float(spread_pct):.2f}%*",
        f"Spot: `{_fmt_price(spot_price)}`  •  Mark: `{_fmt_price(mark_price)}`",
        f"24h Vol: `{_fmt_usd(vol_24h)}`",
        f"Basis: `{float(basis):.6f}`",
    ]
    if funding_rate is not None:
        lines.append(f"Funding (prev): *{_fmt_pct(funding_rate)}*")
    if next_funding_time is not None:
        lines.append(f"Next funding: `{_fmt_ts(next_funding_time)}`")
    return "\n".join(lines)


# --- Сумісні назви, які можуть використовуватись у інших частинах коду/тестах ---
# Старе ім'я, яке могли імпортувати тести/модулі:
format_signal_markdown = format_signal
# Те, що зараз просить dev/test_tg_sender.py:
def format_arbitrage_alert(
    *,
    symbol_spot: str,
    symbol_linear: str,
    spread_pct: float,
    spot_price: float,
    mark_price: float,
    vol_24h: Optional[float],
    basis: float,
    funding_rate: Optional[float] = None,
    next_funding_time: Optional[float] = None,
) -> str:
    # Делегуємо в наш єдиний форматер, щоб уникати дубляжу логіки
    return format_signal(
        symbol_spot=symbol_spot,
        symbol_linear=symbol_linear,
        spread_pct=spread_pct,
        spot_price=spot_price,
        mark_price=mark_price,
        vol_24h=vol_24h,
        basis=basis,
        funding_rate=funding_rate,
        next_funding_time=next_funding_time,
    )


__all__ = [
    "format_signal",
    "format_signal_markdown",
    "format_arbitrage_alert",
]
