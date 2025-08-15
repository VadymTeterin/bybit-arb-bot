# src/ws/subscribers/alerts_subscriber.py
from __future__ import annotations

import asyncio
import math
import time
from typing import Callable, Optional, Dict, Awaitable

from loguru import logger

from src.ws.multiplexer import WSMultiplexer, WsEvent
from src.infra.config import AppSettings, load_settings
from src.telegram.sender import TelegramSender


class AlertsSubscriber:
    """
    WS → (spot/linear) → compute basis → Telegram

    Невтручальний підписник мультиплексора:
    - слухає події від Bybit (джерела "SPOT"/"LINEAR", канал "tickers")
    - тримає останні ціни для символів
    - рахує basis% та застосовує cooldown + allow/deny + min_price
    - відправляє коротке повідомлення в Telegram (асинхронно, без блокування event loop)
    """

    def __init__(
        self,
        mux: WSMultiplexer,
        settings: Optional[AppSettings] = None,
        *,
        send_async: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> None:
        self._mux = mux
        self._s = settings or load_settings()

        # Runtime state
        self._last_spot: Dict[str, float] = {}
        self._last_mark: Dict[str, float] = {}
        self._last_sent_ts: Dict[str, float] = {}

        # Config shortcuts
        self._enabled = bool(self._s.enable_alerts)
        self._threshold = float(self._s.alert_threshold_pct)
        self._cooldown = max(0, int(self._s.alert_cooldown_sec))
        self._min_price = float(self._s.min_price)
        self._allow = set(x.upper() for x in self._s.allow_symbols_list)
        self._deny = set(x.upper() for x in self._s.deny_symbols_list)

        # Telegram sender (sync) wrapped into async call via to_thread
        if send_async is None:
            _sender = TelegramSender(
                token=self._s.telegram.bot_token,
                chat_id=self._s.telegram.alert_chat_id,
                cooldown_s=max(10, min(self._cooldown, 120)),  # локальний запобіжник
            )

            async def _default_send(text: str) -> None:
                if not text:
                    return
                ok = await asyncio.to_thread(_sender.send, text)
                if not ok:
                    logger.warning("AlertsSubscriber: TelegramSender.send returned False")

            self._send_async = _default_send
        else:
            self._send_async = send_async

        # Unsubscribe callbacks
        self._unsubs: list[Callable[[], None]] = []

    # --------------------------- Public API ---------------------------

    def start(self) -> None:
        """Підписуємося на події мультиплексора."""
        self.stop()  # на випадок повторного виклику

        def _on_evt(evt: WsEvent) -> None:
            try:
                self._handle_evt(evt)
            except Exception as e:  # noqa: BLE001
                logger.exception("AlertsSubscriber handler failed: {}", e)

        self._unsubs.append(
            self._mux.subscribe(handler=_on_evt, source="SPOT", channel="tickers", symbol="*")
        )
        self._unsubs.append(
            self._mux.subscribe(handler=_on_evt, source="LINEAR", channel="tickers", symbol="*")
        )
        logger.info("AlertsSubscriber started: threshold={:.2f}% cooldown={}s allow={} deny={}",
                    self._threshold, self._cooldown, (len(self._allow) or "-"), (len(self._deny) or "-"))

    def stop(self) -> None:
        """Відписуємося від усіх подій."""
        for u in self._unsubs:
            try:
                u()
            except Exception:
                pass
        self._unsubs.clear()

    # --------------------------- Internals ---------------------------

    def _handle_evt(self, evt: WsEvent) -> None:
        if not self._enabled:
            return

        sym = evt.symbol.upper() if evt.symbol else ""
        if not sym:
            return

        # allow/deny
        if self._allow and sym not in self._allow:
            return
        if self._deny and sym in self._deny:
            return

        # normalize payload
        payload = evt.payload or {}
        if evt.source.upper() == "SPOT":
            last = payload.get("last")
            try:
                self._last_spot[sym] = float(last)
            except Exception:
                return
        elif evt.source.upper() == "LINEAR":
            mark = payload.get("mark")
            try:
                self._last_mark[sym] = float(mark)
            except Exception:
                return
        else:
            return

        # обчислити basis, якщо є обидві ціни
        sp = self._last_spot.get(sym)
        mk = self._last_mark.get(sym)
        if sp is None or mk is None:
            return
        if sp <= 0 or mk <= 0 or sp < self._min_price:
            return

        try:
            basis_pct = (mk - sp) / sp * 100.0
        except Exception:
            return
        if math.isnan(basis_pct) or abs(basis_pct) < self._threshold:
            return

        # cooldown
        now = time.time()
        last = self._last_sent_ts.get(sym, 0.0)
        if (now - last) < self._cooldown:
            return

        self._last_sent_ts[sym] = now

        # Надіслати: якщо є running loop — плануємо задачу,
        # якщо ні (наприклад, unit-тест) — виконуємо одразу через asyncio.run(...)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send(sym, basis_pct))
        except RuntimeError:
            asyncio.run(self._send(sym, basis_pct))

    async def _send(self, sym: str, basis_pct: float) -> None:
        sign = "+" if basis_pct >= 0 else ""
        lines = [
            "*RT Arbitrage Alert*",
            f"{sym}: basis={sign}{basis_pct:.2f}%",
        ]
        text = "\n".join(lines)
        try:
            await self._send_async(text)
            logger.success("AlertsSubscriber: alert sent for {}", sym)
        except Exception as e:  # noqa: BLE001
            logger.exception("AlertsSubscriber: send failed: {}", e)
