# tests/test_ws_parse_payload.py
from src.exchanges.bybit.ws import iter_ticker_entries


def test_parse_spot_tickers_last_price():
    msg = {
        "topic": "tickers.BTCUSDT",
        "type": "snapshot",
        "data": {
            "symbol": "BTCUSDT",
            "lastPrice": "65000.1",
        },
    }
    rows = list(iter_ticker_entries(msg))
    assert rows and rows[0]["symbol"] == "BTCUSDT"
    assert abs(rows[0]["last"] - 65000.1) < 1e-9
    assert rows[0]["mark"] is None


def test_parse_linear_tickers_mark_price_e4():
    # Імітація linear payload із E4 масштабом для markPrice
    msg = {
        "topic": "tickers.ETHUSDT",
        "type": "delta",
        "data": [
            {
                "symbol": "ETHUSDT",
                "markPriceE4": 345678901,  # 34567.8901
                "lastPriceE4": 345600000,  # 34560.0000
            }
        ],
    }
    rows = list(iter_ticker_entries(msg))
    assert rows and rows[0]["symbol"] == "ETHUSDT"
    assert abs(rows[0]["mark"] - 34567.8901) < 1e-9
    assert abs(rows[0]["last"] - 34560.0) < 1e-9


def test_parse_without_symbol_in_data_uses_topic_suffix():
    msg = {
        "topic": "tickers.XRPUSDT",
        "data": [{"lastPriceE8": "5890000000"}],  # 58.9
    }
    rows = list(iter_ticker_entries(msg))
    assert rows and rows[0]["symbol"] == "XRPUSDT"
    assert abs(rows[0]["last"] - 58.9) < 1e-9
