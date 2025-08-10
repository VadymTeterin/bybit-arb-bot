from __future__ import annotations

import argparse
import sys

from loguru import logger

from src.infra.config import load_settings
from src.infra.logging import setup_logging

APP_VERSION = "0.1.0"


def cmd_version() -> int:
    print(APP_VERSION)
    return 0


def cmd_env() -> int:
    s = load_settings()
    # короткий читабельний вивід ключових параметрів
    print("ENV:", s.env)
    print("ALERT_THRESHOLD_PCT:", s.alert_threshold_pct)
    print("ALERT_COOLDOWN_SEC:", s.alert_cooldown_sec)
    print("MIN_VOL_24H_USD:", s.min_vol_24h_usd)
    print("TG_CHAT_ID:", s.telegram.alert_chat_id or "")
    print("BYBIT_API_KEY set:", bool(s.bybit.api_key))
    return 0


def cmd_logtest() -> int:
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.success("Success message")
    print("Check logs in ./logs/app.log")
    return 0


def cmd_healthcheck() -> int:
    try:
        s = load_settings()
        assert s.alert_threshold_pct > 0
        assert s.alert_cooldown_sec > 0
        logger.success("Healthcheck OK")
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.exception("Healthcheck FAILED: {}", exc)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="bybit-arb-bot")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version")
    sub.add_parser("env")
    sub.add_parser("logtest")
    sub.add_parser("healthcheck")

    args = parser.parse_args()

    # Ініціалізуємо логування один раз (DEBUG у dev зручно)
    setup_logging(load_settings().log_dir, level="DEBUG")

    match args.command:
        case "version":
            sys.exit(cmd_version())
        case "env":
            sys.exit(cmd_env())
        case "logtest":
            sys.exit(cmd_logtest())
        case "healthcheck":
            sys.exit(cmd_healthcheck())
        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
