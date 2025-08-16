# src/infra/config.py
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv_list(x: object) -> List[str]:
    """Нормалізувати CSV/список у List[str]."""
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(t).strip() for t in x if str(t).strip()]
    if isinstance(x, str):
        return [t.strip() for t in x.split(",") if t.strip()]
    return []


# ------------------- Nested models -------------------


class TelegramConfig(BaseModel):
    # ВАЖЛИВО: без alias, щоби працювало TELEGRAM__TOKEN / TELEGRAM__CHAT_ID
    token: Optional[str] = None
    # chat_id часто зручно зберігати як str (Bot API приймає рядок або int)
    chat_id: Optional[str] = None

    # Back-compat властивості (main.py/_tg_fields очікує їх на всякий випадок)
    @property
    def bot_token(self) -> Optional[str]:
        return self.token

    @property
    def alert_chat_id(self) -> Optional[str]:
        return self.chat_id


class BybitConfig(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    # WS параметри з дефолтами (щоб `python -m src.main env` щось показував
    # навіть без .env)
    ws_public_url_linear: Optional[str] = "wss://stream.bybit.com/v5/public/linear"
    ws_public_url_spot: Optional[str] = "wss://stream.bybit.com/v5/public/spot"

    # Топіки можна задавати або як CSV-рядок, або як список у .env
    ws_sub_topics_linear: Optional[str | List[str]] = "tickers.BTCUSDT,tickers.ETHUSDT"
    ws_sub_topics_spot: Optional[str | List[str]] = "tickers.BTCUSDT,tickers.ETHUSDT"


# ------------------- Root settings -------------------


class AppSettings(BaseSettings):
    # Конфіг Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Загальні
    env: str = "dev"

    # Пороги/кулдауни
    alert_threshold_pct: float = 1.0
    alert_cooldown_sec: int = 300

    # Фільтри
    min_vol_24h_usd: float = 10_000_000.0
    min_price: float = 0.001

    # Шлях до БД
    db_path: str = "data/signals.db"

    # Репорт
    top_n_report: int = 10

    # Увімкнення алертів
    enable_alerts: bool = True

    # Списки дозволених/заборонених символів (можна CSV у .env)
    allow_symbols: Optional[str | List[str]] = None
    deny_symbols: Optional[str | List[str]] = None

    # WS опції (тут — «пласкі» поля для back-compat; основні — у BybitConfig)
    ws_enabled: bool = True
    ws_public_url_linear: Optional[str] = None
    ws_public_url_spot: Optional[str] = None
    ws_sub_topics_linear: Optional[str | List[str]] = None
    ws_sub_topics_spot: Optional[str | List[str]] = None
    ws_reconnect_max_sec: Optional[int] = 30

    # Runtime-мета
    rt_meta_refresh_sec: int = 30
    rt_log_passes: int = 1

    # Вкладені секції
    telegram: TelegramConfig = TelegramConfig()
    bybit: BybitConfig = BybitConfig()

    # --------- Зручні computed-властивості ---------

    @property
    def allow_symbols_list(self) -> List[str]:
        return _csv_list(self.allow_symbols)

    @property
    def deny_symbols_list(self) -> List[str]:
        return _csv_list(self.deny_symbols)

    @property
    def ws_topics_list_linear(self) -> List[str]:
        # back-compat: дехто може читати саме це ім'я
        src = self.ws_sub_topics_linear or self.bybit.ws_sub_topics_linear
        return _csv_list(src)

    @property
    def ws_topics_list_spot(self) -> List[str]:
        # back-compat
        src = self.ws_sub_topics_spot or self.bybit.ws_sub_topics_spot
        return _csv_list(src)


# ------------------- Loader with fallbacks -------------------


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    """
    Завантажити налаштування з .env / env vars.
    Містить декілька back-compat містків:
      - Пласкі TELEGRAM_TOKEN / TG_CHAT_ID (якщо не задано TELEGRAM__TOKEN/CHAT_ID)
      - Підхоплення «пласких» WS-полів на верхньому рівні, якщо вони відсутні у bybit.*
    """
    s = AppSettings()

    # --- Back-compat для пласких Telegram-перемінних ---
    # Якщо користувач встановив TELEGRAM_TOKEN/TG_CHAT_ID (без "__"),
    # підхоплюємо їх, тільки якщо nested значення відсутні.
    token_flat = os.getenv("TELEGRAM_TOKEN")
    chat_flat = os.getenv("TG_CHAT_ID")
    if not s.telegram.token and token_flat:
        s.telegram.token = token_flat
    if not s.telegram.chat_id and chat_flat:
        s.telegram.chat_id = chat_flat

    # Також підтримай альтернативні назви ( BOT_TOKEN / ALERT_CHAT_ID )
    token_alt = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_alt = os.getenv("TELEGRAM_ALERT_CHAT_ID")
    if not s.telegram.token and token_alt:
        s.telegram.token = token_alt
    if not s.telegram.chat_id and chat_alt:
        s.telegram.chat_id = chat_alt

    # --- Back-compat для WS-полів (верхній рівень vs. bybit.*) ---
    # 1) URL-и
    if not s.ws_public_url_linear and s.bybit.ws_public_url_linear:
        s.ws_public_url_linear = s.bybit.ws_public_url_linear
    if not s.ws_public_url_spot and s.bybit.ws_public_url_spot:
        s.ws_public_url_spot = s.bybit.ws_public_url_spot

    # 2) Топіки
    if not s.ws_sub_topics_linear and s.bybit.ws_sub_topics_linear is not None:
        s.ws_sub_topics_linear = s.bybit.ws_sub_topics_linear
    if not s.ws_sub_topics_spot and s.bybit.ws_sub_topics_spot is not None:
        s.ws_sub_topics_spot = s.bybit.ws_sub_topics_spot

    return s
