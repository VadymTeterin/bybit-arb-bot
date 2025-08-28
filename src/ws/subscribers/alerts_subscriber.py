# src/ws/subscribers/alerts_subscriber.py
from __future__ import annotations

import asyncio
import math
import time
from typing import Any, Awaitable, Callable, Dict, Iterable, Mapping, Optional

from loguru import logger

from src.infra.config import AppSettings, load_settings
from src.telegram.sender import TelegramSender
from src.ws.multiplexer import WsEvent, WSMultiplexer


def _upper_set(items: Optional[Iterable[str]]) -> set[str]:
    if not items:
        return set()
    return {str(x).upper() for x in items}


def _safe_float(x: object | None) -> Optional[float]:
    """Акуратно конвертує у float, повертає None, якщо неможливо."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return None
    return None


class AlertsSubscriber:
    """
    Слухає WS (SPOT/LINEAR), рахує basis% і шле алерти у Telegram
    з урахуванням allow/deny, порогу, cooldown та мін. ціни.
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
        self._enabled: bool = bool(self._s.enable_alerts)
        self._threshold: float = float(self._s.alert_threshold_pct)
        self._cooldown: int = max(0, int(self._s.alert_cooldown_sec))
        self._min_price: float = float(self._s.min_price)
        self._allow: set[str] = _upper_set(getattr(self._s, "allow_symbols_list", []))
        self._deny: set[str] = _upper_set(getattr(self._s, "deny_symbols_list", []))

        # Async sender (тип чітко фіксований як Awaitable[None])
        self._send_async: Callable[[str], Awaitable[None]]
        if send_async is None:
            sender = TelegramSender(
                token=self._s.telegram.token,
                chat_id=self._s.telegram.chat_id,
                # невеликий локальний ліміт, щоб не спамити
                cooldown_s=max(10, min(self._cooldown, 120)),
            )

            async def _default_send(text: str) -> None:
                if not text:
                    return
                ok = await asyncio.to_thread(sender.send, text)
                if not ok:
                    logger.warning("AlertsSubscriber: TelegramSender.send returned False")

            self._send_async = _default_send
        else:
            self._send_async = send_async

        # Unsubscribe callbacks
        self._unsubs: list[Callable[[], None]] = []

    # --------------------------- Public API ---------------------------

    def start(self) -> None:
        """Підписатись на потоки подій."""
        self.stop()  # на всяк випадок при повторному старті

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
        logger.info(
            "AlertsSubscriber started: threshold={:.2f}% cooldown={}s allow={} deny={}",
            self._threshold,
            self._cooldown,
            (len(self._allow) or "-"),
            (len(self._deny) or "-"),
        )

    def stop(self) -> None:
        """Відписатись від усіх джерел."""
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

        sym = (evt.symbol or "").upper()
        if not sym:
            return

        # allow/deny
        if self._allow and sym not in self._allow:
            return
        if self._deny and sym in self._deny:
            return

        # normalize payload
        payload: Mapping[str, object]
        raw_payload: Any = evt.payload or {}
        if isinstance(raw_payload, dict):
            payload = raw_payload
        else:
            # на випадок, якщо прийде щось інше ніж dict
            return

        if (evt.source or "").upper() == "SPOT":
            last = _safe_float(payload.get("last"))
            if last is None:
                return
            self._last_spot[sym] = last
        elif (evt.source or "").upper() == "LINEAR":
            mark = _safe_float(payload.get("mark"))
            if mark is None:
                return
            self._last_mark[sym] = mark
        else:
            return

        # обчислити basis% тільки коли маємо обидві ціни
        sp = self._last_spot.get(sym)
        mk = self._last_mark.get(sym)
        if sp is None or mk is None:
            return
        if sp <= 0 or mk <= 0 or sp < self._min_price:
            return

        basis_pct = (mk - sp) / sp * 100.0
        if math.isnan(basis_pct) or abs(basis_pct) < self._threshold:
            return

        # cooldown
        now = time.time()
        last_ts = self._last_sent_ts.get(sym, 0.0)
        if (now - last_ts) < self._cooldown:
            return

        self._last_sent_ts[sym] = now

        # Надсилання: якщо є активний loop — створюємо таску; інакше — тимчасовий run
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send(sym, basis_pct))
        except RuntimeError:
            asyncio.run(self._send(sym, basis_pct))

    async def _send(self, sym: str, basis_pct: float) -> None:
        sign = "+" if basis_pct >= 0 else ""
        text = "\n".join(
            [
                "*RT Arbitrage Alert*",
                f"{sym}: basis={sign}{basis_pct:.2f}%",
            ]
        )
        try:
            await self._send_async(text)
            logger.success("AlertsSubscriber: alert sent for {}", sym)
        except Exception as e:  # noqa: BLE001
            logger.exception("AlertsSubscriber: send failed: {}", e)
