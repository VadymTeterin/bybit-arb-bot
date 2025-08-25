import importlib

from src.core.filters import make_liquidity_predicate


def test_make_liquidity_predicate_env(monkeypatch):
    # flat значення
    monkeypatch.setenv("MIN_VOL24_USD", "20000000")
    monkeypatch.setenv("MIN_PRICE_USD", "0.5")
    import src.infra.liquidity_env as le

    importlib.reload(le)

    pred = make_liquidity_predicate()
    assert (
        pred({"price": 0.4, "turnover_usd": 25_000_000}) is False
    )  # ціна нижча за 0.5
    assert (
        pred({"price": 0.6, "turnover_usd": 15_000_000}) is False
    )  # обіг нижчий за 20M
    assert pred({"price": 0.6, "turnover_usd": 25_000_000}) is True  # проходить


def test_env_precedence_flat_over_nested(monkeypatch):
    # nested каже 1.0, flat каже 0.5 -> має перемогти flat (0.5)
    monkeypatch.setenv("LIQUIDITY__MIN_PRICE_USD", "1.0")
    monkeypatch.setenv("MIN_PRICE_USD", "0.5")
    monkeypatch.setenv("LIQUIDITY__MIN_VOL24_USD", "10000000")
    monkeypatch.setenv("MIN_VOL24_USD", "10000000")
    import src.infra.liquidity_env as le

    importlib.reload(le)

    pred = make_liquidity_predicate()
    # 0.6 > 0.5 (flat), тому True
    assert pred({"price": 0.6, "turnover_usd": 15_000_000}) is True
