from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional


def _fmt_usd(x: Optional[float]) -> str:
    if x is None or math.isnan(x):
        return "n/a"
    # Дружнє форматування з розрядами
    if x >= 1_000_000_000:
        return f"${x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"${x/1_000:.2f}K"
    return f"${x:,.2f}"


def _fmt_price(x: Optional[float]) -> str:
    if x is None or math.isnan(x):
        return "n/a"
    # 2–6 знаків після коми залежно від величини
    if x >= 1000:
        return f"{x:,.2f}"
    if x >= 1:
        return f"{x:,.2f}"
    return f"{x:.6f}"


def _fmt_pct(x: Optional[float]) -> str:
    if x is None or math.isnan(x):
        return "n/a"
    sign = "+" if x > 0 else ""
    return f"{sign}{x:.2f}%"

def _fmt_time(ts: Optional[float]) -> str:
    dt = datetime.fromtimestamp(ts or 0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def format_signal(
    *,
    symbol: str,
    spot_price: Optional[float],
    mark_price: Optional[float],
    basis_pct: Optional[float],
    vol24h_usd: Optional[float],
    ts: Optional[float] = None,
) -> str:
    """
    Формат повідомлення для Telegram/логів.
    """
    return (
        "🔔 *Arbitrage Signal*\n"
        f"*Symbol*: `{symbol}`\n"
        f"*Spot*: { _fmt_price(spot_price) }\n"
        f"*Futures (mark)*: { _fmt_price(mark_price) }\n"
        f"*Basis*: {_fmt_pct(basis_pct)}\n"
        f"*24h Vol*: { _fmt_usd(vol24h_usd) }\n"
        f"*Time*: {_fmt_time(ts)}"
    )
