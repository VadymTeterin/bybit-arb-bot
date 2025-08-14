# CHANGELOG

## [0.4.4] - 2025-08-14
### Added
- REST: `BybitRest.get_prev_funding(symbol)` отримує останній funding через `/v5/market/funding/history` (limit=1) та рахує `next_funding_time` на основі `fundingInterval` з `/v5/market/instruments-info`.
- Форматування: `format_signal(...)` тепер опційно показує рядки `Funding (prev)` і `Next funding`.

### Notes
- Інтеграція funding у CLI/WS-алерти робитиметься окремим кроком (5.3).

## [0.4.3] - 2025-08-13
### Added
- CLI команда `alerts:preview` для перегляду форматованого повідомлення без відправки в Telegram.

# CHANGELOG

## [0.4.3] - 2025-08-13 ### Added
- CLI команда `alerts:preview` для перегляду форматованого повідомлення без відправки в Telegram.
- Параметр `--min-vol` для команди `alerts:preview`.

## 0.4.2 – Real-time Alerts
- [2025-08-13] Додано модуль `src/core/alerts.py` для генерації та обробки сигналів у реальному часі.
- [2025-08-13] Додано модуль `src/telegram/formatters.py` для форматування повідомлень у Telegram.
- [2025-08-13] Інтегровано real-time логіку у `main.py`.
- [2025-08-13] Тести для core/alerts та telegram/formatters.
- [2025-08-13] Оновлено `.env.example` та додано нові параметри конфігурації.

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
