# tests/test_env_autoload.py
import importlib
import os


def test_autoload_env_basic(monkeypatch, tmp_path):
    envp = tmp_path / ".env.test"
    envp.write_text(
        "  # comment line\n" 'export TELEGRAM__TOKEN="abc123"\n' "TG_CHAT_ID='999'\n" "FOO=bar\n" "BAR=${FOO}-baz\n",
        encoding="utf-8",
    )
    # ensure a clean room — clear both before relying on autoload
    for k in ["TELEGRAM__TOKEN", "TG_CHAT_ID", "FOO", "BAR"]:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ENV_FILE", str(envp))

    from src.infra.dotenv_autoload import autoload_env

    autoload_env()  # should populate os.environ

    assert os.environ.get("TELEGRAM__TOKEN") == "abc123"
    assert os.environ.get("TG_CHAT_ID") == "999"
    assert os.environ.get("BAR") == "bar-baz"


def test_load_settings_picks_up_env(monkeypatch, tmp_path):
    envp = tmp_path / ".env.test"
    envp.write_text('TELEGRAM__TOKEN="from_file"\n', encoding="utf-8")
    # cleanup any residue from previous runs
    monkeypatch.delenv("TELEGRAM__TOKEN", raising=False)
    monkeypatch.setenv("ENV_FILE", str(envp))

    mod = importlib.import_module("src.infra.config")
    if hasattr(mod, "load_settings") and hasattr(mod.load_settings, "cache_clear"):
        mod.load_settings.cache_clear()

    s = mod.load_settings()

    token = None
    try:
        token = getattr(getattr(s, "telegram", None), "token", None)
    except Exception:
        token = None
    token = token or os.environ.get("TELEGRAM__TOKEN")
    assert token == "from_file"
