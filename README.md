# Bybit Arbitrage Bot

## Опис
Telegram-бот для моніторингу різниці між цінами на спотовому та ф’ючерсному ринках Bybit у режимі реального часу.

## Функціонал
- Підключення до Bybit REST API та WebSocket API v5.
- Обчислення basis % (різниці між spot та futures).
- Відбір топ-3 монет за заданим порогом.
- Фільтри ліквідності.
- Надсилання алертів у Telegram.
- Збереження історії сигналів у SQLite.
- **Експорт сигналів у CSV**.

## Встановлення
```powershell
# Клонування репозиторію
git clone https://github.com/<your-repo>.git
cd bybit-arb-bot

# Створення та активація віртуального середовища
python -m venv .venv
.\.venv\Scripts\activate

# Встановлення залежностей
pip install -r requirements.txt
```

## Налаштування
Створіть файл `.env` на основі `.env.example` і заповніть поля:
```env
BYBIT_API_KEY=
BYBIT_API_SECRET=
TG_BOT_TOKEN=
TG_CHAT_ID=
ALERT_THRESHOLD_PCT=1.0
ALERT_COOLDOWN_SEC=300
DB_PATH=data/signals.db
```

## Приклади запуску
### Експорт у CSV
```powershell
# 1) Останні 24 години у локальну папку exports/ з іменем за замовчуванням
python .\scripts\export_signals.py

# 2) Ті самі 24 години, але з локалізацією часу під Київ (UTC+3 влітку)
python .\scripts\export_signals.py --tz Europe/Kyiv

# 3) Задати чіткий інтервал (UTC) і файл призначення
python .\scripts\export_signals.py --since 2025-08-10T00:00:00 --until 2025-08-14T23:59:59 --out .\exports\signals_aug10-14.csv

# 4) Лише 100 останніх рядків
python .\scripts\export_signals.py --limit 100

# 5) Ротація: зберігати лише 14 останніх CSV із префіксом "signals_*.csv"
python .\scripts\export_signals.py --keep 14
```

**Параметри скрипта `export_signals.py`:**
- `--last-hours N` — кількість годин для вибірки (за замовчуванням 24).
- `--since` / `--until` — початкова та кінцева дата-час у форматі ISO (UTC).
- `--tz` — назва таймзони для локалізації часу.
- `--limit N` — обмеження кількості рядків.
- `--keep N` — ротація: залишити лише N останніх файлів з префіксом `signals_`.
- `--out PATH` — шлях до CSV для збереження.

## Тести
```powershell
pytest -q
```

## Ліцензія
MIT
