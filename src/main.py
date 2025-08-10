from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from src.infra.config import load_settings
from src.infra.logging import setup_logging
from src.exchanges.bybit.rest import BybitRest


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
    """
    Проста перевірка REST: запит часу сервера (публічний ендпоінт).
    """
    client = BybitRest()
    data = client.get_server_time()  # dict
    result = data.get("result", {})
    print("Bybit time (sec):", result.get("timeSecond"))
    return 0


def _parse_turnover_usd(row: Dict[str, Any]) -> float:
    for key in ("turnover24h", "turnoverUsd"):
        v = row.get(key)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return 0.0


def cmd_bybit_top(args: argparse.Namespace) -> int:
    """
    Вивести топ тікерів за 24h оборотом (USD) для категорії.
    """
    client = BybitRest()
    data = client.get_tickers(category=args.category)
    rows = data.get("result", {}).get("list", [])

    rows.sort(key=_parse_turnover_usd, reverse=True)
    top = rows[: args.limit]

    print(f"Top {args.limit} by 24h turnover (category={args.category}):")
    for i, r in enumerate(top, 1):
        sym = r.get("symbol", "-")
        last = r.get("lastPrice") or r.get("lastPriceLatest") or "-"
        usd = _parse_turnover_usd(r)
        print(f"{i:>2}. {sym:<14} last={last}  turnover=${usd:,.0f}")
    return 0


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

    args = parser.parse_args()

    # ініціалізація логування
    log_dir = Path("./logs")
    setup_logging(log_dir, level="DEBUG")

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
