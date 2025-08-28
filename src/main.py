# src/main.py
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import requests
from loguru import logger

# ---- internal imports at top (to satisfy linters) ----
from .core.report import format_report, get_top_signals
from .exchanges.bybit.rest import BybitRest
from .infra.logging import setup_logging
from .storage.persistence import init_db
from .ws.health import MetricsRegistry  # WS health metrics (singleton)

# Optional Telegram sender: fall back to direct HTTP if infra.telegram is absent
try:
    from .infra import send_telegram_message  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001

    def send_telegram_message(token: str, chat_id: str, text: str):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)
        resp.raise_for_status()
        return resp.json()


# Optional/back-compat modules (used if present)
_core_alerts: ModuleType | None
try:
    from .core import alerts as _core_alerts  # type: ignore[assignment]
except Exception:  # noqa: BLE001
    _core_alerts = None

_tg_formatters: ModuleType | None
try:
    from .telegram import formatters as _tg_formatters  # type: ignore[assignment]
except Exception:  # noqa: BLE001
    _tg_formatters = None


APP_VERSION = "0.4.6"

# --- NEW: global metrics handle for the running process ---
METRICS = MetricsRegistry.get()


# --------------------------------------------------------------------------------------
# Settings loader that is safe at import-time and test-friendly (monkeypatchable)
# --------------------------------------------------------------------------------------
def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default))))
    except Exception:
        return default


def _env_csv(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [t.strip() for t in raw.split(",") if t.strip()]


def load_settings():
    """
    Return settings object. Preferred: delegate to `.settings.load_settings()`.
    Fallback: construct from environment variables (so CLI/tests still run).
    """
    # Try project-defined settings first
    try:
        from .settings import load_settings as _ls  # type: ignore

        return _ls()
    except Exception:
        pass

    # Env-based minimal settings
    class _Obj:
        pass

    s = _Obj()
    s.env = os.getenv("ENV", "dev")
    s.alert_threshold_pct = _env_float("ALERT_THRESHOLD_PCT", 1.0)
    s.alert_cooldown_sec = _env_int("ALERT_COOLDOWN_SEC", 300)
    s.min_vol_24h_usd = _env_float("MIN_VOL_24H_USD", 10_000_000.0)
    s.min_price = _env_float("MIN_PRICE", 0.001)
    s.db_path = os.getenv("DB_PATH", "data/signals.db")
    s.top_n_report = _env_int("TOP_N_REPORT", 3)
    s.enable_alerts = _env_bool("ENABLE_ALERTS", True)

    # Allow/deny lists (optional)
    s.allow_symbols = os.getenv("ALLOW_SYMBOLS", "")
    s.allow_symbols_list = _env_csv("ALLOW_SYMBOLS")
    s.deny_symbols = os.getenv("DENY_SYMBOLS", "")
    s.deny_symbols_list = _env_csv("DENY_SYMBOLS")

    # WS / RT meta (optional)
    s.ws_enabled = _env_bool("WS_ENABLED", True)
    s.ws_public_url_linear = os.getenv(
        "WS_PUBLIC_URL_LINEAR", "wss://stream.bybit.com/v5/public/linear"
    )
    s.ws_public_url_spot = os.getenv("WS_PUBLIC_URL_SPOT", "wss://stream.bybit.com/v5/public/spot")
    s.ws_topics_list_linear = _env_csv("WS_SUB_TOPICS_LINEAR")
    s.ws_topics_list_spot = _env_csv("WS_SUB_TOPICS_SPOT")
    s.ws_reconnect_max_sec = _env_int("WS_RECONNECT_MAX_SEC", 30)
    s.rt_meta_refresh_sec = _env_int("RT_META_REFRESH_SEC", 30)
    s.rt_log_passes = _env_int("RT_LOG_PASSES", 1)

    # Telegram subsection
    class _T:
        pass

    tg = _T()
    tg.token = os.getenv("TELEGRAM__BOT_TOKEN") or os.getenv("TELEGRAM__TOKEN") or ""
    tg.bot_token = tg.token
    tg.chat_id = os.getenv("TELEGRAM__ALERT_CHAT_ID") or os.getenv("TELEGRAM__CHAT_ID") or ""
    tg.alert_chat_id = tg.chat_id
    s.telegram = tg

    # Bybit subsection
    class _B:
        pass

    by = _B()
    by.api_key = os.getenv("BYBIT__API_KEY", "")
    by.api_secret = os.getenv("BYBIT__API_SECRET", "")
    by.ws_public_url_linear = s.ws_public_url_linear
    by.ws_public_url_spot = s.ws_public_url_spot
    by.ws_sub_topics_linear = ",".join(s.ws_topics_list_linear) if s.ws_topics_list_linear else ""
    by.ws_sub_topics_spot = ",".join(s.ws_topics_list_spot) if s.ws_topics_list_spot else ""
    s.bybit = by

    return s


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _safe_call(fn, *args, **kwargs):
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except TypeError:
        try:
            return fn(*args)
        except Exception:
            return None
    except Exception:
        return None


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.buffer.write(text.encode(enc, errors="replace"))
        sys.stdout.buffer.write(b"\n")


def _csv_list(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(t).strip() for t in x if str(t).strip()]
    if isinstance(x, str):
        return [t.strip() for t in x.split(",") if t.strip()]
    return []


def _nested_bybit(s):
    by = getattr(s, "bybit", None)
    url_linear = None
    url_spot = None
    topics_linear: list[str] = []
    topics_spot: list[str] = []
    reconnect_max_sec = getattr(s, "ws_reconnect_max_sec", None)

    if by is not None:
        url_linear = getattr(by, "ws_public_url_linear", None)
        url_spot = getattr(by, "ws_public_url_spot", None)
        topics_linear = _csv_list(getattr(by, "ws_sub_topics_linear", None))
        topics_spot = _csv_list(getattr(by, "ws_sub_topics_spot", None))

    url_linear = url_linear or getattr(s, "ws_public_url_linear", None)
    url_spot = url_spot or getattr(s, "ws_public_url_spot", None)
    topics_linear = topics_linear or _csv_list(getattr(s, "ws_topics_list_linear", None))
    topics_spot = topics_spot or _csv_list(getattr(s, "ws_topics_list_spot", None))

    return {
        "url_linear": url_linear,
        "url_spot": url_spot,
        "topics_linear": topics_linear,
        "topics_spot": topics_spot,
        "reconnect_max_sec": reconnect_max_sec,
    }


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------
def cmd_version(_: argparse.Namespace) -> int:
    print(APP_VERSION)
    return 0


def _tg_fields(s):
    """
    Read Telegram config from settings or environment:
      - settings.telegram.token / bot_token
      - settings.telegram.chat_id / alert_chat_id
      - ENV: TELEGRAM__BOT_TOKEN / TELEGRAM__TOKEN
             TELEGRAM__ALERT_CHAT_ID / TELEGRAM__CHAT_ID
    """
    tg = getattr(s, "telegram", None)
    token = (
        (getattr(tg, "token", None) if tg else None)
        or (getattr(tg, "bot_token", None) if tg else None)
        or os.getenv("TELEGRAM__BOT_TOKEN")
        or os.getenv("TELEGRAM__TOKEN")
    )
    chat_id = (
        (getattr(tg, "chat_id", None) if tg else None)
        or (getattr(tg, "alert_chat_id", None) if tg else None)
        or os.getenv("TELEGRAM__ALERT_CHAT_ID")
        or os.getenv("TELEGRAM__CHAT_ID")
    )
    token = token.strip() if isinstance(token, str) and token.strip() else None
    chat_id = chat_id.strip() if isinstance(chat_id, str) and chat_id.strip() else None
    return token, chat_id


def cmd_env(_: argparse.Namespace) -> int:
    s = load_settings()
    print("ENV:", getattr(s, "env", ""))
    print("ALERT_THRESHOLD_PCT:", getattr(s, "alert_threshold_pct", ""))
    print("ALERT_COOLDOWN_SEC:", getattr(s, "alert_cooldown_sec", ""))
    print("MIN_VOL_24H_USD:", getattr(s, "min_vol_24h_usd", ""))
    print("MIN_PRICE:", getattr(s, "min_price", ""))
    print("DB_PATH:", getattr(s, "db_path", ""))
    token, chat_id = _tg_fields(s)
    print("TG_CHAT_ID:", chat_id or "")
    print("TELEGRAM_TOKEN set:", bool(token))
    by = getattr(s, "bybit", None)
    print("BYBIT_API_KEY set:", bool(getattr(by, "api_key", None)) if by else False)
    print("ENABLE_ALERTS:", getattr(s, "enable_alerts", False))
    print("ALLOW_SYMBOLS (raw):", getattr(s, "allow_symbols", ""))
    print("ALLOW_SYMBOLS (list):", ",".join(getattr(s, "allow_symbols_list", []) or []))
    print("DENY_SYMBOLS (raw):", getattr(s, "deny_symbols", ""))
    print("DENY_SYMBOLS (list):", ",".join(getattr(s, "deny_symbols_list", []) or []))
    print("WS_ENABLED:", getattr(s, "ws_enabled", False))

    ws = _nested_bybit(s)
    print("WS_PUBLIC_URL_LINEAR:", ws["url_linear"] or "")
    print("WS_PUBLIC_URL_SPOT:", ws["url_spot"] or "")
    print("WS_SUB_TOPICS_LINEAR (list):", ",".join(ws["topics_linear"]))
    print("WS_SUB_TOPICS_SPOT (list):", ",".join(ws["topics_spot"]))
    print("WS_RECONNECT_MAX_SEC:", ws["reconnect_max_sec"] or "")
    print("RT_META_REFRESH_SEC:", getattr(s, "rt_meta_refresh_sec", ""))
    print("RT_LOG_PASSES:", getattr(s, "rt_log_passes", ""))
    # Debug/diagnostic WS logging knobs
    print("WS_DEBUG_NORMALIZED:", _env_bool("WS_DEBUG_NORMALIZED", False))
    print("WS_DEBUG_FILTER_CHANNELS:", os.getenv("WS_DEBUG_FILTER_CHANNELS", "ticker"))
    print("WS_DEBUG_FILTER_SYMBOLS:", os.getenv("WS_DEBUG_FILTER_SYMBOLS", ""))
    print("WS_DEBUG_SAMPLE_MS:", _env_int("WS_DEBUG_SAMPLE_MS", 1000))
    return 0


def cmd_logtest(_: argparse.Namespace) -> int:
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.success("Success message")
    print("Check logs in ./logs/app.log")
    return 0


def cmd_healthcheck(_: argparse.Namespace) -> int:
    try:
        s = load_settings()
        assert getattr(s, "alert_threshold_pct", 0) > 0
        assert getattr(s, "alert_cooldown_sec", 0) > 0
        logger.success("Healthcheck OK")
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.exception("Healthcheck FAILED: {}", exc)
        return 1


def cmd_bybit_ping(_: argparse.Namespace) -> int:
    client = BybitRest()
    data = client.get_server_time()
    result = data.get("result", {})
    print("Bybit time (sec):", result.get("timeSecond"))
    return 0


def _turnover_usd(row: dict[str, Any]) -> float:
    for k in ("turnover24h", "turnoverUsd", "turnover_usd"):
        v = row.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return 0.0


def cmd_bybit_top(args: argparse.Namespace) -> int:
    client = BybitRest()
    rows = client.get_tickers(args.category)
    rows.sort(key=_turnover_usd, reverse=True)
    top = rows[: args.limit]
    print(f"Top {args.limit} by 24h turnover (category={args.category}):")
    for i, r in enumerate(top, 1):
        sym = r.get("symbol", "-")
        last = r.get("lastPrice") or r.get("lastPriceLatest") or "-"
        usd = _turnover_usd(r)
        print(f"{i:>2}. {sym:<14} last={last}  turnover=${usd:,.0f}")
    return 0


def _basis_rows(
    min_vol: float, threshold: float
) -> tuple[
    list[tuple[str, float, float, float, float]],
    list[tuple[str, float, float, float, float]],
]:
    client = BybitRest()

    try:
        spot_map = client.get_spot_map()
        lin_map = client.get_linear_map()
    except AttributeError:
        spot_rows = client.get_tickers("spot") or []
        lin_rows = client.get_tickers("linear") or []

        def _map_from_tickers(rows: list[dict[str, Any]]):
            m: dict[str, dict[str, float]] = {}
            for r in rows:
                sym = r.get("symbol")
                if not sym:
                    continue
                price = r.get("lastPrice") or r.get("lastPriceLatest")
                vol = r.get("turnover24h") or r.get("turnoverUsd")
                try:
                    price_f = float(price) if price is not None else 0.0
                    vol_f = float(vol) if vol is not None else 0.0
                except Exception:
                    price_f, vol_f = 0.0, 0.0
                m[sym] = {"price": price_f, "turnover_usd": vol_f}
            return m

        spot_map = _map_from_tickers(spot_rows)
        lin_map = _map_from_tickers(lin_rows)

    rows_all: list[tuple[str, float, float, float, float]] = []
    rows_pass: list[tuple[str, float, float, float, float]] = []

    common = set(spot_map.keys()) & set(lin_map.keys())
    for sym in common:
        sp = spot_map[sym]
        ln = lin_map[sym]
        spot_price = float(sp["price"] or 0.0)
        fut_price = float(ln["price"] or 0.0)
        if spot_price <= 0 or fut_price <= 0:
            continue
        spot_vol = float(sp["turnover_usd"] or 0.0)
        lin_vol = float(ln["turnover_usd"] or 0.0)
        vol_min = min(spot_vol, lin_vol)
        basis_pct = (fut_price - spot_price) / spot_price * 100.0

        rows_all.append((sym, spot_price, fut_price, basis_pct, vol_min))
        if vol_min >= min_vol and abs(basis_pct) >= threshold:
            rows_pass.append((sym, spot_price, fut_price, basis_pct, vol_min))

    rows_all.sort(key=lambda x: abs(x[3]), reverse=True)
    rows_pass.sort(key=lambda x: abs(x[3]), reverse=True)
    return rows_pass, rows_all


def _alerts_allowed(s) -> bool:
    return bool(getattr(s, "enable_alerts", False))


def _format_alert_text(
    rows: list[tuple[str, float, float, float, float]], threshold: float, min_vol: float
) -> str:
    if rows:
        header = f"Top {len(rows)} basis (≥ {threshold:.2f}%, MinVol ${min_vol:,.0f})"
        if _tg_formatters and hasattr(_tg_formatters, "format_basis_top"):
            txt = _safe_call(getattr(_tg_formatters, "format_basis_top", None), rows, header)
            if isinstance(txt, str) and txt.strip():
                return txt
        lines = [header]
        for i, (sym, sp, fu, b, vol) in enumerate(rows, 1):
            sign = "+" if b >= 0 else ""
            lines.append(
                f"{i}. {sym}: spot={sp:g} fut={fu:g} basis={sign}{b:.2f}%  vol*=${vol:,.0f}"
            )
        return "\n".join(lines)
    else:
        header = f"Basis scan: no pairs ≥ {threshold:.2f}% at MinVol ${min_vol:,.0f}."
        if _tg_formatters and hasattr(_tg_formatters, "format_no_candidates"):
            txt = _safe_call(getattr(_tg_formatters, "format_no_candidates", None), header)
            if isinstance(txt, str) and txt.strip():
                return txt
        return header + "\nTry lowering threshold or MinVol."


def preview_message(symbol: str, spot: float, mark: float, vol: float, threshold: float) -> str:
    if spot <= 0 or mark <= 0:
        return "Invalid prices for preview."
    basis = (mark - spot) / spot * 100.0
    rows = [(symbol, spot, mark, basis, vol)]
    return _format_alert_text(rows, threshold=threshold, min_vol=vol)


def _fmt_pct(x: float | None) -> str:
    return f"{x * 100:.2f}%" if x is not None else "n/a"


def _fmt_ts(ts: float | None) -> str:
    if not ts:
        return "n/a"
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return "n/a"


def cmd_alerts_preview(args: argparse.Namespace) -> int:
    s = load_settings()
    symbol = args.symbol
    spot = float(args.spot)
    mark = float(args.mark)
    vol = float(args.vol)
    threshold = float(args.threshold if args.threshold is not None else s.alert_threshold_pct)

    text = preview_message(symbol, spot, mark, vol, threshold)
    safe_print(text)

    try:
        client = BybitRest()
        f = client.get_prev_funding(symbol)
        if isinstance(f, dict):
            rate = f.get("funding_rate", None)
            next_ts = f.get("next_funding_time", None)
        else:
            rate, next_ts = None, None
    except Exception:
        rate, next_ts = None, None

    if rate is not None or next_ts:
        print(f"Funding (prev): {_fmt_pct(rate)}")
        print(f"Next funding: {_fmt_ts(next_ts)}")

    return 0


_FUND_CACHE: dict[str, tuple[float, float | None, float | None]] = {}
_FUND_TTL_SEC = 8 * 60  # 8 hours


def _get_funding_with_cache(client: BybitRest, symbol: str) -> tuple[float | None, float | None]:
    now = time.time()
    cached = _FUND_CACHE.get(symbol)
    if cached and (now - cached[0] < _FUND_TTL_SEC):
        _, r, n = cached
        return r, n
    try:
        f = client.get_prev_funding(symbol)
        if isinstance(f, dict):
            rate = f.get("funding_rate", None)
            next_ts = f.get("next_funding_time", None)
        else:
            rate, next_ts = None, None
    except Exception:
        rate, next_ts = None, None
    _FUND_CACHE[symbol] = (now, rate, next_ts)
    return rate, next_ts


def cmd_basis_alert(args: argparse.Namespace) -> int:
    s = load_settings()
    if not _alerts_allowed(s):
        print("Alerts are disabled by config (enable_alerts=false).")
        return 0

    min_vol = float(args.min_vol if args.min_vol is not None else s.min_vol_24h_usd)
    threshold = float(args.threshold if args.threshold is not None else s.alert_threshold_pct)
    limit = int(args.limit)
    token, chat_id = _tg_fields(s)
    if not token or not chat_id:
        print(
            "Telegram is not configured: set TELEGRAM__BOT_TOKEN and TELEGRAM__ALERT_CHAT_ID in .env"
        )
        return 1

    rows_pass, _ = _basis_rows(min_vol=min_vol, threshold=threshold)

    if _core_alerts and hasattr(_core_alerts, "apply_cooldown"):
        cooled = _safe_call(
            getattr(_core_alerts, "apply_cooldown", None),
            rows_pass,
            getattr(s, "alert_cooldown_sec", 0),
        )
        if isinstance(cooled, list):
            rows_pass = cooled

    rows = rows_pass[:limit]
    text = _format_alert_text(rows, threshold, min_vol)

    used_custom_rows_formatter = bool(
        _tg_formatters and hasattr(_tg_formatters, "format_basis_top")
    )
    if rows and not used_custom_rows_formatter:
        client = BybitRest()
        lines = []
        for sym, _sp, _fu, _b, _vol in rows:
            rate, next_ts = _get_funding_with_cache(client, sym)
            line = f"{sym} • Funding (prev): {_fmt_pct(rate)}; Next: {_fmt_ts(next_ts)}"
            lines.append(line)
        if lines:
            text = text + "\n" + "\n".join(lines)

    safe_print(text)

    try:
        send_telegram_message(token, chat_id, text)
        logger.success("Telegram alert sent.")
        if _core_alerts and hasattr(_core_alerts, "on_alert_sent"):
            _safe_call(getattr(_core_alerts, "on_alert_sent", None), rows)
    except requests.HTTPError as e:
        logger.error(
            "Telegram HTTP error: {}",
            e.response.text if e.response is not None else str(e),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Telegram send failed: {}", e)
    return 0


def cmd_tg_send(args: argparse.Namespace) -> int:
    s = load_settings()
    if not _alerts_allowed(s):
        print("Alerts are disabled by config (enable_alerts=false).")
        return 0
    token, chat_id = _tg_fields(s)
    if not token or not chat_id:
        print(
            "Telegram is not configured: set TELEGRAM__BOT_TOKEN and TELEGRAM__ALERT_CHAT_ID in .env"
        )
        return 1
    text = args.text or "Test message from bybit-arb-bot"
    try:
        res = send_telegram_message(token, chat_id, text)
        ok = res.get("ok")
        print("Telegram send ok:", ok)
        logger.success("Telegram test sent.")
        return 0
    except requests.HTTPError as e:
        body = e.response.text if e.response is not None else str(e)
        print("Telegram HTTP error:", body)
        return 2
    except Exception as e:  # noqa: BLE001
        print("Telegram error:", str(e))
        return 2


def cmd_report_print(args: argparse.Namespace) -> int:
    s = load_settings()
    hours = int(args.hours)
    limit = int(args.limit) if args.limit is not None else int(s.top_n_report)
    items = get_top_signals(last_hours=hours, limit=limit)
    text = format_report(items)
    print(text)
    return 0


def cmd_report_send(args: argparse.Namespace) -> int:
    s = load_settings()
    if not _alerts_allowed(s):
        print("Alerts are disabled by config (enable_alerts=false).")
        return 0
    token, chat_id = _tg_fields(s)
    if not token or not chat_id:
        print(
            "Telegram is not configured: set TELEGRAM__BOT_TOKEN and TELEGRAM__ALERT_CHAT_ID in .env"
        )
        return 1
    hours = int(args.hours)
    limit = int(args.limit) if args.limit is not None else int(s.top_n_report)
    items = get_top_signals(last_hours=hours, limit=limit)
    text = format_report(items)
    try:
        send_telegram_message(token, chat_id, text)
        logger.success("Report sent to Telegram.")
        print("OK")
        return 0
    except requests.HTTPError as e:
        print(
            "Telegram HTTP error:",
            e.response.text if e.response is not None else str(e),
        )
        return 2
    except Exception as e:  # noqa: BLE001
        print("Telegram error:", str(e))
        return 2


def cmd_select_save(args: argparse.Namespace) -> int:
    s = load_settings()
    limit = int(args.limit)
    threshold = float(args.threshold) if args.threshold is not None else s.alert_threshold_pct
    min_vol = float(args.min_vol) if args.min_vol is not None else s.min_vol_24h_usd
    min_price = float(args.min_price) if args.min_price is not None else s.min_price
    cooldown_sec = int(args.cooldown_sec) if args.cooldown_sec is not None else s.alert_cooldown_sec

    from .core.selector import run_selection

    saved = run_selection(
        min_vol=min_vol,
        min_price=min_price,
        threshold=threshold,
        limit=limit,
        cooldown_sec=cooldown_sec,
        client=None,
    )

    if not saved:
        print("No new signals saved (maybe cooldown or no pairs above threshold).")
        return 0

    print(f"Saved {len(saved)} signal(s): " + ", ".join(row["symbol"] for row in saved))
    return 0


def create_bybit_client() -> BybitRest:
    return BybitRest()


def cmd_price_pair(args: argparse.Namespace) -> int:
    client = create_bybit_client()

    try:
        spot_map = client.get_spot_map()
        lin_map = client.get_linear_map()
    except AttributeError:
        spot_rows = client.get_tickers("spot") or []
        lin_rows = client.get_tickers("linear") or []

        def _map_from_tickers(rows: list[dict[str, Any]]):
            m: dict[str, dict[str, float]] = {}
            for r in rows:
                sym = r.get("symbol")
                if not sym:
                    continue
                price = r.get("lastPrice") or r.get("lastPriceLatest")
                vol = r.get("turnover24h") or r.get("turnoverUsd")
                try:
                    price_f = float(price) if price is not None else 0.0
                    vol_f = float(vol) if vol is not None else 0.0
                except Exception:
                    price_f, vol_f = 0.0, 0.0
                m[sym] = {"price": price_f, "turnover_usd": vol_f}
            return m

        spot_map = _map_from_tickers(spot_rows)
        lin_map = _map_from_tickers(lin_rows)

    symbols = args.symbol if args.symbol else ["ETHUSDT", "BTCUSDT"]

    printed_any = False
    for sym in symbols:
        sp = spot_map.get(sym)
        ln = lin_map.get(sym)
        if not sp and not ln:
            print(f"{sym}: not found on SPOT or LINEAR")
            continue
        spot_price = float(sp["price"]) if sp and sp.get("price") else None
        fut_price = float(ln["price"]) if ln and ln.get("price") else None

        line = [sym]
        line.append(f"spot={spot_price:g}" if spot_price is not None else "spot=-")
        line.append(f"fut={fut_price:g}" if fut_price is not None else "fut=-")

        if spot_price and fut_price and spot_price > 0:
            basis = (fut_price - spot_price) / spot_price * 100.0
            sign = "+" if basis >= 0 else ""
            line.append(f"basis={sign}{basis:.2f}%")

        print("  ".join(line))
        printed_any = True

    if not printed_any:
        print("No data to show.")
    return 0


def cmd_ws_run(_: argparse.Namespace) -> int:
    s = load_settings()
    if not getattr(s, "ws_enabled", False):
        print("WS is disabled by config (set WS_ENABLED=1 in .env).")
        return 0

    try:
        import asyncio

        from .core.cache import QuoteCache
        from .exchanges.bybit.ws import BybitWS, iter_ticker_entries
        from .ws.bridge import publish_bybit_ticker
        from .ws.multiplexer import WsEvent, WSMultiplexer

        # Normalized event factory
        from .ws.normalizers.bybit_v5 import normalize
        from .ws.subscribers.alerts_subscriber import AlertsSubscriber
    except Exception as e:  # noqa: BLE001
        print("WS components are missing. Please add ws.py and cache.py:", str(e))
        return 1

    ws = _nested_bybit(s)
    url_linear: str | None = ws["url_linear"]
    url_spot: str | None = ws["url_spot"]
    topics_linear: list[str] = ws["topics_linear"]
    topics_spot: list[str] = ws["topics_spot"]

    cache = QuoteCache()
    ws_linear = BybitWS(url_linear, topics_linear or ["tickers"]) if url_linear else None
    ws_spot = BybitWS(url_spot, topics_spot or ["tickers"]) if url_spot else None

    if not ws_linear and not ws_spot:
        print("WS config has neither LINEAR nor SPOT endpoints/topics configured.")
        return 0

    mux = WSMultiplexer(name="core")

    alerts_sub = AlertsSubscriber(mux)
    alerts_sub.start()

    # --- Debug knobs for normalized flow ---
    debug_norm = _env_bool("WS_DEBUG_NORMALIZED", False)
    _channels_env = os.getenv("WS_DEBUG_FILTER_CHANNELS", "ticker")
    debug_channels = set(_csv_list(_channels_env)) if _channels_env else set()
    debug_symbols = set(_csv_list(os.getenv("WS_DEBUG_FILTER_SYMBOLS", "")))
    debug_sample_ms = _env_int("WS_DEBUG_SAMPLE_MS", 1000)
    _last_log: dict[tuple[str, str, str], float] = {}

    if debug_norm:
        logger.bind(tag="WS").info(
            "WS debug enabled: channels=%s symbols=%s sample_ms=%s",
            ",".join(sorted(debug_channels)) if debug_channels else "*",
            ",".join(sorted(debug_symbols)) if debug_symbols else "*",
            debug_sample_ms,
        )

    def _debug_log_normalized(source: str, evt_norm: dict) -> None:
        """Lightweight anti-spam logger for normalized events (filter + sampling)."""
        if not debug_norm:
            return
        channel = str(evt_norm.get("channel") or "")
        symbol = str(evt_norm.get("symbol") or "")
        if not channel or channel == "other":
            return
        if not symbol:
            return
        if debug_channels and channel not in debug_channels:
            return
        if debug_symbols and symbol not in debug_symbols:
            return
        data = evt_norm.get("data")
        items = 1 if isinstance(data, dict) else (len(data) if isinstance(data, list) else 0)
        key = (source, channel, symbol)
        now = time.monotonic()
        last = _last_log.get(key, 0.0)
        if (now - last) * 1000.0 < max(0, debug_sample_ms):
            return
        _last_log[key] = now
        logger.bind(tag="WS").debug(
            f"{source} normalized: channel={channel} symbol={symbol} items={items}"
        )

    async def refresh_meta_task():
        client = BybitRest()
        while True:
            try:
                spot_rows = client.get_tickers("spot") or []
                lin_rows = client.get_tickers("linear") or []

                def _vol_map(rows: list[dict[str, Any]]) -> dict[str, float]:
                    m: dict[str, float] = {}
                    for r in rows:
                        sym = r.get("symbol")
                        if not sym:
                            continue
                        v = r.get("turnover24h") or r.get("turnoverUsd")
                        try:
                            m[sym] = float(v) if v is not None else 0.0
                        except Exception:
                            m[sym] = 0.0
                    return m

                spot_vol = _vol_map(spot_rows)
                lin_vol = _vol_map(lin_rows)

                combined = {
                    sym: min(spot_vol[sym], lin_vol[sym]) for sym in (set(spot_vol) & set(lin_vol))
                }
                await cache.update_vol24h_bulk(combined)
                logger.bind(tag="RTMETA").info(f"Refreshed vol24h for {len(combined)} symbols")
            except Exception as e:
                logger.bind(tag="RTMETA").warning(f"Meta refresh failed: {e!r}")
            await asyncio.sleep(max(30, int(getattr(s, "rt_meta_refresh_sec", 30))))

    # ----------------------------
    # on_message handlers
    # ----------------------------
    async def on_message_spot(msg: dict):
        # 1) Normalized event publish
        try:
            evt_norm = normalize(msg)
            _debug_log_normalized("SPOT", evt_norm)
            mux.publish(
                WsEvent(
                    source="SPOT",
                    channel=str(evt_norm.get("channel") or "other"),
                    symbol=str(evt_norm.get("symbol") or ""),
                    payload=evt_norm.get("data") or {},
                    ts=evt_norm.get("ts_ms") or 0,
                )
            )
            # --- NEW: increment SPOT counter after successful normalized publish ---
            METRICS.inc_spot()
        except Exception as e:
            logger.debug(f"normalize(msg) failed (SPOT): {e!r}")

        # 2) Compatibility path for existing subscribers
        for item in iter_ticker_entries(msg):
            sym = item.get("symbol")
            last = item.get("last")
            if sym and last is not None:
                _ = await cache.update(sym, spot=last)
                publish_bybit_ticker(mux, "SPOT", item)

    async def on_message_linear(msg: dict):
        # 1) Normalized event publish
        try:
            evt_norm = normalize(msg)
            _debug_log_normalized("LINEAR", evt_norm)
            mux.publish(
                WsEvent(
                    source="LINEAR",
                    channel=str(evt_norm.get("channel") or "other"),
                    symbol=str(evt_norm.get("symbol") or ""),
                    payload=evt_norm.get("data") or {},
                    ts=evt_norm.get("ts_ms") or 0,
                )
            )
            # --- NEW: increment LINEAR counter after successful normalized publish ---
            METRICS.inc_linear()
        except Exception as e:
            logger.debug(f"normalize(msg) failed (LINEAR): {e!r}")

        # 2) Compatibility path for existing subscribers
        for item in iter_ticker_entries(msg):
            sym = item.get("symbol")
            mark = item.get("mark")
            if sym and mark is not None:
                _ = await cache.update(sym, linear_mark=mark)
                publish_bybit_ticker(mux, "LINEAR", item)

    async def runner():
        import asyncio as _asyncio

        tasks = []
        if ws_spot:
            tasks.append(ws_spot.run(on_message_spot))
        if ws_linear:
            tasks.append(ws_linear.run(on_message_linear))
        tasks.append(refresh_meta_task())
        await _asyncio.gather(*tasks)

    try:
        import asyncio as _asyncio

        _asyncio.run(runner())
        return 0
    except KeyboardInterrupt:
        print("WS stopped by user.")
        return 0
    except Exception as e:  # noqa: BLE001
        logger.exception("WS run failed: {}", e)
        return 2


def cmd_basis_scan(args: argparse.Namespace) -> int:
    s = load_settings()
    min_vol = float(args.min_vol if args.min_vol is not None else s.min_vol_24h_usd)
    threshold = float(args.threshold if args.threshold is not None else s.alert_threshold_pct)
    limit = int(args.limit)

    rows_pass, _ = _basis_rows(min_vol=min_vol, threshold=threshold)
    rows = rows_pass[:limit]
    text = _format_alert_text(rows, threshold=threshold, min_vol=min_vol)
    safe_print(text)
    return 0


# --- ws:health command ---
def cmd_ws_health(args: argparse.Namespace) -> int:
    """
    Print current WS health metrics as JSON. Optional --reset to zero counters.
    """
    reg = MetricsRegistry.get()
    if getattr(args, "reset", False):
        reg.reset()
    data = reg.snapshot()
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(prog="bybit-arb-bot")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version").set_defaults(func=cmd_version)
    sub.add_parser("env").set_defaults(func=cmd_env)
    sub.add_parser("logtest").set_defaults(func=cmd_logtest)
    sub.add_parser("healthcheck").set_defaults(func=cmd_healthcheck)

    sub.add_parser("bybit:ping").set_defaults(func=cmd_bybit_ping)

    p_top = sub.add_parser("bybit:top")
    p_top.add_argument(
        "--category", default="spot", choices=["spot", "linear", "inverse", "option"]
    )
    p_top.add_argument("--limit", type=int, default=5)
    p_top.set_defaults(func=cmd_bybit_top)

    p_basis = sub.add_parser("basis:scan")
    p_basis.add_argument("--limit", type=int, default=10)
    p_basis.add_argument("--threshold", type=float, default=None)
    p_basis.add_argument("--min-vol", type=float, default=None)
    p_basis.set_defaults(func=cmd_basis_scan)

    p_alert = sub.add_parser("basis:alert")
    p_alert.add_argument("--limit", type=int, default=3)
    p_alert.add_argument("--threshold", type=float, default=None)
    p_alert.add_argument("--min-vol", type=float, default=None)
    p_alert.set_defaults(func=cmd_basis_alert)

    p_prev = sub.add_parser("alerts:preview")
    p_prev.add_argument("--symbol", required=True, type=str)
    p_prev.add_argument("--spot", required=True, type=float)
    p_prev.add_argument("--mark", required=True, type=float)
    p_prev.add_argument(
        "--vol",
        type=float,
        default=0.0,
        help="24h turnover (USD) for the symbol",
    )
    p_prev.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Basis threshold in %, overrides config if set",
    )
    p_prev.set_defaults(func=cmd_alerts_preview)

    p_tg = sub.add_parser("tg:send")
    p_tg.add_argument("--text", type=str, default="Test message from bybit-arb-bot")
    p_tg.set_defaults(func=cmd_tg_send)

    p_rp = sub.add_parser("report:print")
    p_rp.add_argument("--hours", type=int, default=24)
    p_rp.add_argument("--limit", type=int, default=None)
    p_rp.set_defaults(func=cmd_report_print)

    p_rs = sub.add_parser("report:send")
    p_rs.add_argument("--hours", type=int, default=24)
    p_rs.add_argument("--limit", type=int, default=None)
    p_rs.set_defaults(func=cmd_report_send)

    p_sel = sub.add_parser("select:save")
    p_sel.add_argument("--limit", type=int, default=3)
    p_sel.add_argument("--threshold", type=float, default=None)
    p_sel.add_argument("--min-vol", type=float, default=None)
    p_sel.add_argument("--min-price", type=float, default=None)
    p_sel.add_argument(
        "--cooldown-sec",
        type=int,
        default=None,
        help="Override ALERT_COOLDOWN_SEC from .env",
    )
    p_sel.set_defaults(func=cmd_select_save)

    p_pp = sub.add_parser("price:pair")
    p_pp.add_argument(
        "-s",
        "--symbol",
        action="append",
        help="Symbols to show, e.g. ETHUSDT,BTCUSDT (can repeat -s)",
    )
    p_pp.set_defaults(func=cmd_price_pair)

    sub.add_parser("ws:run").set_defaults(func=cmd_ws_run)

    # WS health metrics
    p_wh = sub.add_parser("ws:health")
    p_wh.add_argument("--reset", action="store_true", help="Reset counters before print")
    p_wh.set_defaults(func=cmd_ws_health)

    # NEW: friendly alias for ws:health
    sub.add_parser("status").set_defaults(func=cmd_ws_health)

    args = parser.parse_args()

    log_dir = Path("./logs")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_dir, level=log_level)

    try:
        s = load_settings()
        Path(s.db_path).parent.mkdir(parents=True, exist_ok=True)
        init_db()
        logger.success("SQLite initialized at {}", s.db_path)
    except Exception as e:  # noqa: BLE001
        logger.exception("SQLite init failed: {}", e)
        sys.exit(2)

    sys.exit(args.func(args))


def try_setup_telegram_sender(alerter: Any) -> None:
    try:
        from .core.alerts import RealtimeAlerter  # type: ignore

        if not isinstance(alerter, RealtimeAlerter) or not hasattr(alerter, "set_sender"):
            return
        from .core.alerts import telegram_sender  # type: ignore

        alerter.set_sender(telegram_sender)
        logger.info("Telegram sender wired into RealtimeAlerter.")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to wire Telegram sender: {e!r}")


if __name__ == "__main__":
    main()
