from types import SimpleNamespace

import src.main as app


def test_report_send_respects_enable_alerts(monkeypatch, capsys):
    # load_settings із вимкненими алертами
    fake_settings = SimpleNamespace(
        env="dev",
        alert_threshold_pct=1.0,
        alert_cooldown_sec=300,
        min_vol_24h_usd=10_000_000.0,
        min_price=0.001,
        db_path=":memory:",
        top_n_report=3,
        enable_alerts=False,  # <- головне
        telegram=SimpleNamespace(bot_token="x", alert_chat_id="y"),
        bybit=SimpleNamespace(api_key="", api_secret=""),
    )
    monkeypatch.setattr(app, "load_settings", lambda: fake_settings)

    # штучні дані звіту
    monkeypatch.setattr(
        app,
        "get_top_signals",
        lambda last_hours, limit: [{"symbol": "ETHUSDT", "basis_pct": 1.0}],
    )
    monkeypatch.setattr(app, "format_report", lambda items: "report text")

    called = {"sent": False}

    def fake_send(token, chat, text):
        called["sent"] = True
        return {"ok": True}

    monkeypatch.setattr(app, "send_telegram_message", fake_send)

    # викликаємо handler напряму
    ns = SimpleNamespace(hours=24, limit=None)
    rc = app.cmd_report_send(ns)
    assert rc == 0

    # перевірка, що відправка не виконалася
    assert called["sent"] is False

    # і що вивело попередження
    captured = capsys.readouterr()
    assert "Alerts are disabled by config" in captured.out
