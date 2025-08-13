from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramSettings(BaseModel):
    bot_token: str = ""
    alert_chat_id: str = ""
    report_chat_id: str = ""


class BybitSettings(BaseModel):
    api_key: str = ""
    api_secret: str = ""


class AppSettings(BaseSettings):
    # базове
    env: Literal["dev", "prod"] = "dev"

    # параметри відбору/звітів
    alert_threshold_pct: float = 1.0
    alert_cooldown_sec: int = 300
    min_vol_24h_usd: float = 10_000_000.0
    min_price: float = 0.001
    db_path: str = "data/signals.db"
    top_n_report: int = 3

    # прапор надсилання алертів
    enable_alerts: bool = True

    # інтеграції
    telegram: TelegramSettings = TelegramSettings()
    bybit: BybitSettings = BybitSettings()

    # allow/deny як СИРОВІ РЯДКИ з .env (CSV або JSON-масив).
    # ВАЖЛИВО: не List[str], щоб .env-провайдер НЕ намагався робити json.loads сам.
    allow_symbols: str = ""
    deny_symbols: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )


def load_settings() -> AppSettings:
    """
    Єдина точка завантаження налаштувань.
    У тестах monkeypatch переозначає саме цю функцію.
    """
    return AppSettings()
