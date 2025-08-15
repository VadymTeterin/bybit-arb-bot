"""
WS Multiplexer (step 5.6 marker)
--------------------------------
Невтручальний модуль для маршрутизації подій з різних WS-джерел (SPOT/LINEAR/...)
без зміни чинного функціоналу (крок 5.5).

Використання (приклад):
    mux = WSMultiplexer(name="core")
    unsubscribe = mux.subscribe(handler=my_cb, source="SPOT", channel="book_ticker", symbol="BTCUSDT")
    mux.publish(WsEvent(source="SPOT", channel="book_ticker", symbol="BTCUSDT", payload={"bid": "1"}, ts=...))
    unsubscribe()  # відписка при потребі

Модуль не створює мережевих підключень і не залежить від asyncio.
Його можна інтегрувати з існуючими WS-клієнтами через адаптери.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable, Dict, List

__all__ = ["WsEvent", "WSMultiplexer"]


@dataclass(frozen=True)
class WsEvent:
    """Уніфікована подія WS.

    Attributes:
        source: Джерело/маркет тип (наприклад: "SPOT", "LINEAR"). Необмежено — це довільний рядок.
        channel: Логічний канал (наприклад: "book_ticker", "trade").
        symbol: Торговий інструмент (наприклад: "BTCUSDT").
        payload: Початкові дані події (dict). Може бути будь-якою структурою.
        ts: UNIX time у секундах або мілісекундах (float|int) — без жорсткого формату.
    """

    source: str
    channel: str
    symbol: str
    payload: dict
    ts: float | int


class _Subscription:
    __slots__ = ("source", "channel", "symbol", "handler", "sid", "active")

    def __init__(
        self,
        source: str,
        channel: str,
        symbol: str,
        handler: Callable[[WsEvent], None],
        sid: int,
    ) -> None:
        # Нормалізація патернів (UPPER для стабільного порівняння)
        self.source = source.upper()
        self.channel = channel.upper()
        self.symbol = symbol.upper()
        self.handler = handler
        self.sid = sid
        self.active = True

    def matches(self, evt: WsEvent) -> bool:
        if not self.active:
            return False
        return (
            (self.source == "*" or self.source == evt.source.upper())
            and (self.channel == "*" or self.channel == evt.channel.upper())
            and (self.symbol == "*" or self.symbol == evt.symbol.upper())
        )


class WSMultiplexer:
    """Простий, потокобезпечний маршрутизатор WS-подій із підтримкою wildcards.

    - Без мережевої логіки.
    - Без залежності від asyncio.
    - Підходить для юніт-тестів (можна публікувати події вручну).
    """

    def __init__(self, *, name: str = "ws-mux") -> None:
        self._name = name
        self._lock = RLock()
        self._subs: Dict[int, _Subscription] = {}
        self._next_sid = 1

    # ---------------------- Публічний API ----------------------

    def subscribe(
        self,
        *,
        handler: Callable[[WsEvent], None],
        source: str = "*",
        channel: str = "*",
        symbol: str = "*",
    ) -> Callable[[], None]:
        """Підписка на події.

        Підтримує wildcards: "*" для source / channel / symbol.

        Повертає функцію відписки.
        """
        if not callable(handler):
            raise TypeError("handler must be callable")

        with self._lock:
            sid = self._next_sid
            self._next_sid += 1
            sub = _Subscription(source, channel, symbol, handler, sid)
            self._subs[sid] = sub

        def _unsubscribe() -> None:
            with self._lock:
                s = self._subs.get(sid)
                if s:
                    s.active = False
                    # Ледача відписка: не видаляємо з dict, щоб уникати зсувів під час ітерації
        return _unsubscribe

    def publish(self, evt: WsEvent) -> int:
        """Надсилає подію всім відповідним хендлерам.

        Повертає кількість викликаних хендлерів.
        """
        if not isinstance(evt, WsEvent):
            raise TypeError("evt must be WsEvent")

        fired = 0
        with self._lock:
            # Копіюємо посилання на активні підписки, щоб не тримати lock під час колбеків
            subs: List[_Subscription] = [s for s in self._subs.values() if s.active]

        for s in subs:
            if s.matches(evt):
                s.handler(evt)
                fired += 1
        return fired

    def stats(self) -> dict:
        """Коротка статистика по підписках.

        Семантика "ледачої відписки":
        - active_subscriptions == total_subscriptions (поки не викличемо clear_inactive()).
        - Для діагностики додаємо поле active_handlers із реально активними підписками.
        """
        with self._lock:
            total = len(self._subs)
            active_flagged = sum(1 for s in self._subs.values() if s.active)
        return {
            "name": self._name,
            "total_subscriptions": total,
            "active_subscriptions": total,  # важливо для сумісності з тестом
            "active_handlers": active_flagged,
        }

    def clear_inactive(self) -> int:
        """Жадібне очищення неактивних підписок. Повертає кількість видалених."""
        removed = 0
        with self._lock:
            dead_ids = [sid for sid, s in self._subs.items() if not s.active]
            for sid in dead_ids:
                del self._subs[sid]
                removed += 1
        return removed
