from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional


def _fmt_usd(x: Optional[float]) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if x >= 1_000_000_000:
        return f"${x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"${x/1_000:.2f}K"
    return f"${x:,.0f}"


def _fmt_price(x: Optional[float]) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if x >= 1000:
        return f"{x:,.2f}"
    if x >= 1:
        return f"{x:,.2f}"
    return f"{x:.6f}"


def _fmt_pct(x: Optional[float]) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    sign = "+" if x > 0 else ""
    return f"{sign}{x:.2f}%"


def _fmt_time(ts: Optional[float]) -> str:
    if not ts:
        return "n/a"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def format_signal(
    *,
    symbol: str,
    spot_price: Optional[float],
    mark_price: Optional[float],
    basis_pct: Optional[float],
    vol24h_usd: Optional[float],
    ts: Optional[float] = None,
    # ---- NEW (optional) ----
    funding_rate: Optional[float] = None,        # частка: 0.0001 == 0.01%
    next_funding_time: Optional[float] = None,   # UNIX seconds
) -> str:
    """
    Формат повідомлення для Telegram/логів.
    Нові поля опційні: якщо не задані — рядок з funding не з'являється.
    """
    lines = [
        "🔔 *Arbitrage Signal*",
        f"*Symbol*: `{symbol}`",
        f"*Spot*: {_fmt_price(spot_price)}",
        f"*Futures (mark)*: {_fmt_price(mark_price)}",
        f"*Basis*: {_fmt_pct(basis_pct)}",
        f"*24h Vol*: {_fmt_usd(vol24h_usd)}",
        f"*Time*: {_fmt_time(ts)}",
    ]
    if funding_rate is not None:
        # funding_rate тут — частка. Переведемо у % для відображення.
        lines.insert(6, f"*Funding (prev)*: {_fmt_pct((funding_rate or 0.0) * 100.0)}")
        if next_funding_time:
            lines.insert(7, f"*Next funding*: {_fmt_time(next_funding_time)}")
    return "\n".join(lines)


def format_arbitrage_alert(
    symbol_a: str,
    symbol_b: str,
    spread_pct: float,
    vol_24h: float,
    basis: float,
) -> str:
    """
    Класичний HTML‑формат для альтернативних каналів (залишаємо як був).
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f" <b>Arbitrage Signal</b>\n"
        f" {ts}\n"
        f" Pair: <b>{symbol_a}</b>  <b>{symbol_b}</b>\n"
        f" Spread: <b>{spread_pct:.2f}%</b>\n"
        f" 24h Vol: <b>{vol_24h:,.0f}</b>\n"
        f" Basis: <b>{basis:.4f}</b>\n"
    )
