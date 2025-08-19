# tests/test_main.py
from types import SimpleNamespace as NS

import pytest

import src.main as m


def test_env_helpers(monkeypatch):
    # _env_bool
    monkeypatch.delenv("X", raising=False)
    assert m._env_bool("X", True) is True
    monkeypatch.setenv("X", "1")
    assert m._env_bool("X") is True
    monkeypatch.setenv("X", "true")
    assert m._env_bool("X") is True
    monkeypatch.setenv("X", "no")
    assert m._env_bool("X") is False

    # _env_float
    monkeypatch.setenv("YF", "12.34")
    assert m._env_float("YF", 0.0) == pytest.approx(12.34, rel=1e-6)
    monkeypatch.setenv("YF", "bad")
    assert m._env_float("YF", 7.0) == 7.0

    # _env_int
    monkeypatch.setenv("YI", "42")
    assert m._env_int("YI", 0) == 42
    monkeypatch.setenv("YI", "bad")
    assert m._env_int("YI", 5) == 5

    # _env_csv
    monkeypatch.setenv("CSV", "A, B,,C ,  ")
    assert m._env_csv("CSV") == ["A", "B", "C"]


def test_nested_bybit_fallbacks():
    s = NS(
        ws_public_url_linear="linear",
        ws_public_url_spot="spot",
        ws_topics_list_linear=["tickers.BTCUSDT"],
        ws_topics_list_spot=["tickers.ETHUSDT"],
        ws_reconnect_max_sec=30,
    )
    res = m._nested_bybit(s)
    assert res["url_linear"] == "linear"
    assert res["url_spot"] == "spot"
    assert res["topics_linear"] == ["tickers.BTCUSDT"]
    assert res["topics_spot"] == ["tickers.ETHUSDT"]
    assert res["reconnect_max_sec"] == 30

    s2 = NS(
        bybit=NS(
            ws_public_url_linear="l2",
            ws_public_url_spot="s2",
            ws_sub_topics_linear="tickers.ABC,tickers.DEF",
            ws_sub_topics_spot="tickers.XYZ",
        )
    )
    res2 = m._nested_bybit(s2)
    assert res2["url_linear"] == "l2"
    assert res2["url_spot"] == "s2"
    assert res2["topics_linear"] == ["tickers.ABC", "tickers.DEF"]
    assert res2["topics_spot"] == ["tickers.XYZ"]


def test_basis_rows_and_preview(monkeypatch):
    class FakeRest:
        def get_spot_map(self):
            return {
                "ETHUSDT": {"price": 2000.0, "turnover_usd": 20_000_000.0},
                "LOWVOL": {"price": 1.0, "turnover_usd": 1_000.0},
            }

        def get_linear_map(self):
            return {
                "ETHUSDT": {"price": 2040.0, "turnover_usd": 25_000_000.0},
                "LOWVOL": {"price": 1.1, "turnover_usd": 1_000.0},
            }

    monkeypatch.setattr(m, "BybitRest", FakeRest, raising=True)
    rows_pass, rows_all = m._basis_rows(min_vol=5_000_000.0, threshold=1.0)

    # ETHUSDT should pass (min vol met, ~+2% basis)
    assert any(r[0] == "ETHUSDT" for r in rows_pass)
    # rows_all should include both symbols
    assert {r[0] for r in rows_all} == {"ETHUSDT", "LOWVOL"}

    # preview text sanity
    txt = m.preview_message("ETHUSDT", 2000.0, 2040.0, 25_000_000.0, 1.0)
    assert "ETHUSDT" in txt and "basis=+2.00%" in txt


def test_cmd_ws_run_disabled(monkeypatch, capsys):
    # If WS is disabled in settings, the command should exit early with a note.
    monkeypatch.setattr(m, "load_settings", lambda: NS(ws_enabled=False))
    rc = m.cmd_ws_run(NS())
    out = capsys.readouterr().out
    assert rc == 0
    assert "WS is disabled" in out


def test_cmd_price_pair(monkeypatch, capsys):
    class FakeClient:
        def get_spot_map(self):
            return {"ETHUSDT": {"price": 2000.0, "turnover_usd": 10_000_000.0}}

        def get_linear_map(self):
            return {"ETHUSDT": {"price": 2040.0, "turnover_usd": 12_000_000.0}}

    monkeypatch.setattr(m, "create_bybit_client", lambda: FakeClient())
    rc = m.cmd_price_pair(NS(symbol=["ETHUSDT"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert "ETHUSDT" in out and "basis=+2.00%" in out


def test_tg_fields_env_and_settings(monkeypatch):
    # Clean envs
    for key in [
        "TELEGRAM__BOT_TOKEN",
        "TELEGRAM__TOKEN",
        "TELEGRAM__ALERT_CHAT_ID",
        "TELEGRAM__CHAT_ID",
    ]:
        monkeypatch.delenv(key, raising=False)

    # Fallback to envs
    monkeypatch.setenv("TELEGRAM__TOKEN", "tkn")
    monkeypatch.setenv("TELEGRAM__CHAT_ID", "123")
    token, chat_id = m._tg_fields(NS())
    assert token == "tkn" and chat_id == "123"

    # Settings.telegram should take precedence
    s2 = NS(telegram=NS(token="A", chat_id="B"))
    token2, chat_id2 = m._tg_fields(s2)
    assert token2 == "A" and chat_id2 == "B"


def test_cmd_basis_scan(monkeypatch, capsys):
    class FakeRest:
        def get_spot_map(self):
            return {"ETHUSDT": {"price": 2000.0, "turnover_usd": 20_000_000.0}}

        def get_linear_map(self):
            return {"ETHUSDT": {"price": 2040.0, "turnover_usd": 25_000_000.0}}

    monkeypatch.setattr(m, "BybitRest", FakeRest, raising=True)
    s = NS(min_vol_24h_usd=5_000_000.0, alert_threshold_pct=1.0)
    monkeypatch.setattr(m, "load_settings", lambda: s)
    rc = m.cmd_basis_scan(NS(limit=5, threshold=None, min_vol=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "ETHUSDT" in out and "+2.00%" in out
