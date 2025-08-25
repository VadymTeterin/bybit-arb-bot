import importlib

import src.infra.liquidity_env as le


def test_toggle_default_off(monkeypatch):
    monkeypatch.delenv("ENABLE_LIQUIDITY_FILTERS", raising=False)
    monkeypatch.delenv("LIQUIDITY__ENABLED", raising=False)
    importlib.reload(le)
    assert le.is_liquidity_enabled() is False


def test_toggle_nested_on(monkeypatch):
    monkeypatch.setenv("LIQUIDITY__ENABLED", "1")
    importlib.reload(le)
    assert le.is_liquidity_enabled() is True


def test_toggle_flat_overrides_nested(monkeypatch):
    monkeypatch.setenv("LIQUIDITY__ENABLED", "0")
    monkeypatch.setenv("ENABLE_LIQUIDITY_FILTERS", "true")
    importlib.reload(le)
    assert le.is_liquidity_enabled() is True
