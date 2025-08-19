# src/ws/subscribers/alerts_subscriber.py
from __future__ import annotations

import asyncio
import math
import time
from typing import Awaitable, Callable, Dict, Optional

from loguru import logger

from src.infra.config import AppSettings, load_settings
from src.telegram.sender import TelegramSender
from src.ws.multiplexer import WsEvent, WSMultiplexer


class AlertsSubscriber:
    """
    WS РІвЂ вЂ™ (spot/linear) РІвЂ вЂ™ compute basis РІвЂ вЂ™ Telegram

    Р СњР ВµР Р†РЎвЂљРЎР‚РЎС“РЎвЂЎР В°Р В»РЎРЉР Р…Р С‘Р в„– Р С—РЎвЂ“Р Т‘Р С—Р С‘РЎРѓР Р…Р С‘Р С” Р СРЎС“Р В»РЎРЉРЎвЂљР С‘Р С—Р В»Р ВµР С”РЎРѓР С•РЎР‚Р В°:
    - РЎРѓР В»РЎС“РЎвЂ¦Р В°РЎвЂќ Р С—Р С•Р Т‘РЎвЂ“РЎвЂ” Р Р†РЎвЂ“Р Т‘ Bybit (Р Т‘Р В¶Р ВµРЎР‚Р ВµР В»Р В° "SPOT"/"LINEAR", Р С”Р В°Р Р…Р В°Р В» "tickers")
    - РЎвЂљРЎР‚Р С‘Р СР В°РЎвЂќ Р С•РЎРѓРЎвЂљР В°Р Р…Р Р…РЎвЂ“ РЎвЂ РЎвЂ“Р Р…Р С‘ Р Т‘Р В»РЎРЏ РЎРѓР С‘Р СР Р†Р С•Р В»РЎвЂ“Р Р†
    - РЎР‚Р В°РЎвЂ¦РЎС“РЎвЂќ basis% РЎвЂљР В° Р В·Р В°РЎРѓРЎвЂљР С•РЎРѓР С•Р Р†РЎС“РЎвЂќ cooldown + allow/deny + min_price
    - Р Р†РЎвЂ“Р Т‘Р С—РЎР‚Р В°Р Р†Р В»РЎРЏРЎвЂќ Р С”Р С•РЎР‚Р С•РЎвЂљР С”Р Вµ Р С—Р С•Р Р†РЎвЂ“Р Т‘Р С•Р СР В»Р ВµР Р…Р Р…РЎРЏ Р Р† Telegram (Р В°РЎРѓР С‘Р Р…РЎвЂ¦РЎР‚Р С•Р Р…Р Р…Р С•, Р В±Р ВµР В· Р В±Р В»Р С•Р С”РЎС“Р Р†Р В°Р Р…Р Р…РЎРЏ event loop)
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
                token=self._s.telegram.token,
                chat_id=self._s.telegram.chat_id,
                cooldown_s=max(
                    10, min(self._cooldown, 120)
                ),  # Р В»Р С•Р С”Р В°Р В»РЎРЉР Р…Р С‘Р в„– Р В·Р В°Р С—Р С•Р В±РЎвЂ“Р В¶Р Р…Р С‘Р С”
            )

            async def _default_send(text: str) -> None:
                if not text:
                    return
                ok = await asyncio.to_thread(_sender.send, text)
                if not ok:
                    logger.warning(
                        "AlertsSubscriber: TelegramSender.send returned False"
                    )

            self._send_async = _default_send
        else:
            self._send_async = send_async

        # Unsubscribe callbacks
        self._unsubs: list[Callable[[], None]] = []

    # --------------------------- Public API ---------------------------

    def start(self) -> None:
        """Р СџРЎвЂ“Р Т‘Р С—Р С‘РЎРѓРЎС“РЎвЂќР СР С•РЎРѓРЎРЏ Р Р…Р В° Р С—Р С•Р Т‘РЎвЂ“РЎвЂ” Р СРЎС“Р В»РЎРЉРЎвЂљР С‘Р С—Р В»Р ВµР С”РЎРѓР С•РЎР‚Р В°."""
        self.stop()  # Р Р…Р В° Р Р†Р С‘Р С—Р В°Р Т‘Р С•Р С” Р С—Р С•Р Р†РЎвЂљР С•РЎР‚Р Р…Р С•Р С–Р С• Р Р†Р С‘Р С”Р В»Р С‘Р С”РЎС“

        def _on_evt(evt: WsEvent) -> None:
            try:
                self._handle_evt(evt)
            except Exception as e:  # noqa: BLE001
                logger.exception("AlertsSubscriber handler failed: {}", e)

        self._unsubs.append(
            self._mux.subscribe(
                handler=_on_evt, source="SPOT", channel="tickers", symbol="*"
            )
        )
        self._unsubs.append(
            self._mux.subscribe(
                handler=_on_evt, source="LINEAR", channel="tickers", symbol="*"
            )
        )
        logger.info(
            "AlertsSubscriber started: threshold={:.2f}% cooldown={}s allow={} deny={}",
            self._threshold,
            self._cooldown,
            (len(self._allow) or "-"),
            (len(self._deny) or "-"),
        )

    def stop(self) -> None:
        """Р вЂ™РЎвЂ“Р Т‘Р С—Р С‘РЎРѓРЎС“РЎвЂќР СР С•РЎРѓРЎРЏ Р Р†РЎвЂ“Р Т‘ РЎС“РЎРѓРЎвЂ“РЎвЂ¦ Р С—Р С•Р Т‘РЎвЂ“Р в„–."""
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

        # Р С•Р В±РЎвЂЎР С‘РЎРѓР В»Р С‘РЎвЂљР С‘ basis, РЎРЏР С”РЎвЂ°Р С• РЎвЂќ Р С•Р В±Р С‘Р Т‘Р Р†РЎвЂ“ РЎвЂ РЎвЂ“Р Р…Р С‘
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

        # Р СњР В°Р Т‘РЎвЂ“РЎРѓР В»Р В°РЎвЂљР С‘: РЎРЏР С”РЎвЂ°Р С• РЎвЂќ running loop РІР‚вЂќ Р С—Р В»Р В°Р Р…РЎС“РЎвЂќР СР С• Р В·Р В°Р Т‘Р В°РЎвЂЎРЎС“,
        # РЎРЏР С”РЎвЂ°Р С• Р Р…РЎвЂ“ (Р Р…Р В°Р С—РЎР‚Р С‘Р С”Р В»Р В°Р Т‘, unit-РЎвЂљР ВµРЎРѓРЎвЂљ) РІР‚вЂќ Р Р†Р С‘Р С”Р С•Р Р…РЎС“РЎвЂќР СР С• Р С•Р Т‘РЎР‚Р В°Р В·РЎС“ РЎвЂЎР ВµРЎР‚Р ВµР В· asyncio.run(...)
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
