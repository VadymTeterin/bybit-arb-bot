# tests/test_ws_alerts_subscriber.py
import asyncio
import re
from typing import List

from src.infra.config import AppSettings
from src.ws.multiplexer import WsEvent, WSMultiplexer
from src.ws.subscribers.alerts_subscriber import AlertsSubscriber


async def _wait():
    await asyncio.sleep(0.05)


def test_alerts_subscriber_basic_send(monkeypatch):
    mux = WSMultiplexer()

    # capture sink
    out: List[str] = []

    async def fake_send(text: str) -> None:
        out.append(text)

    # lower threshold and no cooldown to make test deterministic
    s = AppSettings(
        enable_alerts=True,
        alert_threshold_pct=0.5,
        alert_cooldown_sec=0,
        min_price=0.0001,
    )
    sub = AlertsSubscriber(mux, s, send_async=fake_send)
    sub.start()

    # publish spot then linear
    mux.publish(
        WsEvent(
            source="SPOT",
            channel="tickers",
            symbol="ETHUSDT",
            payload={"symbol": "ETHUSDT", "last": 100.0},
            ts=0,
        )
    )
    mux.publish(
        WsEvent(
            source="LINEAR",
            channel="tickers",
            symbol="ETHUSDT",
            payload={"symbol": "ETHUSDT", "mark": 101.0},
            ts=0,
        )
    )

    # Python 3.12+: у синхронному тесті немає активного event loop → використовуємо asyncio.run
    asyncio.run(_wait())

    assert len(out) >= 1, "No alert was sent"
    assert re.search(r"ETHUSDT.*basis=\+1\.00%", out[-1])


def test_alerts_subscriber_cooldown(monkeypatch):
    mux = WSMultiplexer()

    out: List[str] = []

    async def fake_send(text: str) -> None:
        out.append(text)

    s = AppSettings(
        enable_alerts=True,
        alert_threshold_pct=0.1,
        alert_cooldown_sec=999,  # big cooldown to suppress second send
        min_price=0.0001,
    )
    sub = AlertsSubscriber(mux, s, send_async=fake_send)
    sub.start()

    mux.publish(
        WsEvent(
            source="SPOT",
            channel="tickers",
            symbol="BTCUSDT",
            payload={"symbol": "BTCUSDT", "last": 100.0},
            ts=0,
        )
    )
    mux.publish(
        WsEvent(
            source="LINEAR",
            channel="tickers",
            symbol="BTCUSDT",
            payload={"symbol": "BTCUSDT", "mark": 110.0},
            ts=0,
        )
    )
    asyncio.run(_wait())

    # second event above threshold but within cooldown
    mux.publish(
        WsEvent(
            source="LINEAR",
            channel="tickers",
            symbol="BTCUSDT",
            payload={"symbol": "BTCUSDT", "mark": 111.0},
            ts=0,
        )
    )
    asyncio.run(_wait())

    assert len(out) == 1, f"Cooldown failed, got {len(out)} messages"
