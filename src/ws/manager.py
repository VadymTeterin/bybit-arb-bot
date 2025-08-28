# src/ws/manager.py
# English-only comments per project rules.
from __future__ import annotations

import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class WSManagerSnapshot:
    ts: float
    topics: list[str]
    reconnects_total: int
    last_connect_ts: float | None
    last_disconnect_ts: float | None
    last_msg_ts: float | None
    last_heartbeat_ts: float | None

    def last_msg_age_ms(self) -> int | None:
        if self.last_msg_ts is None:
            return None
        return int((self.ts - self.last_msg_ts) * 1000)

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "topics": list(self.topics),
            "reconnects_total": self.reconnects_total,
            "last_connect_ts": self.last_connect_ts,
            "last_disconnect_ts": self.last_disconnect_ts,
            "last_msg_ts": self.last_msg_ts,
            "last_heartbeat_ts": self.last_heartbeat_ts,
            "last_msg_age_ms": self.last_msg_age_ms(),
        }


@dataclass
class WSManager:
    """
    Pure-Python WS manager:
      - stores current topic set
      - resubscribe() returns topics to replay after reconnect
      - tracks reconnects and heartbeats
      - no I/O; call on_connect/on_message/on_disconnect from your WS loop
    """

    topics: set[str] = field(default_factory=set)
    reconnects_total: int = 0
    last_connect_ts: float | None = None
    last_disconnect_ts: float | None = None
    last_msg_ts: float | None = None
    last_heartbeat_ts: float | None = None

    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    # --- topics
    def set_topics(self, topics: Iterable[str]) -> None:
        with self._lock:
            self.topics = {str(t).strip() for t in topics if str(t).strip()}

    def add_topics(self, topics: Iterable[str]) -> None:
        with self._lock:
            for t in topics:
                t = str(t).strip()
                if t:
                    self.topics.add(t)

    def remove_topics(self, topics: Iterable[str]) -> None:
        with self._lock:
            for t in topics:
                self.topics.discard(str(t).strip())

    def resubscribe_args(self) -> list[str]:
        with self._lock:
            return sorted(self.topics)

    # --- lifecycle hooks
    def on_connect(self) -> list[str]:
        with self._lock:
            self.last_connect_ts = time.time()
            # after (re)connect we want to replay all current topics
            return sorted(self.topics)

    def on_disconnect(self, *_reason) -> None:
        with self._lock:
            self.reconnects_total += 1
            self.last_disconnect_ts = time.time()

    def on_message(self, payload: dict | None) -> None:
        now = time.time()
        with self._lock:
            self.last_msg_ts = now
            if isinstance(payload, dict):
                op = str(payload.get("op", "")).lower()
                ev = str(payload.get("event", "")).lower()
                # update heartbeat timestamp on pongs/keepalives
                if op == "pong" or ev == "pong":
                    self.last_heartbeat_ts = now

    # --- views
    def snapshot(self) -> WSManagerSnapshot:
        with self._lock:
            return WSManagerSnapshot(
                ts=time.time(),
                topics=sorted(self.topics),
                reconnects_total=self.reconnects_total,
                last_connect_ts=self.last_connect_ts,
                last_disconnect_ts=self.last_disconnect_ts,
                last_msg_ts=self.last_msg_ts,
                last_heartbeat_ts=self.last_heartbeat_ts,
            )
