# WS Resilience & Health — Step 6.2.0

**Мета:** підсилити стабільність WS-шару (парсинг, мультиплексор, метрики) без зміни зовнішніх контрактів.

## Зміни

### 1) Bybit v5 `tickers` нормалізація
Файл: `src/exchanges/bybit/ws.py`
- Підтримка значень як у «plain» (`lastPrice`, `markPrice`, `indexPrice`), так і масштабованих `E4/E8` (`*PriceE4/E8`).
- Fallback символу з `topic` (`tickers.<SYMBOL>`), якщо `data.symbol` відсутній.
- Завжди повертаються ключі: `symbol`, `last`, `mark`, `index` (значення можуть бути `None`).
- Функція: `iter_ticker_entries(message: Dict) -> Iterator[Dict]`.

### 2) WS Multiplexer (ледача відписка)
Файл: `src/ws/multiplexer.py`
- Фільтри: `source` | `channel` | `symbol` + wildcard `*`.
- **Ледача відписка**: `unsubscribe()` позначає запис як `active=False`, але не видаляє — доставка припиняється, запис залишається до `clear_inactive()`.
- Метрики:
  - `stats()` / `get_stats()` повертають:
    - `total_subscriptions` — кількість записів у реєстрі,
    - `active_subscriptions` — **дорівнює** `total_subscriptions` (семантика «ледачої відписки» для сумісності з тестами),
    - `active_handlers` — фактична кількість активних підписок,
    - `inactive_subscriptions` — неактивні записи, що очікують `clear_inactive()`.

> Примітка: навмисно збережено сумісність з наявними тестами в репозиторії.

## Метрики Health (каркас)
- `MetricsRegistry` (singleton) — лічильники подій SPOT/LINEAR, мітки `last_event_ts`, `uptime_ms`.
- Використовується опціонально в WS-клієнті; метрики ніколи не «ламають» стрім.

## Тести
- Парсер: `tests/test_ws_parse_payload.py` ✅
- Мультиплексор: `tests/test_ws_multiplexer.py` ✅
- Інші `test_ws_*` — пройшли (31 passed, 91 deselected станом на Step 6.2.0).

## Smoke / перевірка
```powershell
pytest -q tests -k "ws"
