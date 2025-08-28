# exchanges/bybit/ws_manager.py
from __future__ import annotations

try:
    import websockets  # type: ignore
except Exception:  # noqa: BLE001
    websockets = None  # Легка залежність, додамо при наповненні


class BybitWebSocketManager:
    def __init__(self, ws_url: str):
        if websockets is None:
            raise ImportError("websockets не встановлено. Додай пакет 'websockets' або 'aiohttp'.")
        self.ws_url = ws_url

    async def connect(self) -> None:
        # TODO: підписки, авторизація, ресаби, gap-detect
        pass

    async def close(self) -> None:
        pass
