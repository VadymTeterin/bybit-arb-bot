from src.core.filters.liquidity import enough_liquidity


def test_liquidity_ok_basic():
    row = {"price": 1.25, "turnover_usd": 15_000_000}
    assert enough_liquidity(row, min_vol_usd=10_000_000, min_price=0.01) is True


def test_liquidity_fail_low_price():
    row = {"price": 0.005, "turnover_usd": 20_000_000}
    assert enough_liquidity(row, min_vol_usd=10_000_000, min_price=0.01) is False


def test_liquidity_fail_low_volume():
    row = {"price": 2.0, "turnover_usd": 9_999_999.99}
    assert enough_liquidity(row, min_vol_usd=10_000_000, min_price=0.01) is False


def test_liquidity_flexible_keys():
    row = {"last": "3.5", "quoteVolume": "12000000"}  # альтернативні ключі як рядки
    assert enough_liquidity(row, min_vol_usd=10_000_000, min_price=1.0) is True


def test_liquidity_zero_or_missing_values():
    assert not enough_liquidity({"price": 0, "turnover_usd": 100}, 10, 0.01)
    assert not enough_liquidity({"price": 1, "turnover_usd": 0}, 10, 0.01)
    assert not enough_liquidity({}, 10, 0.01)


def test_liquidity_wrong_type_returns_false():
    assert not enough_liquidity(None, 10, 0.01)  # не мапа -> False
