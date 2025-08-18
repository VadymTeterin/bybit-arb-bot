# Step-5.8.3 — BYBIT WS → Multiplexer Integration

> **Goal:** Normalize all Bybit v5 WS messages to a single internal format and route them through the WS Multiplexer.

## Files added in this step
- `src/ws/normalizers/bybit_v5.py` — stateless normalizer to `{exchange, channel, symbol, event, ts_ms, data}`.
- `src/ws/reconnect.py` — reconnect policy + heartbeat helpers (exchange-agnostic).
- Tests: `tests/test_ws_normalizer_bybit_v5.py`, `tests/test_ws_reconnect_policy.py`.

## Wiring into your WS bridge (example)

> **Note:** adapt to your actual bridge. Keep changes minimal and covered by tests.

```python
# Example (pseudo) — inside your Bybit WS on_message callback
from src.ws.normalizers.bybit_v5 import normalize
from src.ws.multiplexer import publish  # assuming you expose a publish(event_dict)

def on_message(raw_msg: dict) -> None:
    evt = normalize(raw_msg)
    publish(evt)  # routes by channel/symbol/event
