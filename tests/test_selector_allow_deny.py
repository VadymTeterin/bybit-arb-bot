# tests/test_selector_allow_deny.py
from types import SimpleNamespace

import src.core.selector as selector


class FakeClient:
    def get_spot_map(self):
        return {
            "ETHUSDT": {"price": 3000, "turnover_usd": 50_000_000},
            "BTCUSDT": {"price": 65000, "turnover_usd": 80_000_000},
            "XRPUSDT": {"price": 0.6, "turnover_usd": 20_000_000},
        }

    def get_linear_map(self):
        return {
            "ETHUSDT": {"price": 3030, "turnover_usd": 60_000_000},
            "BTCUSDT": {"price": 65300, "turnover_usd": 90_000_000},
            "XRPUSDT": {"price": 0.604, "turnover_usd": 25_000_000},
        }


def test_allow_deny_filters(monkeypatch):
    # підміняємо load_settings у модулі selector
    fake_settings = SimpleNamespace(
        min_vol_24h_usd=1_000_000,
        min_price=0.001,
        alert_threshold_pct=0.5,  # ETH ~1%, BTC ~0.46%, XRP ~0.67%
        alert_cooldown_sec=0,  # щоб не заважав
        allow_symbols=["ETHUSDT", "XRPUSDT"],  # дозволимо тільки ETH/XRP
        deny_symbols=["XRPUSDT"],  # але XRP забороняємо
        db_path=":memory:",
    )
    monkeypatch.setattr(selector, "load_settings", lambda: fake_settings)

    # відключаємо реальні виклики до SQLite
    saved = []
    monkeypatch.setattr(selector.persistence, "init_db", lambda: None)
    monkeypatch.setattr(
        selector.persistence, "recent_signal_exists", lambda symbol, cooldown_sec: False
    )
    monkeypatch.setattr(
        selector.persistence,
        "save_signal",
        lambda *args, **kwargs: saved.append(args),
    )

    res = selector.run_selection(client=FakeClient(), limit=5)
    # маємо зберегти лише ETHUSDT (XRP – deny, BTC – не в allow)
    assert len(res) == 1
    assert res[0]["symbol"] == "ETHUSDT"
