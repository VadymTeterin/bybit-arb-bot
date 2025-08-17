# tests/safety/test_redact.py
from __future__ import annotations

from exchanges.common.redact import redact_headers, redact_json, redact_text


def test_redact_headers_masks_sensitive():
    headers = {
        "X-BAPI-API-KEY": "SECRETKEY123456",
        "X-BAPI-SIGN": "SIGNATURE1234567890",
        "Authorization": "Bearer abc.def.ghi",
        "Content-Type": "application/json",
    }
    out = redact_headers(headers)
    assert out["X-BAPI-API-KEY"] != headers["X-BAPI-API-KEY"]
    assert out["X-BAPI-SIGN"] != headers["X-BAPI-SIGN"]
    assert out["Authorization"] != headers["Authorization"]
    assert out["Content-Type"] == "application/json"


def test_redact_json_recursive():
    payload = {
        "apiKey": "AAAABBBBCCCCDDDD",
        "nested": {"signature": "SGN123", "regular": 1},
        "list": [{"secret": "ZZZ"}, {"ok": "yes"}],
    }
    out = redact_json(payload)
    assert out["apiKey"] != "AAAABBBBCCCCDDDD"
    assert out["nested"]["signature"] != "SGN123"
    assert out["nested"]["regular"] == 1
    assert out["list"][0]["secret"] != "ZZZ"
    assert out["list"][1]["ok"] == "yes"


def test_redact_text_variants():
    t1 = '..."X-BAPI-API-KEY":"SECRET" ...'
    t2 = "api_key=SECRET&foo=bar"
    t3 = "Authorization: Bearer abc.def.ghi"
    r1 = redact_text(t1)
    r2 = redact_text(t2)
    r3 = redact_text(t3)
    assert "SECRET" not in r1
    assert "SECRET" not in r2
    assert "abc.def.ghi" not in r3
