from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from loguru import logger
import requests

from src.exchanges.bybit.rest import BybitRest
from src.infra.config import load_settings
from src.infra.logging import setup_logging
from src.infra.notify import send_telegram_message
from src.storage.persistence import init_db  # <-- ДОДАНО

APP_VERSION = "0.1.0"


def cmd_version(_: argparse.Namespace) -> int:
    print(APP_VERSION)
    return 0


def cmd_env(_: argparse.Namespace) -> int:
    s = load_settings()
    print("ENV:", s.env)
    print("ALERT_THRESHOLD_PCT:", s.alert_threshold_pct)
    print("ALERT_COOLDOWN_SEC:", s.alert_cooldown_sec)
    print("MIN_VOL_24H_USD:", s.min_vol_24h_usd)
    print("TG_CHAT_ID:", s.telegram.alert_chat_id or "")
    print("TELEGRAM_TOKEN set:", bool(s.telegram.bot_token))
    print("BYBIT_API_KEY set:", bool(s.bybit.api_key))
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


def _basis_rows(min_vol: float, threshold: float) -> tuple[list[tuple[str, float, float, float, float]], list[tuple[str, float, float, float, float]]]:
    """
    Повертає (rows_pass, rows_all):
      - rows_pass: пари, що пройшли фільтри (vol && |basis|>=threshold)
      - rows_all: усі зіставлені пари для діагностики
    Кортеж елемента: (symbol, spot_price, fut_price, basis_pct, vol_min)
    """
    client = BybitRest()
    spot_map = client.get_spot_map()
    lin_map = client.get_linear_map()

    rows_all: List[Tuple[str, float, float, float, float]] = []
    rows_pass: List[Tuple[str, float, float, float, float]] = []

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
    """
    Зіставляє SPOT і LINEAR та рахує basis %.
    Якщо немає пар вище порога — показує діагностичний top за |basis|.
    """
    s = load_settings()
    min_vol = float(args.min_vol if args.min_vol is not None else s.min_vol_24h_usd)
    threshold = float(args.threshold if args.threshold is not None else s.alert_threshold_pct)

    rows_pass, rows_all = _basis_rows(min_vol=min_vol, threshold=threshold)

    header = f"Basis scan (spot vs linear). MinVol=${min_vol:,.0f}, Threshold={threshold:.2f}%"
    if rows_pass:
        top = rows_pass[: args.limit]
        print(f"{header} → showing {len(top)}")
        for i, (sym, sp, fu, b, vol) in enumerate(top, 1):
            sign = "+" if b >= 0 else ""
            print(f"{i:>2}. {sym:<12} spot={sp:<12g} fut={fu:<12g} basis={sign}{b:.2f}%  vol*=${vol:,.0f}")
    else:
        top = rows_all[: args.limit]
        print(f"{header} → no pairs met the threshold; showing diagnostic top {len(top)} (below threshold)")
        for i, (sym, sp, fu, b, vol) in enumerate(top, 1):
            sign = "+" if b >= 0 else ""
            print(f"{i:>2}. {sym:<12} spot={sp:<12g} fut={fu:<12g} basis={sign}{b:.2f}%  vol*=${vol:,.0f}")
    return 0


def cmd_basis_alert(args: argparse.Namespace) -> int:
    """
    Обчислює basis, фільтрує за порогом і шле топ N у Telegram.
    Якщо пар немає — надсилає діагностичне повідомлення.
    """
    s = load_settings()
    min_vol = float(args.min_vol if args.min_vol is not None else s.min_vol_24h_usd)
    threshold = float(args.threshold if args.threshold is not None else s.alert_threshold_pct)
    limit = int(args.limit)

    if not s.telegram.bot_token or not s.telegram.alert_chat_id:
        print("Telegram is not configured: set TELEGRAM_BOT_TOKEN and TG_ALERT_CHAT_ID in .env")
        return 1

    rows_pass, _ = _basis_rows(min_vol=min_vol, threshold=threshold)
    rows = rows_pass[:limit]

    if not rows:
        text = f"Basis scan: no pairs ≥ {threshold:.2f}% at MinVol ${min_vol:,.0f}.\nTry lowering threshold or MinVol."
        print(text)
        try:
            send_telegram_message(s.telegram.bot_token, s.telegram.alert_chat_id, text)
            logger.success("Telegram notice sent (no pairs).")
        except requests.HTTPError as e:
            logger.error("Telegram HTTP error: {}", e.response.text if e.response is not None else str(e))
        except Exception as e:  # noqa: BLE001
            logger.exception("Telegram send failed: {}", e)
        return 0

    lines = [f"Top {len(rows)} basis (≥ {threshold:.2f}%, MinVol ${min_vol:,.0f})"]
    for i, (sym, sp, fu, b, vol) in enumerate(rows, 1):
        sign = "+" if b >= 0 else ""
        lines.append(f"{i}. {sym}: spot={sp:g} fut={fu:g} basis={sign}{b:.2f}%  vol*=${vol:,.0f}")
    text = "\n".join(lines)
    print(text)
    try:
        send_telegram_message(s.telegram.bot_token, s.telegram.alert_chat_id, text)
        logger.success("Telegram alert sent.")
    except requests.HTTPError as e:
        logger.error("Telegram HTTP error: {}", e.response.text if e.response is not None else str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Telegram send failed: {}", e)
    return 0


def cmd_tg_send(args: argparse.Namespace) -> int:
    """
    Надсилає тестове повідомлення в Telegram з .env.
    Використання: python -m src.main tg:send --text "hello"
    """
    s = load_settings()
    if not s.telegram.bot_token or not s.telegram.alert_chat_id:
        print("Telegram is not configured: set TELEGRAM_BOT_TOKEN and TG_ALERT_CHAT_ID in .env")
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
    p_basis.add_argument("--threshold", type=float, default=None)  # якщо None — з .env
    p_basis.add_argument("--min-vol", type=float, default=None)    # якщо None — з .env
    p_basis.set_defaults(func=cmd_basis_scan)

    # basis alert (telegram)
    p_alert = sub.add_parser("basis:alert")
    p_alert.add_argument("--limit", type=int, default=3)
    p_alert.add_argument("--threshold", type=float, default=None)
    p_alert.add_argument("--min-vol", type=float, default=None)
    p_alert.set_defaults(func=cmd_basis_alert)

    # telegram test
    p_tg = sub.add_parser("tg:send")
    p_tg.add_argument("--text", type=str, default="Test message from bybit-arb-bot")
    p_tg.set_defaults(func=cmd_tg_send)

    args = parser.parse_args()

    # логування
    log_dir = Path("./logs")
    setup_logging(log_dir, level="DEBUG")

    # --- ІНІЦІАЛІЗАЦІЯ SQLite БД (КРОК 2) ---
    try:
        s = load_settings()
        Path(s.db_path).parent.mkdir(parents=True, exist_ok=True)  # гарантуємо існування папки data/
        init_db()
        logger.success("SQLite initialized at {}", s.db_path)
    except Exception as e:  # noqa: BLE001
        logger.exception("SQLite init failed: {}", e)
        sys.exit(2)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
