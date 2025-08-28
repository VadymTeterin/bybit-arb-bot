import importlib
from types import SimpleNamespace

# Ми тестуємо, що main використовує форматери, якщо вони доступні,
# і що відправка в Telegram отримує саме відформатований текст.


def _fake_settings():
    return SimpleNamespace(
        enable_alerts=True,
        min_vol_24h_usd=1_000.0,
        min_price=1.0,
        alert_threshold_pct=0.5,
        alert_cooldown_sec=0,
        top_n_report=5,
        ws_enabled=False,
        rt_meta_refresh_sec=60,
        rt_log_passes=False,
        allow_symbols="",
        allow_symbols_list=[],
        deny_symbols="",
        deny_symbols_list=[],
        ws_public_url_linear="",
        ws_public_url_spot="",
        ws_topics_list_linear=[],
        ws_topics_list_spot=[],
        ws_reconnect_max_sec=10,
        db_path=":memory:",
        telegram=SimpleNamespace(bot_token="x", alert_chat_id="1"),
        bybit=SimpleNamespace(api_key="", api_secret=""),
        env="test",
    )


def test_alerts_formatter_used_for_rows(monkeypatch):
    m = importlib.import_module("src.main")

    # 1) стабілізуємо конфіг
    monkeypatch.setattr(m, "load_settings", _fake_settings)

    # 2) підміняємо джерело даних
    rows_ok = [("BTCUSDT", 50000.0, 50500.0, 1.0, 3_000_000.0)]
    monkeypatch.setattr(m, "_basis_rows", lambda **kw: (rows_ok, rows_ok))

    # 3) підміняємо відправку в Telegram, щоб перехопити текст
    sent = {}

    def _fake_send(token, chat, text):
        sent["text"] = text
        return {"ok": True}

    monkeypatch.setattr(m, "send_telegram_message", _fake_send)

    # 4) гарантуємо наявність модуля форматерів і функції format_basis_top
    fmt = importlib.import_module("src.telegram.formatters")
    monkeypatch.setattr(
        fmt,
        "format_basis_top",
        lambda rows, header=None: "FAKE_FMT_ROWS",
        raising=False,
    )

    # 5) викликаємо команду без телеметрії
    ns = SimpleNamespace(limit=1, threshold=None, min_vol=None)
    rc = m.cmd_basis_alert(ns)
    assert rc == 0
    assert sent["text"] == "FAKE_FMT_ROWS"


def test_alerts_formatter_used_when_no_rows(monkeypatch):
    m = importlib.import_module("src.main")

    # 1) стабілізуємо конфіг
    monkeypatch.setattr(m, "load_settings", _fake_settings)

    # 2) дані без кандидатів
    rows_empty = []
    monkeypatch.setattr(m, "_basis_rows", lambda **kw: (rows_empty, rows_empty))

    # 3) підміняємо відправку в Telegram
    sent = {}

    def _fake_send(token, chat, text):
        sent["text"] = text
        return {"ok": True}

    monkeypatch.setattr(m, "send_telegram_message", _fake_send)

    # 4) гарантуємо наявність функції format_no_candidates
    fmt = importlib.import_module("src.telegram.formatters")
    monkeypatch.setattr(fmt, "format_no_candidates", lambda header=None: "FAKE_NO_ROWS", raising=False)

    # 5) викликаємо команду
    ns = SimpleNamespace(limit=3, threshold=1.0, min_vol=1_000.0)
    rc = m.cmd_basis_alert(ns)
    assert rc == 0
    assert sent["text"] == "FAKE_NO_ROWS"
