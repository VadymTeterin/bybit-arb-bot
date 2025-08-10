from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корінь проєкту: .../bybit-arb-bot/
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


class TelegramConfig(BaseModel):
    bot_token: str = Field(default="", description="Telegram bot token")
    alert_chat_id: str = Field(default="", description="Chat/channel ID for alerts")


class BybitConfig(BaseModel):
    api_key: str = Field(default="", description="Bybit API key")
    api_secret: str = Field(default="", description="Bybit API secret")


class AppSettings(BaseSettings):
    """Налаштування застосунку, що читаються з env або .env."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "prod", "test"] = "dev"

    # Пороги та інтервали
    alert_threshold_pct: float = 1.0       # поріг basis, %
    alert_cooldown_sec: int = 300          # cooldown алертів, сек
    min_vol_24h_usd: float = 10_000_000.0  # фільтр ліквідності, USD

    # Вкладені секції
    telegram: TelegramConfig = TelegramConfig()
    bybit: BybitConfig = BybitConfig()

    # Інше
    log_dir: Path = ROOT_DIR / "logs"

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


def load_settings() -> AppSettings:
    """Завантажити налаштування з .env та оточення."""
    data = {
        "telegram": {
            "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TG_BOT_TOKEN", "")),
            "alert_chat_id": os.getenv("ALERT_CHAT_ID", os.getenv("TG_CHAT_ID", "")),
        },
        "bybit": {
            "api_key": os.getenv("BYBIT_API_KEY", ""),
            "api_secret": os.getenv("BYBIT_API_SECRET", ""),
        },
        "alert_threshold_pct": float(os.getenv("ALERT_THRESHOLD_PCT", "1.0")),
        "alert_cooldown_sec": int(os.getenv("ALERT_COOLDOWN_SEC", "300")),
        "min_vol_24h_usd": float(os.getenv("MIN_VOL_24H_USD", "10000000")),
        "env": os.getenv("ENV", "dev"),
    }

    settings = AppSettings(**data)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    return settings
