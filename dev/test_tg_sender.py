from src.infra.notify_telegram import TelegramNotifier
from src.telegram.formatters import format_arbitrage_alert


def main():
    text = format_arbitrage_alert(
        symbol_a="BTCUSDT",
        symbol_b="BTCUSDT:PERP",
        spread_pct=1.00,
        vol_24h=50_000_000,
        basis=0.0100,
    )
    ok = TelegramNotifier(enabled=True).send_text(text)
    print("Telegram send ok:", ok)


if __name__ == "__main__":
    main()
