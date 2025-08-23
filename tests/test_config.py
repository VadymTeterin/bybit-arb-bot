import pytest
from pydantic import ValidationError


def _load_settings():
    """
    Некешоване завантаження конфігів.
    Якщо є get_settings() з кешем — чистимо його перед викликом.
    """
    import src.infra.config as cfg

    if hasattr(cfg, "get_settings") and hasattr(cfg.get_settings, "cache_clear"):
        cfg.get_settings.cache_clear()

    return cfg.load_settings() if hasattr(cfg, "load_settings") else cfg.get_settings()


def test_nested_env_loading(monkeypatch):
    # Значення беруться з ENV (ENV > .env > defaults)
    monkeypatch.setenv("RUNTIME__ENV", "dev")
    monkeypatch.setenv("TELEGRAM__TOKEN", "t-123")
    monkeypatch.setenv("TELEGRAM__CHAT_ID", "999")
    monkeypatch.setenv("ALERTS__THRESHOLD_PCT", "1.8")
    monkeypatch.setenv("LIQUIDITY__MIN_PRICE", "0.005")

    s = _load_settings()
    # runtime
    assert getattr(s, "env", getattr(s.runtime, "env", None)) == "dev"
    # telegram
    assert s.telegram.token == "t-123"
    assert s.telegram.chat_id == "999"
    # alerts
    assert pytest.approx(s.alerts.threshold_pct) == 1.8
    # liquidity
    assert s.liquidity.min_price == 0.005


def test_flat_overrides_nested(monkeypatch):
    # nested дає 1.0, але flat має перекрити на 2.5
    monkeypatch.setenv("ALERTS__THRESHOLD_PCT", "1.0")
    monkeypatch.setenv("ALERT_THRESHOLD_PCT", "2.5")

    s = _load_settings()
    assert pytest.approx(s.alerts.threshold_pct) == 2.5


@pytest.mark.parametrize("bad_value", ["-0.1", "101"])
def test_validation_threshold_pct_out_of_range(monkeypatch, bad_value):
    # out-of-range значення має спричинити ValidationError
    monkeypatch.setenv("ALERTS__THRESHOLD_PCT", bad_value)

    with pytest.raises(ValidationError):
        _load_settings()
