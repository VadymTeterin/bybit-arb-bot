from datetime import datetime, timezone


def format_arbitrage_alert(symbol_a: str, symbol_b: str, spread_pct: float, vol_24h: float, basis: float) -> str:
    """
    Форматує текст повідомлення для Telegram у стилі:
     Arbitrage Signal
     2025-08-14 12:34:56 UTC
     Pair: BTCUSDT  BTCUSDT:PERP
     Spread: 0.85%
     24h Vol: 123,456,789
     Basis: 0.0012
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
def format_signal(
    symbol_a: str,
    symbol_b: str,
    spread_pct: float,
    vol_24h: float,
    basis: float,
) -> str:
    \"\"\"Зворотно-сумісний враппер для старих викликів.
    Делегує у format_arbitrage_alert(...).\"\"\"
    return format_arbitrage_alert(
        symbol_a=symbol_a,
        symbol_b=symbol_b,
        spread_pct=spread_pct,
        vol_24h=vol_24h,
        basis=basis,
    )
