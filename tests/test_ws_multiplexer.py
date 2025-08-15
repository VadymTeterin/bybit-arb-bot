import time
import pytest

from src.ws.multiplexer import WSMultiplexer, WsEvent


def make_evt(source="SPOT", channel="book_ticker", symbol="BTCUSDT", payload=None):
    return WsEvent(
        source=source,
        channel=channel,
        symbol=symbol,
        payload={} if payload is None else payload,
        ts=time.time(),
    )


def test_exact_subscription_receives_event():
    mux = WSMultiplexer()
    received = []

    def handler(evt: WsEvent):
        received.append(evt)

    mux.subscribe(
        handler=handler, source="SPOT", channel="book_ticker", symbol="BTCUSDT"
    )

    fired = mux.publish(
        make_evt(
            source="SPOT", channel="book_ticker", symbol="BTCUSDT", payload={"x": 1}
        )
    )

    assert fired == 1
    assert len(received) == 1
    assert received[0].payload["x"] == 1


def test_wildcards_match_multiple_dimensions():
    mux = WSMultiplexer()
    hits = 0

    def handler(evt: WsEvent):
        nonlocal hits
        hits += 1

    # Лише символ
    mux.subscribe(handler=handler, symbol="ETHUSDT")

    # Підходить під всі події з ETHUSDT
    fired1 = mux.publish(make_evt(source="SPOT", channel="trade", symbol="ETHUSDT"))
    fired2 = mux.publish(
        make_evt(source="LINEAR", channel="book_ticker", symbol="ETHUSDT")
    )

    assert fired1 == 1 and fired2 == 1
    assert hits == 2


def test_unsubscribe_stops_delivery():
    mux = WSMultiplexer()
    received = 0

    def handler(evt: WsEvent):
        nonlocal received
        received += 1

    unsubscribe = mux.subscribe(
        handler=handler, source="SPOT", channel="trade", symbol="XRPUSDT"
    )

    assert mux.stats()["active_subscriptions"] == 1

    mux.publish(make_evt(source="SPOT", channel="trade", symbol="XRPUSDT"))
    unsubscribe()  # відписка
    mux.publish(make_evt(source="SPOT", channel="trade", symbol="XRPUSDT"))

    # друга подія не доставлена
    assert received == 1
    assert mux.stats()["active_subscriptions"] == 1  # ледача відписка

    # тепер прибираємо "мертві" підписки
    removed = mux.clear_inactive()
    assert removed == 1
    assert mux.stats()["active_subscriptions"] == 0


def test_publish_returns_number_of_fired_handlers():
    mux = WSMultiplexer()
    c1 = c2 = 0

    def h1(evt: WsEvent):
        nonlocal c1
        c1 += 1

    def h2(evt: WsEvent):
        nonlocal c2
        c2 += 1

    mux.subscribe(handler=h1, channel="book_ticker")
    mux.subscribe(handler=h2, channel="book_ticker", symbol="*")  # явний wildcard

    fired = mux.publish(make_evt(channel="book_ticker", symbol="DOGEUSDT"))
    assert fired == 2
    assert c1 == 1 and c2 == 1


def test_invalid_inputs_raise():
    mux = WSMultiplexer()
    with pytest.raises(TypeError):
        mux.publish("not-an-event")  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        mux.subscribe(handler=123)  # type: ignore[arg-type]
