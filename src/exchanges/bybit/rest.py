# src/exchanges/bybit/rest.py
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, List, NotRequired, Optional, TypedDict

import requests

__all__ = ["BybitRest", "SymbolMeta"]


class SymbolMeta(TypedDict):
    """Мета-інформація по інструменту.

    base/quote — обов’язкові, інші поля можуть додаватись кодом вище по стеку.
    """

    base: str
    quote: str
    price: NotRequired[float]
    turnover_usd: NotRequired[float]


class BybitRest:
    """
    Легкий REST-клієнт Bybit з чіткими типами, достатній для потреб типізації.

    Покриті методи:
      - get_spot_map() -> dict[symbol, {"base": str, "quote": str}]
      - get_linear_map() -> dict[symbol, {"base": str, "quote": str}]
      - get_orderbook_spot(symbol, *, limit|depth) -> dict
      - get_orderbook_linear(symbol, *, limit|depth) -> dict
      - get_prev_funding(symbol) -> dict | None
      - get_server_time() -> dict[str, Any]  (має ключі timeSecond/timeNow)
      - get_tickers(category="spot"/"linear", symbols=None) -> list[dict]
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: str = "https://api.bybit.com",
        *,
        timeout: float = 10.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.base_url: str = base_url.rstrip("/")
        self.session: requests.Session = session or requests.Session()
        self.timeout: float = timeout
        self.api_key: Optional[str] = api_key
        self.api_secret: Optional[str] = api_secret
        self.log: logging.Logger = logger or logging.getLogger(__name__)

        self.session.headers.update(
            {"User-Agent": "bybit-arb-bot/0.0 (rest.py typesafe client)"}
        )

    # -------------------------- внутрішні утиліти --------------------------

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params or {}, timeout=self.timeout)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()  # type: ignore[assignment]
        # Bybit v5: retCode == 0 — ок
        if isinstance(data, dict) and data.get("retCode") not in (0, "0", None):
            raise requests.HTTPError(
                f"Bybit API error retCode={data.get('retCode')} msg={data.get('retMsg')}",
                response=resp,
            )
        return data

    def _get_paged(
        self,
        path: str,
        params: Dict[str, Any] | None = None,
        *,
        item_path: Iterable[str] = ("result", "list"),
        cursor_param: str = "cursor",
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        cursor: str | None = None

        while True:
            q = dict(params or {})
            if cursor:
                q[cursor_param] = cursor
            data = self._get(path, q)

            node: Any = data
            for k in item_path:
                if not isinstance(node, dict):
                    node = None
                    break
                node = node.get(k)

            if not isinstance(node, list):
                break

            for it in node:
                if isinstance(it, dict):
                    items.append(it)

            cursor = None
            result = data.get("result")
            if isinstance(result, dict):
                c = result.get("nextPageCursor") or result.get("cursor")
                if isinstance(c, str) and c:
                    cursor = c

            if not cursor:
                break

        return items

    # -------------------------- публічні методи ---------------------------

    def get_spot_map(self) -> Dict[str, SymbolMeta]:
        """Карта SPOT-інструментів: symbol -> {"base": baseCoin, "quote": quoteCoin}"""
        params = {"category": "spot"}
        data = self._get("/v5/market/instruments-info", params=params)

        symbols: Dict[str, SymbolMeta] = {}
        result = data.get("result")
        if isinstance(result, dict):
            lst = result.get("list")
            if isinstance(lst, list):
                for row in lst:
                    if not isinstance(row, dict):
                        continue
                    symbol = row.get("symbol")
                    base = row.get("baseCoin")
                    quote = row.get("quoteCoin")
                    if (
                        isinstance(symbol, str)
                        and isinstance(base, str)
                        and isinstance(quote, str)
                    ):
                        symbols[symbol] = {"base": base, "quote": quote}
        return symbols

    def get_linear_map(self) -> Dict[str, SymbolMeta]:
        """Карта USDT-перпатів (linear): symbol -> {"base": baseCoin, "quote": quoteCoin}"""
        params = {"category": "linear"}
        data = self._get("/v5/market/instruments-info", params=params)

        symbols: Dict[str, SymbolMeta] = {}
        result = data.get("result")
        if isinstance(result, dict):
            lst = result.get("list")
            if isinstance(lst, list):
                for row in lst:
                    if not isinstance(row, dict):
                        continue
                    symbol = row.get("symbol")
                    base = row.get("baseCoin")
                    quote = row.get("quoteCoin")
                    if (
                        isinstance(symbol, str)
                        and isinstance(base, str)
                        and isinstance(quote, str)
                    ):
                        symbols[symbol] = {"base": base, "quote": quote}
        return symbols

    def get_orderbook_spot(
        self,
        symbol: str,
        *,
        limit: int | None = None,
        depth: int | None = None,
    ) -> Dict[str, Any]:
        """Orderbook для SPOT. Приймаємо як `limit=`, так і `depth=`."""
        final = limit if limit is not None else (depth if depth is not None else 50)
        final = max(1, min(int(final), 200))  # Bybit дозволяє до 200
        params = {"category": "spot", "symbol": symbol, "limit": final}
        return self._get("/v5/market/orderbook", params=params)

    def get_orderbook_linear(
        self,
        symbol: str,
        *,
        limit: int | None = None,
        depth: int | None = None,
    ) -> Dict[str, Any]:
        """Orderbook для USDT-perp (linear). Приймаємо як `limit=`, так і `depth=`."""
        final = limit if limit is not None else (depth if depth is not None else 200)
        final = max(1, min(int(final), 500))  # зазвичай до 500
        params = {"category": "linear", "symbol": symbol, "limit": final}
        return self._get("/v5/market/orderbook", params=params)

    def get_prev_funding(self, symbol: str) -> Dict[str, Any] | None:
        """
        Повертає перший елемент з /v5/market/funding/history для linear-контракту,
        або None, якщо немає даних. Очікується подальше використання через .get("fundingRate").
        """
        params = {"category": "linear", "symbol": symbol}
        data = self._get("/v5/market/funding/history", params=params)

        result = data.get("result")
        if not isinstance(result, dict):
            return None

        lst = result.get("list")
        if not isinstance(lst, list) or not lst:
            return None

        row = lst[0]
        return row if isinstance(row, dict) else None

    def get_server_time(self) -> Dict[str, Any]:
        """
        Серверний час Bybit як dict з ключами, які далі очікуються в коді:
        - timeSecond: int
        - timeNow: str
        Якщо API не повернув ці поля, формуємо їх локально.
        """
        now_sec = int(time.time())
        try:
            data = self._get("/v5/market/time")
            result = data.get("result")
            if isinstance(result, dict):
                out: Dict[str, Any] = {}
                # нормалізуємо до потрібних ключів
                if "timeSecond" in result:
                    out["timeSecond"] = int(float(result["timeSecond"]))
                elif "time" in result:
                    out["timeSecond"] = int(float(result["time"]))
                elif "timeNow" in result:
                    out["timeSecond"] = int(float(result["timeNow"]))
                else:
                    out["timeSecond"] = now_sec

                out["timeNow"] = str(out["timeSecond"])
                return out
        except Exception as exc:
            self.log.debug("get_server_time fallback due to: %s", exc)

        return {"timeSecond": now_sec, "timeNow": str(now_sec)}

    def get_tickers(
        self,
        category: str = "linear",
        symbols: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Обгортка над /v5/market/tickers, яка **повертає список** тікерів.
        Це узгоджується з подальшими викликами: .sort(), зрізи тощо.
        """

        def _one(sym: Optional[str]) -> List[Dict[str, Any]]:
            p = {"category": category}
            if sym:
                p["symbol"] = sym
            data = self._get("/v5/market/tickers", p)
            result = data.get("result")
            if isinstance(result, dict) and isinstance(result.get("list"), list):
                return [it for it in result["list"] if isinstance(it, dict)]
            return []

        if not symbols:
            return _one(None)

        out: List[Dict[str, Any]] = []
        for s in symbols:
            out.extend(_one(s))
        return out
