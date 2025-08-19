# tests/test_settings_back_compat.py
import importlib


def _reset(mod):
    # Скинути кеш, якщо є
    if hasattr(mod, "load_settings") and hasattr(mod.load_settings, "cache_clear"):
        mod.load_settings.cache_clear()


def test_telegram_nested_back_compat(monkeypatch, tmp_path):
    # Підкинемо .env із TELEGRAM__TOKEN і перевіримо nested telegram.token
    envp = tmp_path / ".env.test"
    envp.write_text('TELEGRAM__TOKEN="from_file"\nTG_CHAT_ID="777"\n', encoding="utf-8")

    # Чистимо середовище
    for k in [
        "TELEGRAM__TOKEN",
        "TELEGRAM_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM__CHAT_ID",
        "TELEGRAM_CHAT_ID",
        "TG_CHAT_ID",
    ]:
        monkeypatch.delenv(k, raising=False)

    monkeypatch.setenv("ENV_FILE", str(envp))
    mod = importlib.import_module("src.infra.config")
    _reset(mod)

    s = mod.load_settings()
    assert getattr(getattr(s, "telegram", None), "token", None) == "from_file"
    assert getattr(getattr(s, "telegram", None), "chat_id", None) == "777"


def test_env_priority_over_file(monkeypatch, tmp_path):
    # Якщо в процесі вже є TELEGRAM__TOKEN, .env не має його перезаписувати
    envp = tmp_path / ".env.test"
    envp.write_text('TELEGRAM__TOKEN="from_file"\n', encoding="utf-8")

    monkeypatch.setenv("TELEGRAM__TOKEN", "from_env")
    monkeypatch.setenv("ENV_FILE", str(envp))

    mod = importlib.import_module("src.infra.config")
    _reset(mod)

    s = mod.load_settings()
    assert getattr(getattr(s, "telegram", None), "token", None) == "from_env"


def test_ws_defaults_fallback(monkeypatch, tmp_path):
    # Якщо верхні WS-поля не задані, беремо значення з bybit.*
    envp = tmp_path / ".env.test"
    envp.write_text("", encoding="utf-8")
    # чисте середовище
    for k in ["WS_PUBLIC_URL_LINEAR", "WS_PUBLIC_URL_SPOT"]:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ENV_FILE", str(envp))

    mod = importlib.import_module("src.infra.config")
    _reset(mod)
    s = mod.load_settings()

    assert s.ws_public_url_linear or s.bybit.ws_public_url_linear
    assert s.ws_public_url_spot or s.bybit.ws_public_url_spot
