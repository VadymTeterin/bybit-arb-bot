# src/infra/config.py
from __future__ import annotations

import os
from typing import List, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "TelegramSettings",
    "BybitSettings",
    "AppSettings",
    "load_settings",
]


class TelegramSettings(BaseModel):
    bot_token: str = ""
    alert_chat_id: str = ""
    report_chat_id: str = ""
    enabled: bool = True
    cooldown_seconds: int = 30


class BybitSettings(BaseModel):
    # API keys (допускаємо BYBIT__API_KEY або BYBIT_API_KEY через load_settings())
    api_key: str = Field(default="", validation_alias="BYBIT__API_KEY")
    api_secret: str = Field(default="", validation_alias="BYBIT__API_SECRET")

    # Public WS (linear / spot)
    ws_public_url_linear: str = "wss://stream.bybit.com/v5/public/linear"
    ws_public_url_spot: str = "wss://stream.bybit.com/v5/public/spot"

    # Топіки підписки (CSV): "tickers" або "tickers.BTCUSDT,tickers.ETHUSDT"
    ws_sub_topics_linear: str = "tickers"
    ws_sub_topics_spot: str = "tickers"

    ws_reconnect_max_sec: int = 30


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",  # підтримка BYBIT__API_KEY і т.п.
        extra="ignore",  # не падати, якщо в .env є зайві ключі
    )

    # Загальне
    env: Literal["dev", "prod", "test"] = "dev"

    # Алгоритмічні пороги / фільтри
    alert_threshold_pct: float = 1.0
    alert_cooldown_sec: int = 300
    min_vol_24h_usd: float = 10_000_000
    min_price: float = 0.001
    db_path: str = "data/signals.db"
    top_n_report: int = 3
    enable_alerts: bool = True  # очікується тестами

    # Allow / Deny lists (CSV/JSON)
    allow_symbols: str = ""
    deny_symbols: str = ""

    # Експорт сигналів (очікується тестами)
    export_last_hours: int = 24
    export_dir: str = "exports"
    export_keep: int = 0

    # Діагностика реального часу (очікується тестами)
    rt_log_passes: int = 1

    # Telegram та Bybit (вкладені)
    telegram: TelegramSettings = TelegramSettings()
    bybit: BybitSettings = BybitSettings()

    # Глобальний перемикач WS у додатку
    ws_enabled: bool = True

    # ---- helpers ----
    def _split_csv(self, s: str) -> List[str]:
        if not s:
            return []
        return [x.strip() for x in s.replace(";", ",").split(",") if x.strip()]

    @property
    def allow_symbols_list(self) -> List[str]:
        return [x.upper() for x in self._split_csv(self.allow_symbols)]

    @property
    def deny_symbols_list(self) -> List[str]:
        return [x.upper() for x in self._split_csv(self.deny_symbols)]


def load_settings() -> AppSettings:
    """
    Завантажуємо налаштування з .env з подвійною сумісністю:
    - Вкладені ключі BYBIT__* (рекомендовано).
    - Плоскі WS_* (якщо такі вже є у .env) — мапимо їх у BybitSettings.
    """
    # Back-compat: приймаємо BYBIT_API_KEY/SECRET і прокидаємо їх у нові назви BYBIT__*
    if not os.getenv("BYBIT__API_KEY") and os.getenv("BYBIT_API_KEY"):
        os.environ["BYBIT__API_KEY"] = os.getenv("BYBIT_API_KEY", "")
    if not os.getenv("BYBIT__API_SECRET") and os.getenv("BYBIT_API_SECRET"):
        os.environ["BYBIT__API_SECRET"] = os.getenv("BYBIT_API_SECRET", "")

    s = AppSettings()

    # Back-compat для плоских WS_ змінних:
    s.bybit.ws_public_url_linear = os.getenv(
        "WS_PUBLIC_URL_LINEAR", s.bybit.ws_public_url_linear
    )
    s.bybit.ws_public_url_spot = os.getenv(
        "WS_PUBLIC_URL_SPOT", s.bybit.ws_public_url_spot
    )
    s.bybit.ws_sub_topics_linear = os.getenv(
        "WS_SUB_TOPICS_LINEAR", s.bybit.ws_sub_topics_linear
    )
    s.bybit.ws_sub_topics_spot = os.getenv(
        "WS_SUB_TOPICS_SPOT", s.bybit.ws_sub_topics_spot
    )
    try:
        s.bybit.ws_reconnect_max_sec = int(
            os.getenv("WS_RECONNECT_MAX_SEC", s.bybit.ws_reconnect_max_sec)
        )
    except Exception:
        pass

    return s
