from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корінь проєкту: ./bybit-arb-bot/
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"

# Підвантажуємо .env (не кидає помилок, якщо файлу немає)
load_dotenv(ENV_FILE)

# --------- секції конфігів ---------
class TelegramConfig(BaseModel):
    bot_token: str = Field(default="")
    alert_chat_id: str = Field(default="")

class BybitConfig(BaseModel):
    api_key: str = Field(default="")
    api_secret: str = Field(default="")

class AppSettings(BaseSettings):
    # Базові налаштування
    env: Literal["dev", "prod"] = "dev"

    # Алерти / фільтри
    alert_threshold_pct: float = 1.0         # % basis для тригера нотифікації
    alert_cooldown_sec: int = 300            # анти-спам інтервал
    min_vol_24h_usd: float = 10_000_000.0    # мін. обсяг 24h для ліквідності
    min_price: float = 0.001                 # мін. ціна для відсікання «пені-коінів»

    # БД / звіти
    db_path: str = str(ROOT_DIR / "data" / "signals.db")
    top_n_report: int = 3

    # Підсекції
    telegram: TelegramConfig = TelegramConfig()
    bybit: BybitConfig = BybitConfig()

    # Налаштування pydantic-settings
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_prefix="",
        env_nested_delimiter="__",     # підтримка TELEGRAM__BOT_TOKEN, BYBIT__API_KEY і т.д.
        extra="ignore",
    )

def _from_env_many(*names: str, default: str = "") -> str:
    """Повертає перше непорожнє значення змінної середовища з перелічених."""
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default

def load_settings() -> AppSettings:
    """
    Читає .env, збирає AppSettings і підставляє значення для Telegram/Bybit
    з підтримкою і нових (вкладених), і старих назв змінних.
    """
    s = AppSettings()

    # Telegram
    tg_token = _from_env_many(
        "TELEGRAM__BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN",
        default=s.telegram.bot_token
    )
    tg_chat  = _from_env_many(
        "TELEGRAM__ALERT_CHAT_ID", "TG_ALERT_CHAT_ID", "TG_CHAT_ID",
        default=s.telegram.alert_chat_id
    )

    # Bybit
    bybit_key    = _from_env_many("BYBIT__API_KEY", "BYBIT_API_KEY", default=s.bybit.api_key)
    bybit_secret = _from_env_many("BYBIT__API_SECRET", "BYBIT_API_SECRET", default=s.bybit.api_secret)

    return AppSettings(
        env=s.env,
        alert_threshold_pct=s.alert_threshold_pct,
        alert_cooldown_sec=s.alert_cooldown_sec,
        min_vol_24h_usd=s.min_vol_24h_usd,
        min_price=s.min_price,
        db_path=s.db_path,
        top_n_report=s.top_n_report,
        telegram=TelegramConfig(bot_token=tg_token, alert_chat_id=tg_chat),
        bybit=BybitConfig(api_key=bybit_key, api_secret=bybit_secret),
    )
