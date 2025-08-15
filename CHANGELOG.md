# CHANGELOG — Step 5.8 (WS Multiplexer)

- Added `WSMultiplexer` with wildcard subscriptions and thread-safety.
- Introduced `bridge.publish_bybit_ticker` to normalize Bybit ticker messages to `WsEvent`.
- Implemented `AlertsSubscriber` with allow/deny, cooldown and Telegram async bridge.
- Selector improvements: depth filter compatibility and cooldown logic.
- CLI glue for RT-mode and preview utilities.
