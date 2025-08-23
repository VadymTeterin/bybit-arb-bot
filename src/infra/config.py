# src/infra/config.py
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Autoload .env (stdlib loader lives in src/infra/dotenv_autoload.py)
from .dotenv_autoload import autoload_env

# Try to load .env as early as possible (idempotent)
autoload_env()


def _csv_list(x: object) -> List[str]:
    """Normalize CSV/list into List[str]."""
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(t).strip() for t in x if str(t).strip()]
    if isinstance(x, str):
        return [t.strip() for t in x.split(",") if t.strip()]
    return []


def _from_env_many(*names: str, default: str = "") -> str:
    """Return the first non-empty value among the given env var names."""
    for n in names:
        v = os.getenv(n)
        if v not in (None, ""):
            return v
    return default


def _from_env_many_float(*names: str, default: float | None = None) -> float | None:
    raw = _from_env_many(*names, default="" if default is None else str(default))
    try:
        return float(raw) if raw != "" else default
    except ValueError:
        return default


def _from_env_many_int(*names: str, default: int | None = None) -> int | None:
    raw = _from_env_many(*names, default="" if default is None else str(default))
    try:
        return int(float(raw)) if raw != "" else default
    except ValueError:
        return default


def _from_env_many_bool(*names: str, default: bool | None = None) -> bool | None:
    raw = _from_env_many(*names, default="" if default is None else str(default))
    if raw == "":
        return default
    val = str(raw).strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return default


# ------------------- Nested models -------------------


class TelegramConfig(BaseModel):
    """Telegram settings."""

    token: Optional[str] = None
    # Bot API accepts str or int; we keep str for convenience
    chat_id: Optional[str] = None

    # Back-compat properties (some code may expect these)
    @property
    def bot_token(self) -> Optional[str]:
        return self.token

    @property
    def alert_chat_id(self) -> Optional[str]:
        return self.chat_id


class BybitConfig(BaseModel):
    """Bybit settings (API & WS)."""

    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    # Default WS endpoints (so env demo works even without .env)
    ws_public_url_linear: Optional[str] = "wss://stream.bybit.com/v5/public/linear"
    ws_public_url_spot: Optional[str] = "wss://stream.bybit.com/v5/public/spot"

    # Topics can be CSV or list via .env
    ws_sub_topics_linear: Optional[str | List[str]] = "tickers.BTCUSDT,tickers.ETHUSDT"
    ws_sub_topics_spot: Optional[str | List[str]] = "tickers.BTCUSDT,tickers.ETHUSDT"


class AlertsConfig(BaseModel):
    """Alert thresholds & throttling (validated)."""

    threshold_pct: float = Field(
        default=1.0,
        ge=0.0,
        le=100.0,
        description="Basis % threshold to trigger an alert (0..100).",
    )
    cooldown_sec: int = Field(
        default=300,
        ge=0,
        le=86_400,
        description="Per-symbol cooldown to avoid spam, seconds (0..86400).",
    )


class LiquidityConfig(BaseModel):
    """Liquidity filters (validated)."""

    min_vol_24h_usd: float = Field(
        default=10_000_000.0,
        ge=0.0,
        description="Minimum 24h USD volume to consider asset liquid.",
    )
    min_price: float = Field(
        default=0.001,
        ge=0.0,
        description="Minimum last price to exclude very low-priced assets.",
    )


class RuntimeConfig(BaseModel):
    """Runtime behavior & misc toggles (validated)."""

    env: Literal["dev", "prod"] = "dev"
    db_path: str = "data/signals.db"
    top_n_report: int = Field(default=10, ge=1, le=100)
    enable_alerts: bool = True


# ------------------- Root settings -------------------


class AppSettings(BaseSettings):
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # ---------- EXISTING TOP-LEVEL FIELDS (back-compat kept) ----------
    # General
    env: str = "dev"

    # Thresholds / cooldowns
    alert_threshold_pct: float = 1.0
    alert_cooldown_sec: int = 300

    # Filters
    min_vol_24h_usd: float = 10_000_000.0
    min_price: float = 0.001

    # DB path
    db_path: str = "data/signals.db"

    # Report / runtime
    top_n_report: int = 10
    enable_alerts: bool = True

    # Allowed/denied symbol lists (CSV or list in .env)
    allow_symbols: Optional[str | List[str]] = None
    deny_symbols: Optional[str | List[str]] = None

    # WS options (flat fields for back-compat; primary values live in BybitConfig)
    ws_enabled: bool = True
    ws_public_url_linear: Optional[str] = None
    ws_public_url_spot: Optional[str] = None
    ws_sub_topics_linear: Optional[str | List[str]] = None
    ws_sub_topics_spot: Optional[str | List[str]] = None
    ws_reconnect_max_sec: Optional[int] = 30

    # Runtime meta
    rt_meta_refresh_sec: int = 30
    rt_log_passes: int = 1

    # ---------- NEW NESTED SECTIONS ----------
    telegram: TelegramConfig = TelegramConfig()
    bybit: BybitConfig = BybitConfig()
    alerts: AlertsConfig = AlertsConfig()
    liquidity: LiquidityConfig = LiquidityConfig()
    runtime: RuntimeConfig = RuntimeConfig()

    # --------- Handy computed properties (kept) ---------
    @property
    def allow_symbols_list(self) -> List[str]:
        return _csv_list(self.allow_symbols)

    @property
    def deny_symbols_list(self) -> List[str]:
        return _csv_list(self.deny_symbols)

    @property
    def ws_topics_list_linear(self) -> List[str]:
        # back-compat: some code may read this name
        src = self.ws_sub_topics_linear or self.bybit.ws_sub_topics_linear
        return _csv_list(src)

    @property
    def ws_topics_list_spot(self) -> List[str]:
        # back-compat
        src = self.ws_sub_topics_spot or self.bybit.ws_sub_topics_spot
        return _csv_list(src)


# ------------------- Loader with merging/validation -------------------


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    """
    Load settings from .env / env vars with hardening.

    Back-compat bridges included:
      - Flat TELEGRAM_* / TG_* → nested telegram.token / telegram.chat_id if nested empty
      - Flat WS fields on top-level used if bybit.* absent
      - Flat legacy keys for alerts/liquidity/runtime override nested sections
      - Final instance is reconstructed so that top-level mirrors nested (single source of truth)
    """
    autoload_env()  # idempotent

    # 1) First pass: parse everything the usual way (nested & flat)
    base = AppSettings()

    # 2) Build nested sections with overrides from flat legacy keys (if present)
    telegram = TelegramConfig(
        token=_from_env_many(
            "TELEGRAM__TOKEN",
            "TELEGRAM_TOKEN",
            "TELEGRAM_BOT_TOKEN",
            default=base.telegram.token or "",
        ),
        chat_id=_from_env_many(
            "TELEGRAM__CHAT_ID",
            "TELEGRAM_CHAT_ID",
            "TG_CHAT_ID",
            "TELEGRAM_ALERT_CHAT_ID",
            default=base.telegram.chat_id or "",
        ),
    )

    bybit = BybitConfig(
        api_key=_from_env_many(
            "BYBIT__API_KEY", "BYBIT_API_KEY", default=base.bybit.api_key or ""
        ),
        api_secret=_from_env_many(
            "BYBIT__API_SECRET", "BYBIT_API_SECRET", default=base.bybit.api_secret or ""
        ),
        ws_public_url_linear=base.bybit.ws_public_url_linear,
        ws_public_url_spot=base.bybit.ws_public_url_spot,
        ws_sub_topics_linear=base.bybit.ws_sub_topics_linear,
        ws_sub_topics_spot=base.bybit.ws_sub_topics_spot,
    )

    alerts = AlertsConfig(
        threshold_pct=_from_env_many_float(
            "ALERTS__THRESHOLD_PCT",
            "ALERT_THRESHOLD_PCT",
            default=base.alerts.threshold_pct,
        )
        or base.alerts.threshold_pct,
        cooldown_sec=_from_env_many_int(
            "ALERTS__COOLDOWN_SEC",
            "ALERT_COOLDOWN_SEC",
            default=base.alerts.cooldown_sec,
        )
        or base.alerts.cooldown_sec,
    )

    liquidity = LiquidityConfig(
        min_vol_24h_usd=_from_env_many_float(
            "LIQUIDITY__MIN_VOL_24H_USD",
            "MIN_VOL_24H_USD",
            default=base.liquidity.min_vol_24h_usd,
        )
        or base.liquidity.min_vol_24h_usd,
        min_price=_from_env_many_float(
            "LIQUIDITY__MIN_PRICE", "MIN_PRICE", default=base.liquidity.min_price
        )
        or base.liquidity.min_price,
    )

    runtime = RuntimeConfig(
        env=_from_env_many("RUNTIME__ENV", "ENV", default=base.runtime.env)
        or base.runtime.env,
        db_path=_from_env_many(
            "RUNTIME__DB_PATH", "DB_PATH", default=base.runtime.db_path
        )
        or base.runtime.db_path,
        top_n_report=_from_env_many_int(
            "RUNTIME__TOP_N_REPORT", "TOP_N_REPORT", default=base.runtime.top_n_report
        )
        or base.runtime.top_n_report,
        enable_alerts=_from_env_many_bool(
            "RUNTIME__ENABLE_ALERTS",
            "ENABLE_ALERTS",
            default=base.runtime.enable_alerts,
        )
        if _from_env_many("RUNTIME__ENABLE_ALERTS", "ENABLE_ALERTS", default="") != ""
        else base.runtime.enable_alerts,
    )

    # 3) Reconstruct final AppSettings so validation is applied and
    #    top-level values mirror nested sections (single source of truth)
    s = AppSettings(
        # keep existing top-levels but source them from nested validated values where applicable
        env=runtime.env,
        alert_threshold_pct=alerts.threshold_pct,
        alert_cooldown_sec=alerts.cooldown_sec,
        min_vol_24h_usd=liquidity.min_vol_24h_usd,
        min_price=liquidity.min_price,
        db_path=runtime.db_path,
        top_n_report=runtime.top_n_report,
        enable_alerts=runtime.enable_alerts,
        allow_symbols=base.allow_symbols,
        deny_symbols=base.deny_symbols,
        ws_enabled=base.ws_enabled,
        ws_public_url_linear=base.ws_public_url_linear,
        ws_public_url_spot=base.ws_public_url_spot,
        ws_sub_topics_linear=base.ws_sub_topics_linear,
        ws_sub_topics_spot=base.ws_sub_topics_spot,
        ws_reconnect_max_sec=base.ws_reconnect_max_sec,
        rt_meta_refresh_sec=base.rt_meta_refresh_sec,
        rt_log_passes=base.rt_log_passes,
        telegram=telegram,
        bybit=bybit,
        alerts=alerts,
        liquidity=liquidity,
        runtime=runtime,
    )

    # 4) Additional back-compat for WS fields (top-level vs bybit.*)
    if not s.ws_public_url_linear and s.bybit.ws_public_url_linear:
        s.ws_public_url_linear = s.bybit.ws_public_url_linear
    if not s.ws_public_url_spot and s.bybit.ws_public_url_spot:
        s.ws_public_url_spot = s.bybit.ws_public_url_spot
    if s.ws_sub_topics_linear is None and s.bybit.ws_sub_topics_linear is not None:
        s.ws_sub_topics_linear = s.bybit.ws_sub_topics_linear
    if s.ws_sub_topics_spot is None and s.bybit.ws_sub_topics_spot is not None:
        s.ws_sub_topics_spot = s.bybit.ws_sub_topics_spot

    return s
