## [0.4.3] - 2025-08-13
### Added
- CLI команда `alerts:preview` для перегляду форматованого повідомлення без відправки в Telegram.

# CHANGELOG

## [0.4.3] - 2025-08-13 ### Added
- CLI команда `alerts:preview` для перегляду форматованого повідомлення без відправки в Telegram.
- Параметр `--min-vol` для команди `alerts:preview` (зручність тестування і налаштування заголовка).


## 0.4.2 – Real-time Alerts
- [2025-08-13] Додано модуль `src/core/alerts.py` для генерації та обробки сигналів у реальному часі.
- [2025-08-13] Додано модуль `src/telegram/formatters.py` для форматування повідомлень у Telegram.
- [2025-08-13] Інтегровано real-time логіку у `main.py` (гілка `step-4.4-realtime-alerts`).
- [2025-08-13] Створено тести для core/alerts та telegram/formatters.
- [2025-08-13] Оновлено `.env.example` та додано нові параметри конфігурації.
- [2025-08-13] Усі тести проходять.

## Етап 0 – Ініціалізація проєкту
- [2025-08-10 12:55] Створено базову структуру папок і залежності.
- [2025-08-10 13:05] Налаштовано використання Python 3.11.
- [2025-08-10 13:15] Додано залежності в `requirements.txt`.
- [2025-08-10 13:20] Додано sanity-команди (`version`, `logtest`, `env`, `healthcheck`).

## Етап 1 – REST API Bybit
- [2025-08-10 14:20] Створено клас `BybitRest` для роботи з Bybit API.
- [2025-08-10 14:46] Додано команди `bybit:ping` та `bybit:top` (spot/linear).
- [2025-08-10 15:18] Додано команду `basis:scan` з фільтрацією за MinVol та threshold.

## Етап 2 – Telegram інтеграція
- [2025-08-10 15:50] Додано змінні `TELEGRAM_BOT_TOKEN` та `TG_ALERT_CHAT_ID` у `.env`.
- [2025-08-10 15:58] Перевірено, що конфігурація відображається через `python -m src.main env`.
- [2025-08-10 16:02] Додано відправку звіту у Telegram через команду `basis:alert`.

## Етап 3 – Частина 1: Фільтри та репорти
- [2025-08-10] Оновлено `src/infra/config.py`:
  - Додано підтримку вкладених змінних середовища (`env_nested_delimiter="__"`).
  - Додано ключі конфігурації: `min_price`, `db_path`, `top_n_report`.
  - Оновлено обробку секретів (`TG_BOT_TOKEN`, `BYBIT_API_KEY` тощо).
- [2025-08-10] Оновлено `.env` з прикладами для: `TELEGRAM__BOT_TOKEN`, `TELEGRAM__ALERT_CHAT_ID`, `BYBIT__API_KEY`, `BYBIT__API_SECRET`.
- [2025-08-10] Додано інструкції для PowerShell:
  - Додавання секретів у `.env`.
  - Тест відправки повідомлень у Telegram.

## Етап 3 – Частина 2: Ліквідність + репорти
- [2025-08-10] Створено модуль `src/core/filters/liquidity.py`.
- [2025-08-10] Створено модуль `src/core/report.py`.
- [2025-08-10] Додано тести: `tests/test_liquidity_filters.py`, `tests/test_report.py`.
- [2025-08-10] Оновлено `main.py`: команди `report:print`, `report:send`; підключено SQLite.
- [2025-08-10] Додано генерацію звітів (консоль + Telegram).

## Етап 3 – Частина 2.1: Перевірка ціни (price:pair) + тести
- [2025-08-10] Додано команду `price:pair` і тести `tests/test_price_pair.py`.

## Етап 3 – Частина 3.4: Фільтр глибини (depth filter)
- [2025-08-13] Створено `src/core/filters/depth.py`, додано REST-запити, інтегровано у `selector.py`.
- [2025-08-13] Оновлено конфігурацію (`src/infra/config.py`, `.env.example`) з параметрами depth.
- [2025-08-13] Додано тести: `tests/test_depth_filter.py`, `tests/test_selector_with_depth.py`.

## Етап 4 – Частина 4.1: WS skeleton
- [2025-08-13] Створено `src/exchanges/bybit/ws.py` (асинхронний клієнт) з підтримкою `src/core/cache.py`.
- [2025-08-13] Додано тести: `tests/test_backoff.py`, `tests/test_cache_basic.py`.
- [2025-08-13] Оновлено `.env.example`, `src/infra/config.py`, `src/main.py` з командою `ws:run` (skeleton).
- [2025-08-13] WS клієнт отримує дані.

## Етап 4 – Частина 4.2: WS parsing + cache update
- [2025-08-13] Додано обробку WS каналів: `SPOT` і `LINEAR`.
- [2025-08-13] Парсинг `tickers.*` з конвертацією E4/E8 у float.
- [2025-08-13] Оновлено `ws:run` для оновлення кешу котирувань; збереження `spot` та `linear_mark`.
- [2025-08-13] Додано тести: `tests/test_ws_parse_payload.py`.
- [2025-08-13] Оновлено `.env.example`, `src/infra/config.py`, `src/exchanges/bybit/ws.py`, `src/main.py`.

## Етап 4 – Частина 4.3: Real-time basis + фільтри
- [2025-08-13] Додано розрахунок basis% і відбір кандидатів для алертів (spot/linear).
- [2025-08-13] Додано оновлення 24h turnover через REST для фільтра `min_vol_24h_usd`.
- [2025-08-13] Інтегровано параметри у команду з threshold, min_price, min_vol_24h_usd.
- [2025-08-13] Оновлено `src/main.py`, `src/core/cache.py`, `src/infra/config.py`.
- [2025-08-13] Додано тести: `tests/test_realtime_basis.py`.
