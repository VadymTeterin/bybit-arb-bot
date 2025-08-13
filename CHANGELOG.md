# CHANGELOG

## Фаза 0 — Підготовка середовища
- [2025-08-10 12:55] Створено структуру проєкту згідно з інструкціями.
- [2025-08-10 13:05] Налаштовано віртуальне середовище Python 3.11.
- [2025-08-10 13:15] Встановлено залежності з `requirements.txt`.
- [2025-08-10 13:20] Виконано швидкі sanity-перевірки (`version`, `logtest`, `env`, `healthcheck`).

## Фаза 1 — REST API Bybit
- [2025-08-10 14:20] Додано клас `BybitRest` для роботи з Bybit API.
- [2025-08-10 14:46] Додано команди `bybit:ping` та `bybit:top` (spot/linear).
- [2025-08-10 15:18] Додано команду `basis:scan` з фільтрами по MinVol та threshold.

## Фаза 2 — Telegram алерти
- [2025-08-10 15:50] Додано змінні `TELEGRAM_BOT_TOKEN` та `TG_ALERT_CHAT_ID` у `.env`.
- [2025-08-10 15:58] Перевірено, що конфігурація зчитується через `python -m src.main env`.
- [2025-08-10 16:02] Успішно надіслані тестові повідомлення в Telegram через команду `basis:alert`.

## Фаза 3 — Крок 1: Конфіг для історії/ліквідності
- [2025-08-10] Оновлено `src/infra/config.py`:
  - Увімкнено підтримку вкладених змінних оточення (`env_nested_delimiter="__"`).
  - Додано нові параметри: `min_price`, `db_path`, `top_n_report`.
  - Забезпечено зворотну сумісність зі старими назвами змінних (`TG_BOT_TOKEN`, `BYBIT_API_KEY` тощо).
- [2025-08-10] Оновлено `.env` до вкладеного формату: `TELEGRAM__BOT_TOKEN`, `TELEGRAM__ALERT_CHAT_ID`, `BYBIT__API_KEY`, `BYBIT__API_SECRET`.
- [2025-08-10] Перевірено завантаження конфігу в PowerShell:
  - Значення параметрів збігаються з `.env`.
  - Telegram токен та Bybit ключ зчитуються успішно.

## Фаза 3 — Крок 2: Фільтри ліквідності + репорти
- [2025-08-10] Додано модуль `src/core/filters/liquidity.py`.
- [2025-08-10] Додано модуль `src/core/report.py`.
- [2025-08-10] Додано тести: `tests/test_liquidity_filters.py`, `tests/test_report.py`.
- [2025-08-10] Оновлено `main.py`: команди `report:print`, `report:send`; ініціалізація SQLite.
- [2025-08-10] Перевірено роботу звітів (термінал + Telegram).

## Фаза 3 — Крок 2.1: Цінові пари (price:pair) + тести
- [2025-08-10] Реалізовано команду `price:pair` і тести `tests/test_price_pair.py`.

## Фаза 3 — Крок 3.4: Фільтр глибини стакану (depth filter)
- [2025-08-13] Додано `src/core/filters/depth.py`, оновлено `rest.py`, інтегровано у `selector.py`.
- [2025-08-13] Оновлено конфіг (`src/infra/config.py`, `.env.example`) новими параметрами depth.
- [2025-08-13] Додано тести: `tests/test_depth_filter.py`, `tests/test_selector_with_depth.py`.

## Фаза 4 — Крок 4.1: WS skeleton
- [2025-08-13] Додано `src/exchanges/bybit/ws.py` (автоперепідключення) та `src/core/cache.py`.
- [2025-08-13] Додано базові тести: `tests/test_backoff.py`, `tests/test_cache_basic.py`.
- [2025-08-13] Оновлено `.env.example`, `src/infra/config.py`, `src/main.py` — команда `ws:run` (скелет).
- [2025-08-13] Всі тести пройшли успішно.

## Фаза 4 — Крок 4.2: WS parsing + cache update
- [2025-08-13] Розведено два WS потоки: `SPOT` і `LINEAR` (окремі URL та топіки).
- [2025-08-13] Додано парсинг `tickers.*` з нормалізацією `E4/E8 → float`.
- [2025-08-13] `ws:run` запускає обидва клієнти паралельно; оновлює `QuoteCache` (spot/linear_mark).
- [2025-08-13] Додано тести `tests/test_ws_parse_payload.py`.
- [2025-08-13] Оновлено `.env.example`, `src/infra/config.py`, `src/exchanges/bybit/ws.py`, `src/main.py`.
