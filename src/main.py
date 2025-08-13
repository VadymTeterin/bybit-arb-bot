# src/main.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
from loguru import logger

# --- модулі звітів / БД ---
from src.core.report import format_report, get_top_signals
from src.exchanges.bybit.rest import BybitRest
from src.infra.config import load_settings
from src.infra.logging import setup_logging
from src.infra.notify import send_telegram_message
from src.storage.persistence import init_db

# Опціональна інтеграція з новими модулями (не ламає роботу, якщо їх ще немає / без потрібних функцій)
try:  # telegram форматування повідомлень
    from src.telegram import formatters as _tg_formatters  # type: ignore
except Exception:  # noqa: BLE001
    _tg_formatters = None

try:  # core alerts (наприклад, cooldown, пост-обробка кандидатів)
    from src.core import alerts as _core_alerts  # type: ignore
except Exception:  # noqa: BLE001
    _core_alerts = None


APP_VERSION = "0.4.2"  # 4.4: інтеграція core/alerts + telegram/formatters (опціонально)


def _safe_call(fn, *args, **kwargs):
    """
    Викликає функцію, але tolerant до різниць підпису.
    Повертає None, якщо виклик не вдався або функції немає.
    """
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except TypeError:
        try:
            return fn(*args)  # відкидаємо kwargs, якщо підпис інший
        except Exception:
            return None
    except Exception:
        return None


def cmd_version(_: argparse.Namespace) -> int:
    print(APP_VERSION)
    return 0


def cmd_env(_: argparse.Namespace) -> int:
    s = load_settings()
    print("ENV:", s.env)
    print("ALERT_THRESHOLD_PCT:", s.alert_threshold_pct)
    print("ALERT_COOLDOWN_SEC:", s.alert_cooldown_sec)
    print("MIN_VOL_24H_USD:", s.min_vol_24h_usd)
    print("MIN_PRICE:", s.min_price)
    print("DB_PATH:", s.db_path)
    print("TG_CHAT_ID:", s.telegram.alert_chat_id or "")
    print("TELEGRAM_TOKEN set:", bool(s.telegram.bot_token))
    print("BYBIT_API_KEY set:", bool(s.bybit.api_key))
    # інфо-поля
    print("ENABLE_ALERTS:", s.enable_alerts)
    # виводимо сирі рядки та вже розпарсені списки
    print("ALLOW_SYMBOLS (raw):", s.allow_symbols)
    print("ALLOW_SYMBOLS (list):", ",".join(s.allow_symbols_list))
    print("DENY_SYMBOLS (raw):", s.deny_symbols)
    print("DENY_SYMBOLS (list):", ",".join(s.deny_symbols_list))
    # WS-параметри (4.2+)
    print("WS_ENABLED:", s.ws_enabled)
    print("WS_PUBLIC_URL_LINEAR:", s.ws_public_url_linear)
    print("WS_PUBLIC_URL_SPOT:", s.ws_public_url_spot)
    print("WS_SUB_TOPICS_LINEAR (list):", ",".join(s.ws_topics_list_linear))
    print("WS_SUB_TOPICS_SPOT (list):", ",".join(s.ws_topics_list_spot))
    print("WS_RECONNECT_MAX_SEC:", s.ws_reconnect_max_sec)
    # 4.3
    print("RT_META_REFRESH_SEC:", s.rt_meta_refresh_sec)
    print("RT_LOG_PASSES:", s.rt_log_passes)
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
        assert s.alert_threshold_pct > 0
        assert s.alert_cooldown_sec > 0
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


def _turnover_usd(row: Dict[str, Any]) -> float:
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


def _basis_rows(min_vol: float, threshold: float) -> tuple[
    list[tuple[str, float, float, float, float]],
    list[tuple[str, float, float, float, float]],
]:
    """
    Повертає (rows_pass, rows_all):
      - rows_pass: пари, що пройшли фільтри (vol && |basis|>=threshold)
      - rows_all: усі зіставлені пари для діагностики
    Кортеж елемента: (symbol, spot_price, fut_price, basis_pct, vol_min)
    """
    client = BybitRest()
    spot_map = client.get_spot_map()
    lin_map = client.get_linear_map()

    rows_all: List[tuple[str, float, float, float, float]] = []
    rows_pass: List[tuple[str, float, float, float, float]] = []

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


def cmd_basis_scan(args: argparse.Namespace) -> int:
    s = load_settings()
    min_vol = float(args.min_vol if args.min_vol is not None else s.min_vol_24h_usd)
    threshold = float(
        args.threshold if args.threshold is not None else s.alert_threshold_pct
    )

    rows_pass, rows_all = _basis_rows(min_vol=min_vol, threshold=threshold)

    header = f"Basis scan (spot vs linear). MinVol=${min_vol:,.0f}, Threshold={threshold:.2f}%"
    if rows_pass:
        top = rows_pass[: args.limit]
        print(f"{header} → showing {len(top)}")
        for i, (sym, sp, fu, b, vol) in enumerate(top, 1):
            sign = "+" if b >= 0 else ""
            print(
                f"{i:>2}. {sym:<12} spot={sp:<12g} fut={fu:<12g} basis={sign}{b:.2f}%  vol*=${vol:,.0f}"
            )
    else:
        top = rows_all[: args.limit]
        print(
            f"{header} → no pairs met the threshold; showing diagnostic top {len(top)} (below threshold)"
        )
        for i, (sym, sp, fu, b, vol) in enumerate(top, 1):
            sign = "+" if b >= 0 else ""
            print(
                f"{i:>2}. {sym:<12} spot={sp:<12g} fut={fu:<12g} basis={sign}{b:.2f}%  vol*=${vol:,.0f}"
            )
    return 0


def _alerts_allowed(s) -> bool:
    return bool(s.enable_alerts)


def _format_alert_text(rows: list[tuple[str, float, float, float, float]], threshold: float, min_vol: float) -> str:
    """
    Використовує src/telegram/formatters якщо доступний, інакше — дефолтне форматування.
    """
    if rows:
        header = f"Top {len(rows)} basis (≥ {threshold:.2f}%, MinVol ${min_vol:,.0f})"
        if _tg_formatters and hasattr(_tg_formatters, "format_basis_top"):
            txt = _safe_call(getattr(_tg_formatters, "format_basis_top", None), rows, header)
            if isinstance(txt, str) and txt.strip():
                return txt
        # дефолт
        lines = [header]
        for i, (sym, sp, fu, b, vol) in enumerate(rows, 1):
            sign = "+" if b >= 0 else ""
            lines.append(f"{i}. {sym}: spot={sp:g} fut={fu:g} basis={sign}{b:.2f}%  vol*=${vol:,.0f}")
        return "\n".join(lines)
    else:
        header = f"Basis scan: no pairs ≥ {threshold:.2f}% at MinVol ${min_vol:,.0f}."
        if _tg_formatters and hasattr(_tg_formatters, "format_no_candidates"):
            txt = _safe_call(getattr(_tg_formatters, "format_no_candidates", None), header)
            if isinstance(txt, str) and txt.strip():
                return txt
        # дефолт
        return header + "\nTry lowering threshold or MinVol."


# --------- ПРЕВ'Ю АЛЕРТУ (без відправки) ---------
def preview_message(symbol: str, spot: float, mark: float, vol: float, threshold: float) -> str:
    """
    Формує текст повідомлення для однієї пари, використовуючи форматер (якщо є).
    """
    if spot <= 0 or mark <= 0:
        return "Invalid prices for preview."
    basis = (mark - spot) / spot * 100.0
    rows = [(symbol, spot, mark, basis, vol)]
    return _format_alert_text(rows, threshold=threshold, min_vol=vol)


def cmd_alerts_preview(args: argparse.Namespace) -> int:
    s = load_settings()
    symbol = args.symbol
    spot = float(args.spot)
    mark = float(args.mark)
    vol = float(args.vol)
    threshold = float(args.threshold if args.threshold is not None else s.alert_threshold_pct)
    text = preview_message(symbol, spot, mark, vol, threshold)
    print(text)
    return 0


def cmd_basis_alert(args: argparse.Namespace) -> int:
    s = load_settings()
    if not _alerts_allowed(s):
        print("Alerts are disabled by config (enable_alerts=false).")
        return 0

    min_vol = float(args.min_vol if args.min_vol is not None else s.min_vol_24h_usd)
    threshold = float(
        args.threshold if args.threshold is not None else s.alert_threshold_pct
    )
    limit = int(args.limit)

    if not s.telegram.bot_token or not s.telegram.alert_chat_id:
        print("Telegram is not configured: set TELEGRAM__BOT_TOKEN and TELEGRAM__ALERT_CHAT_ID in .env")
        return 1

    rows_pass, _ = _basis_rows(min_vol=min_vol, threshold=threshold)

    # опціональна пост-обробка кандидатів через core.alerts (наприклад, cooldown)
    if _core_alerts and hasattr(_core_alerts, "apply_cooldown"):
        cooled = _safe_call(getattr(_core_alerts, "apply_cooldown", None), rows_pass, getattr(s, "alert_cooldown_sec", 0))
        if isinstance(cooled, list):
            rows_pass = cooled

    rows = rows_pass[:limit]

    text = _format_alert_text(rows, threshold, min_vol)
    print(text)

    try:
        send_telegram_message(s.telegram.bot_token, s.telegram.alert_chat_id, text)
        logger.success("Telegram alert sent.")
        # опціонально повідомимо core.alerts про успішну відправку
        if _core_alerts and hasattr(_core_alerts, "on_alert_sent"):
            _safe_call(getattr(_core_alerts, "on_alert_sent", None), rows)
    except requests.HTTPError as e:
        logger.error("Telegram HTTP error: {}", e.response.text if e.response is not None else str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Telegram send failed: {}", e)
    return 0


def cmd_tg_send(args: argparse.Namespace) -> int:
    s = load_settings()
    if not _alerts_allowed(s):
        print("Alerts are disabled by config (enable_alerts=false).")
        return 0
    if not s.telegram.bot_token or not s.telegram.alert_chat_id:
        print("Telegram is not configured: set TELEGRAM__BOT_TOKEN and TELEGRAM__ALERT_CHAT_ID in .env")
        return 1
    text = args.text or "Test message from bybit-arb-bot"
    try:
        res = send_telegram_message(s.telegram.bot_token, s.telegram.alert_chat_id, text)
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


# ---------- ЗВІТИ ----------
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
    if not s.telegram.bot_token or not s.telegram.alert_chat_id:
        print("Telegram is not configured: set TELEGRAM__BOT_TOKEN and TELEGRAM__ALERT_CHAT_ID in .env")
        return 1
    hours = int(args.hours)
    limit = int(args.limit) if args.limit is not None else int(s.top_n_report)
    items = get_top_signals(last_hours=hours, limit=limit)
    text = format_report(items)
    try:
        send_telegram_message(s.telegram.bot_token, s.telegram.alert_chat_id, text)
        logger.success("Report sent to Telegram.")
        print("OK")
        return 0
    except requests.HTTPError as e:
        print("Telegram HTTP error:", e.response.text if e.response is not None else str(e))
        return 2
    except Exception as e:  # noqa: BLE001
        print("Telegram error:", str(e))
        return 2


# ---------- SELECTOR SAVE ----------
def cmd_select_save(args: argparse.Namespace) -> int:
    s = load_settings()
    limit = int(args.limit)
    threshold = float(args.threshold) if args.threshold is not None else s.alert_threshold_pct
    min_vol = float(args.min_vol) if args.min_vol is not None else s.min_vol_24h_usd
    min_price = float(args.min_price) if args.min_price is not None else s.min_price
    cooldown_sec = int(args.cooldown_sec) if args.cooldown_sec is not None else s.alert_cooldown_sec

    from src.core.selector import run_selection

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


# ---------- Вивід поточних цін для пари ----------
def create_bybit_client() -> BybitRest:
    return BybitRest()


def cmd_price_pair(args: argparse.Namespace) -> int:
    client = create_bybit_client()
    spot_map = client.get_spot_map()
    lin_map = client.get_linear_map()

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


# ---------- WS:RUN (4.3 realtime basis + filters) ----------
def cmd_ws_run(_: argparse.Namespace) -> int:
    s = load_settings()
    if not s.ws_enabled:
        print("WS is disabled by config (set WS_ENABLED=1 in .env).")
        return 0

    try:
        import asyncio
        from src.exchanges.bybit.ws import BybitWS, iter_ticker_entries
        from src.core.cache import QuoteCache
    except Exception as e:  # noqa: BLE001
        print("WS components are missing. Please add ws.py and cache.py:", str(e))
        return 1

    cache = QuoteCache()

    ws_linear = BybitWS(s.ws_public_url_linear, s.ws_topics_list_linear)
    ws_spot = BybitWS(s.ws_public_url_spot, s.ws_topics_list_spot)

    async def refresh_meta_task():
        client = BybitRest()
        while True:
            try:
                spot_map = client.get_spot_map()
                lin_map = client.get_linear_map()
                combined = {}
                common = set(spot_map.keys()) & set(lin_map.keys())
                for sym in common:
                    try:
                        sv = float(spot_map[sym].get("turnover_usd") or 0.0)
                        lv = float(lin_map[sym].get("turnover_usd") or 0.0)
                        combined[sym] = min(sv, lv)
                    except Exception:
                        continue
                await cache.update_vol24h_bulk(combined)
                logger.bind(tag="RTMETA").info(f"Refreshed vol24h for {len(combined)} symbols")
            except Exception as e:
                logger.bind(tag="RTMETA").warning(f"Meta refresh failed: {e!r}")
            await asyncio.sleep(max(30, int(s.rt_meta_refresh_sec)))

    import math

    async def maybe_log_realtime_pass(sym: str):
        rows = await cache.candidates(
            threshold_pct=s.alert_threshold_pct,
            min_price=s.min_price,
            min_vol24h_usd=s.min_vol_24h_usd,
            allow=s.allow_symbols_list,
            deny=s.deny_symbols_list,
        )
        for rsym, basis in rows[:10]:
            if rsym == sym:
                if s.rt_log_passes:
                    sign = "+" if basis >= 0 else ""
                    logger.bind(tag="RT").success(f"{rsym} basis={sign}{basis:.2f}%  (passes filters)")
                break

    async def on_message_spot(msg: dict):
        for item in iter_ticker_entries(msg):
            sym = item.get("symbol")
            last = item.get("last")
            if sym and last is not None:
                bp = await cache.update(sym, spot=last)
                logger.bind(tag="WS.SPOT").debug(f"{sym} spot={last}")
                if not math.isnan(bp):
                    await maybe_log_realtime_pass(sym)

    async def on_message_linear(msg: dict):
        for item in iter_ticker_entries(msg):
            sym = item.get("symbol")
            mark = item.get("mark")
            if sym and mark is not None:
                bp = await cache.update(sym, linear_mark=mark)
                logger.bind(tag="WS.LINEAR").debug(f"{sym} mark={mark}")
                if not math.isnan(bp):
                    await maybe_log_realtime_pass(sym)

    async def runner():
        await asyncio.gather(
            ws_spot.run(on_message_spot),
            ws_linear.run(on_message_linear),
            refresh_meta_task(),
        )

    try:
        asyncio.run(runner())
        return 0
    except KeyboardInterrupt:
        print("WS stopped by user.")
        return 0
    except Exception as e:  # noqa: BLE001
        logger.exception("WS run failed: {}", e)
        return 2


# -------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(prog="bybit-arb-bot")
    sub = parser.add_subparsers(dest="command", required=True)

    # базові команди
    sub.add_parser("version").set_defaults(func=cmd_version)
    sub.add_parser("env").set_defaults(func=cmd_env)
    sub.add_parser("logtest").set_defaults(func=cmd_logtest)
    sub.add_parser("healthcheck").set_defaults(func=cmd_healthcheck)

    # bybit
    sub.add_parser("bybit:ping").set_defaults(func=cmd_bybit_ping)

    p_top = sub.add_parser("bybit:top")
    p_top.add_argument("--category", default="spot", choices=["spot", "linear", "inverse", "option"])
    p_top.add_argument("--limit", type=int, default=5)
    p_top.set_defaults(func=cmd_bybit_top)

    # basis scan (консольний)
    p_basis = sub.add_parser("basis:scan")
    p_basis.add_argument("--limit", type=int, default=10)
    p_basis.add_argument("--threshold", type=float, default=None)
    p_basis.add_argument("--min-vol", type=float, default=None)
    p_basis.set_defaults(func=cmd_basis_scan)

    # basis alert (telegram)
    p_alert = sub.add_parser("basis:alert")
    p_alert.add_argument("--limit", type=int, default=3)
    p_alert.add_argument("--threshold", type=float, default=None)
    p_alert.add_argument("--min-vol", type=float, default=None)
    p_alert.set_defaults(func=cmd_basis_alert)

    # alerts:preview (формування повідомлення без надсилання)
    p_prev = sub.add_parser("alerts:preview")
    p_prev.add_argument("--symbol", required=True, type=str)
    p_prev.add_argument("--spot", required=True, type=float)
    p_prev.add_argument("--mark", required=True, type=float)
    p_prev.add_argument("--vol", type=float, default=0.0, help="Мін. обіг (USD) серед легів для заголовка")
    p_prev.add_argument("--threshold", type=float, default=None, help="Поріг для заголовка (%, якщо не задано — з .env)")
    p_prev.set_defaults(func=cmd_alerts_preview)

    # telegram test
    p_tg = sub.add_parser("tg:send")
    p_tg.add_argument("--text", type=str, default="Test message from bybit-arb-bot")
    p_tg.set_defaults(func=cmd_tg_send)

    # --- звіти ---
    p_rp = sub.add_parser("report:print")
    p_rp.add_argument("--hours", type=int, default=24)
    p_rp.add_argument("--limit", type=int, default=None)
    p_rp.set_defaults(func=cmd_report_print)

    p_rs = sub.add_parser("report:send")
    p_rs.add_argument("--hours", type=int, default=24)
    p_rs.add_argument("--limit", type=int, default=None)
    p_rs.set_defaults(func=cmd_report_send)

    # --- selector save ---
    p_sel = sub.add_parser("select:save")
    p_sel.add_argument("--limit", type=int, default=3)
    p_sel.add_argument("--threshold", type=float, default=None)
    p_sel.add_argument("--min-vol", type=float, default=None)
    p_sel.add_argument("--min-price", type=float, default=None)
    p_sel.add_argument(
        "--cooldown-sec",
        type=int,
        default=None,
        help="Переважує ALERT_COOLDOWN_SEC з .env",
    )
    p_sel.set_defaults(func=cmd_select_save)

    # --- price:pair ---
    p_pp = sub.add_parser("price:pair")
    p_pp.add_argument(
        "-s",
        "--symbol",
        action="append",
        help="Може повторюватися: -s ETHUSDT -s BTCUSDT. За замовчуванням: ETHUSDT,BTCUSDT",
    )
    p_pp.set_defaults(func=cmd_price_pair)

    # --- ws:run ---
    sub.add_parser("ws:run").set_defaults(func=cmd_ws_run)

    args = parser.parse_args()

    # логування
    log_dir = Path("./logs")
    setup_logging(log_dir, level="DEBUG")

    # --- ініціалізація SQLite БД на старті ---
    try:
        s = load_settings()
        Path(s.db_path).parent.mkdir(parents=True, exist_ok=True)
        init_db()
        logger.success("SQLite initialized at {}", s.db_path)
    except Exception as e:  # noqa: BLE001
        logger.exception("SQLite init failed: {}", e)
        sys.exit(2)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
