from src.ws.multiplexer import WSMultiplexer
from src.ws.bridge import publish_bybit_ticker


def test_publish_bybit_ticker_delivers_to_matching_subscription():
    mux = WSMultiplexer()
    captured = []
    unsub = mux.subscribe(
        handler=lambda e: captured.append(e),
        source="SPOT",
        channel="tickers",
        symbol="ETHUSDT",
    )

    item = {"symbol": "ETHUSDT", "last": 2500.0, "mark": 2501.5}
    fired = publish_bybit_ticker(mux, "SPOT", item, ts=123.0)

    assert fired == 1
    assert len(captured) == 1
    evt = captured[0]
    assert evt.source == "SPOT" and evt.channel == "tickers" and evt.symbol == "ETHUSDT"
    assert evt.payload["last"] == 2500.0 and evt.payload["mark"] == 2501.5
    assert evt.ts == 123.0

    unsub()


def test_publish_bybit_ticker_ignores_missing_symbol():
    mux = WSMultiplexer()
    fired = publish_bybit_ticker(mux, "SPOT", {"last": 1.0})
    assert fired == 0
