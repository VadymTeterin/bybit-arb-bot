# exchanges/bybit/symbol_mapper.py
def normalize_symbol(symbol: str) -> str:
    """BTCUSDT -> BTC/USDT (spot) — найпростіша нормалізація."""
    s = symbol.replace("-", "").replace("_", "").upper()
    if s.endswith("USDT"):
        return f"{s[:-4]}/USDT"
    return symbol.upper()
