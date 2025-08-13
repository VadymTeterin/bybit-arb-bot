from __future__ import annotations

from typing import Literal, List

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

    # ---- depth-фільтр (із фази 3.4) ----
    min_depth_usd: float = 1_000_000.0   # мінімальна глибина ($) у межах ±depth_window_pct
    depth_window_pct: float = 0.5        # ширина вікна у %, 0.5 => ±0.5%
    min_depth_levels: int = 30           # мінімальна сумарна к-сть рівнів (bid+ask) у вікні

    # прапор надсилання алертів
    enable_alerts: bool = True

    # інтеграції
    telegram: TelegramSettings = TelegramSettings()
    bybit: BybitSettings = BybitSettings()

    # allow/deny як СИРОВІ РЯДКИ з .env (CSV або JSON-масив).
    allow_symbols: str = ""
    deny_symbols: str = ""

    # ---- WS (фаза 4.2+) ----
    ws_enabled: bool = False

    # окремі канали для linear та spot
    ws_public_url_linear: str = "wss://stream.bybit.com/v5/public/linear"
    ws_public_url_spot: str = "wss://stream.bybit.com/v5/public/spot"

    # CSV рядки топіків (наприклад: "tickers" або "tickers.BTCUSDT,tickers.ETHUSDT")
    ws_sub_topics_linear: str = "tickers"
    ws_sub_topics_spot: str = "tickers"

    ws_reconnect_max_sec: int = 30

    # (Залишено для зворотної сумісності — НЕ використовується в 4.2+)
    ws_public_url: str = "wss://stream.bybit.com/v5/public/linear"
    ws_sub_topics: str = "tickers"

    # ---- 4.3: realtime wiring ----
    rt_meta_refresh_sec: int = 300  # як часто оновлювати vol24h із REST (сек)
    rt_log_passes: bool = True      # логувати коли символ проходить пороги в реальному часі

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # ---- зручні властивості ----
    @staticmethod
    def _parse_symbols(raw: str) -> List[str]:
        raw = (raw or "").strip()
        if not raw:
            return []
        # підтримуємо CSV і простий JSON-список
        if raw.lstrip().startswith("["):
            try:
                import json
                arr = json.loads(raw)
                return [str(x).strip() for x in arr if str(x).strip()]
            except Exception:
                pass
        return [x.strip() for x in raw.split(",") if x.strip()]

    @property
    def allow_symbols_list(self) -> List[str]:
        return self._parse_symbols(self.allow_symbols)

    @property
    def deny_symbols_list(self) -> List[str]:
        return self._parse_symbols(self.deny_symbols)

    # нові: окремі списки топіків
    @property
    def ws_topics_list_linear(self) -> List[str]:
        return self._parse_symbols(self.ws_sub_topics_linear)

    @property
    def ws_topics_list_spot(self) -> List[str]:
        return self._parse_symbols(self.ws_sub_topics_spot)

    # старий метод (не використовується в 4.2, але лишаємо)
    @property
    def ws_topics_list(self) -> List[str]:
        return self._parse_symbols(self.ws_sub_topics)


def load_settings() -> AppSettings:
    """Єдина точка завантаження налаштувань."""
    return AppSettings()
