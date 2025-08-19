# tests/bybit/test_auth_sign.py
from __future__ import annotations

import hmac
from hashlib import sha256

from exchanges.bybit.auth import canonical_json, canonical_query, sign_v5


def test_canonical_query_and_sign_get():
    api_key = "mykey"
    api_secret = "mysecret"
    recv = 5000
    ts = "1700000000000"
    params = {"symbol": "BTCUSDT", "category": "spot"}
    body_str = canonical_query(params)
    assert body_str == "category=spot&symbol=BTCUSDT"  # алфавітне сортування
    # очікуваний підпис за формулою
    prehash = f"{ts}{api_key}{recv}{body_str}"
    expected = hmac.new(api_secret.encode(), prehash.encode(), sha256).hexdigest()
    assert sign_v5(api_key, api_secret, recv, ts, body_str) == expected


def test_canonical_json_and_sign_post():
    api_key = "mykey"
    api_secret = "mysecret"
    recv = 5000
    ts = "1700000000000"
    body = {"category": "spot", "symbol": "BTCUSDT", "qty": "1"}
    body_str = canonical_json(body)
    assert body_str == '{"category":"spot","symbol":"BTCUSDT","qty":"1"}'
    prehash = f"{ts}{api_key}{recv}{body_str}"
    expected = hmac.new(api_secret.encode(), prehash.encode(), sha256).hexdigest()
    assert sign_v5(api_key, api_secret, recv, ts, body_str) == expected
