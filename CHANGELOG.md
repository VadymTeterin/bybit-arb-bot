# Changelog

## [Фаза 0] - Початок роботи
### Додано
- Ініційовано репозиторій `bybit-arb-bot`
- Створено та активовано віртуальне середовище `.venv`
- Встановлено основні залежності (aiogram, aiohttp, websockets, pandas, pydantic, loguru, apscheduler, python-dotenv, httpx, pytest, ruff, black, isort, mypy)
- Налаштовано базову структуру проекту: `src/infra`, `src/main.py`
- Виконано швидкі перевірки (sanity checks) інструментами:
  - `ruff` — статичний аналіз коду
  - `black` — перевірка форматування
  - `isort` — перевірка імпортів
  - `pytest` — тестовий запуск тестів

### Результат
- [2025-08-10 13:10] Проект успішно підготовлено до розробки
- [2025-08-10 13:10] Створено `.env.example` з шаблоном налаштувань

---

## [Фаза 1] - Перевірка середовища та CLI
### Додано
- Реалізовано модуль `logging` з функцією `setup_logging`
- Додано читання конфігурації з `.env` через `pydantic` та `pydantic-settings`
- Створено CLI-команди:
  - `version` — перевірка версії бота
  - `env` — вивід поточних змінних середовища
  - `logtest` — тест усіх рівнів логування (DEBUG, INFO, WARNING, ERROR, SUCCESS)
  - `healthcheck` — перевірка працездатності середовища
- Налаштовано вивід логів у консоль та файл `./logs/app.log`

### Результат
- [2025-08-10 13:19] `python -m src.main version` → OK
- [2025-08-10 13:21] `python -m src.main env` → OK
- [2025-08-10 13:20] `python -m src.main logtest` → OK
- [2025-08-10 13:22] `python -m src.main healthcheck` → OK
- [2025-08-10 13:22] Середовище готове до підключення Bybit REST API
