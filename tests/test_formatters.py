# tests/test_formatters.py

from src.telegram.formatters import format_signal_markdown
from datetime import datetime, timezone

def test_format_with_and_without_funding():
    # Без funding
    txt = format_signal_markdown(
        symbol_spot="BTCUSDT",
        symbol_linear="BTCUSDT",
        spread_pct=0.42,
        spot_price=62850.12,
        mark_price=62823.44,
        vol_24h=2_100_000_000.0,
        basis=0.001234,
        funding_rate=None,
        next_funding_time=None,
    )
    assert "Funding (prev)" not in txt
    assert "Next funding" not in txt

    # З funding
    ts = datetime(2025, 8, 14, 20, 0, tzinfo=timezone.utc).timestamp()
    txt2 = format_signal_markdown(
        symbol_spot="BTCUSDT",
        symbol_linear="BTCUSDT",
        spread_pct=0.42,
        spot_price=62850.12,
        mark_price=62823.44,
        vol_24h=2_100_000_000.0,
        basis=0.001234,
        funding_rate=0.0001,
        next_funding_time=ts,
    )
    assert "Funding (prev): *0.01%*" in txt2
    assert "Next funding: `2025-08-14 20:00 UTC`" in txt2
