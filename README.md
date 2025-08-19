# BYBIT Arbitrage Bot (Windows)

> Telegram‑бот для моніторингу базису між **Spot** та **Futures** на Bybit із алертами в Telegram.
> Платформа розробки: **Windows 11**. Команди наводимо для **PowerShell** та VS Code **«Термінал»**.

## Основне
- Скани різниці **spot vs futures** (basis %) і вибір **топ‑3** пар вище порогу.
- Фільтри ліквідності: 24h обсяг, мінімальна ціна, глибина.
- Алерти в Telegram (тротлінг/cooldown).
- Історія сигналів у SQLite/Parquet.
- **WebSocket (v5)**: стрім цін + нормалізація + лічильники подій (SPOT/LINEAR).
- **Windows‑лаунчер:** `launcher_export.cmd` (див. нижче).

## Вимоги
- Python **3.11+** (Windows)
- Інтернет з’єднання
- PowerShell або VS Code «Термінал»

## Швидкий старт (PowerShell)
> ⚠️ Секрети в `.env` не показуйте на скрінах.

```powershell
# Активувати venv
& .\.venv\Scripts\Activate.ps1

# Встановити залежності
pip install -r requirements.txt

# Скопіювати приклад змінних оточення
Copy-Item .env.example .env

# Заповнити .env (BYBIT_API_KEY, BYBIT_API_SECRET, TG_BOT_TOKEN, TG_CHAT_ID, ...)

# Перевірити середовище
python -m src.main env

# Прогнати тести
pytest -q
```

## .env (приклад полів)
```
BYBIT_API_KEY=
BYBIT_API_SECRET=
TG_BOT_TOKEN=
TG_CHAT_ID=
ALERT_THRESHOLD_PCT=1.0
ALERT_COOLDOWN_SEC=300
MIN_VOL_24H_USD=10000000
MIN_PRICE=0.001
WS_ENABLED=True
WS_PUBLIC_URL_LINEAR=wss://stream.bybit.com/v5/public/linear
WS_PUBLIC_URL_SPOT=wss://stream.bybit.com/v5/public/spot
WS_SUB_TOPICS_LINEAR=tickers.BTCUSDT,tickers.ETHUSDT
WS_SUB_TOPICS_SPOT=tickers.BTCUSDT,tickers.ETHUSDT
WS_RECONNECT_MAX_SEC=30
```

## Запуск (CLI)
Всі команди виконуються так: `python -m src.main <команда> [аргументи]`

```powershell
# Довідка
python -m src.main -h

# Перевірка ENV
python -m src.main env

# Пошук топ-3 сигналів і вивід у консоль
python -m src.main basis:alert --limit 3 --threshold 1.0 --min-vol 10000000

# Звіт за годину
python -m src.main report:print --hours 1 --limit 10

# WebSocket (стрім/нормалізація)
python -m src.main ws:run

# NEW: прев’ю алерта без відправки у Telegram (Step 5.8.3)
python -m src.main alerts:preview --symbol BTCUSDT --spot 50000 --mark 50500
python -m src.main alerts:preview --symbol ETHUSDT --spot 2500 --mark 2525 --vol 12000000 --threshold 0.5
```

## Windows‑лаунчер `launcher_export.cmd`
Файл у корені репозиторію. Призначення:
- Гарантує перехід у директорію проекту: `cd /d %~dp0`.
- Створює `logs\` якщо її нема: `if not exist logs mkdir logs`.
- Віддає пріоритет `.venv\Scripts\python.exe`.
- Містить явне посилання на `scripts\export_signals.py`.
- **Без аргументів** запускає експорт із логуванням у `logs\export.log`:
  ```
  %PY_EXE% "%EXPORT_SCRIPT%" >> logs\export.log 2>&1
  ```
- **З аргументами** прокидає їх у `python -m src.main`.

Приклади:
```powershell
# Прев’ю алерта (через лаунчер)
.\launcher_export.cmd alerts:preview --symbol BTCUSDT --spot 50000 --mark 50500

# Без аргументів (створить logs\ та виконає export_signals.py; лог -> logs\export.log)
.\launcher_export.cmd
```

## Якість коду та тести
```powershell
ruff check .
ruff format .
isort .
black .
pytest -q
```

## CI
- GitHub Actions: тести, лінтинг, форматування.
- Додатковий workflow **Verify Windows Launcher** перевіряє наявність і структуру `launcher_export.cmd` (див. `.github/workflows/verify-launcher.yml`).

## Структура (скорочено)
```
src/
  main.py
  ws/
    backoff.py        # Step 5.8.4 (бекоф)
    health.py         # Step 5.8.4 (метрики WS)
  telegram/
    bot.py
    formatters.py
scripts/
  export_signals.py
  ws_health_cli.py    # тимчасовий health‑CLI
tests/
  test_backoff.py     # Step 5.8.4
  test_ws_health.py   # Step 5.8.4
  test_launcher_cmd.py
launcher_export.cmd
.env.example
README.md
CHANGELOG.md
```
