# src/infra/config.py
from __future__ import annotations

import os
from typing import List, Optional

from pydantic import BaseModel, Field, PrivateAttr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv_to_list(s: Optional[str]) -> list[str]:
    """Split comma-separated string into list, tolerating None/empty."""
    if not s:
        return []
    parts = [p.strip() for p in s.split(",")]
    return [p for p in parts if p]


class TelegramConfig(BaseModel):
    token: Optional[str] = Field(default=None, alias="TELEGRAM_TOKEN")
    chat_id: Optional[int] = Field(default=None, alias="TG_CHAT_ID")


class AppSettings(BaseSettings):
    # ====== Base config ======
    env: str = Field(default="dev", alias="ENV")

    alert_threshold_pct: float = Field(default=0.5, alias="ALERT_THRESHOLD_PCT")
    alert_cooldown_sec: int = Field(default=180, alias="ALERT_COOLDOWN_SEC")

    min_vol_24h_usd: float = Field(default=500_000.0, alias="MIN_VOL_24H_USD")
    min_price: float = Field(default=0.001, alias="MIN_PRICE")

    db_path: str = Field(default="data/signals.db", alias="DB_PATH")

    enable_alerts: bool = Field(default=True, alias="ENABLE_ALERTS")

    # --- RAW strings from env (не списки!) ---
    allow_symbols_raw: Optional[str] = Field(default=None, alias="ALLOW_SYMBOLS")
    deny_symbols_raw: Optional[str] = Field(default=None, alias="DENY_SYMBOLS")

    # ====== WS / Realtime ======
    ws_enabled: bool = Field(default=True, alias="WS_ENABLED")

    # Нові BYBIT__*; є й legacy fallback через властивості нижче
    bybit_ws_public_url_linear: Optional[str] = Field(
        default=None, alias="BYBIT__WS_PUBLIC_URL_LINEAR"
    )
    bybit_ws_public_url_spot: Optional[str] = Field(
        default=None, alias="BYBIT__WS_PUBLIC_URL_SPOT"
    )

    bybit_ws_sub_topics_linear_raw: Optional[str] = Field(
        default=None, alias="BYBIT__WS_SUB_TOPICS_LINEAR"
    )
    bybit_ws_sub_topics_spot_raw: Optional[str] = Field(
        default=None, alias="BYBIT__WS_SUB_TOPICS_SPOT"
    )

    ws_reconnect_max_sec: Optional[int] = Field(
        default=30, alias="WS_RECONNECT_MAX_SEC"
    )
    rt_meta_refresh_sec: Optional[int] = Field(default=30, alias="RT_META_REFRESH_SEC")
    rt_log_passes: int = Field(default=1, alias="RT_LOG_PASSES")

    # Nested
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)

    # ====== Private computed attrs (щоб settings-джерела їх НЕ чіпали) ======
    _allow_symbols: List[str] = PrivateAttr(default_factory=list)
    _deny_symbols: List[str] = PrivateAttr(default_factory=list)
    _topics_linear: List[str] = PrivateAttr(default_factory=list)
    _topics_spot: List[str] = PrivateAttr(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # TELEGRAM__*, BYBIT__*, ...
        extra="ignore",
    )

    # ---------- Build/normalize ----------
    @model_validator(mode="after")
    def _normalize(self) -> "AppSettings":
        # CSV -> lists, без JSON
        self._allow_symbols = _csv_to_list(self.allow_symbols_raw)
        self._deny_symbols = _csv_to_list(self.deny_symbols_raw)

        self._topics_linear = _csv_to_list(self.bybit_ws_sub_topics_linear_raw)
        self._topics_spot = _csv_to_list(self.bybit_ws_sub_topics_spot_raw)

        # Legacy fallbacks для топіків, якщо нові не задані
        if not self._topics_linear:
            self._topics_linear = _csv_to_list(os.getenv("WS_SUB_TOPICS_LINEAR"))
        if not self._topics_spot:
            self._topics_spot = _csv_to_list(os.getenv("WS_SUB_TOPICS_SPOT"))

        return self

    # ---------- Public properties ----------
    # Нові "канонічні" проперті
    @property
    def allow_symbols(self) -> List[str]:
        return self._allow_symbols

    @property
    def deny_symbols(self) -> List[str]:
        return self._deny_symbols

    # Бек-сумісні назви, які очікують старі місця коду/тести
    @property
    def allow_symbols_list(self) -> List[str]:
        return self._allow_symbols

    @property
    def deny_symbols_list(self) -> List[str]:
        return self._deny_symbols

    # Back-compat: очікується в main.ws:run
    @property
    def ws_public_url_linear(self) -> Optional[str]:
        return self.bybit_ws_public_url_linear or os.getenv("WS_PUBLIC_URL_LINEAR")

    @property
    def ws_public_url_spot(self) -> Optional[str]:
        return self.bybit_ws_public_url_spot or os.getenv("WS_PUBLIC_URL_SPOT")

    @property
    def ws_topics_list_linear(self) -> List[str]:
        return list(self._topics_linear)

    @property
    def ws_topics_list_spot(self) -> List[str]:
        return list(self._topics_spot)

    # Зручні дзеркала для друку
    @property
    def telegram_token(self) -> Optional[str]:
        return self.telegram.token

    @property
    def tg_chat_id(self) -> Optional[int]:
        return self.telegram.chat_id


def load_settings() -> AppSettings:
    """Factory used across the project."""
    return AppSettings()
