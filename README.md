# Bybit Arbitrage Bot

> Реальний час • Windows • Telegram Alerts • Без індикаторів (Price Action / Liquidity Filters)

## Огляд
UA: Телеграм-бот відстежує спред (basis %) між SPOT та ф’ючерсами (USDT‑перпетуали) на Bybit. Підтримано режим реального часу через WebSocket, фільтри ліквідності, попередній перегляд алертів і експорт сигналів у CSV.
EN: Telegram bot that tracks the spread (basis %) between SPOT and USDT‑perpetual futures on Bybit. Real‑time via WebSocket, liquidity filters, alert preview, and CSV export included.

---

## Можливості (коротко)
- Basis % (SPOT vs LINEAR) у real‑time та single‑shot скануванні
- Фільтри ліквідності: обсяг (24h), глибина ринку
- Throttling алертів, Telegram‑повідомлення, попередній перегляд форматування
- SQLite збереження сигналів, звіти, експорт у CSV
- **WS Multiplexer (Крок 5.6)** — модуль маршрутизації подій із `*`‑wildcard (не змінює чинний 5.5)
- Легка CLI‑утиліта з командами для діагностики/запуску

> Платформа розробки: **Windows**. Інструкції для **PowerShell** та VS Code **“Термінал”**.

---

## Встановлення (Windows PowerShell / VS Code “Термінал”)
```powershell
git clone https://github.com/<your-repo>/bybit-arb-bot.git
cd bybit-arb-bot

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Налаштування середовища
Скопіюйте `.env.example` → `.env` і заповніть значення:
```env
BYBIT__API_KEY=
BYBIT__API_SECRET=
TELEGRAM__TOKEN=
TELEGRAM__CHAT_ID=
ALERT_THRESHOLD_PCT=1.0
ALERT_COOLDOWN_SEC=300
DB_PATH=data/signals.db
```

#### Автозавантаження `.env`
З **Кроку 5.8** `src/infra/config.py` автоматично викликає `autoload_env()` (stdlib), тож `.env` підхоплюється без `python-dotenv` та без PowerShell‑хелперів. Якщо потрібно, можна вказати альтернативний шлях файлу через `ENV_FILE`.

#### Back‑compat містки (на перехідний період)
Якщо у вашому середовищі залишилися старі назви ключів — вони автоматично мапляться у nested‑конфіг:

| Старий ключ                                 | Новий ключ (nested)                    |
|---------------------------------------------|----------------------------------------|
| `TELEGRAM_TOKEN`, `TELEGRAM_BOT_TOKEN`      | `TELEGRAM__TOKEN` → `telegram.token`   |
| `TELEGRAM_CHAT_ID`, `TG_CHAT_ID`, `TELEGRAM_ALERT_CHAT_ID` | `TELEGRAM__CHAT_ID` → `telegram.chat_id` |

> Під час друку `python -m src.main env` ці значення відображаються у секції `telegram`.

---

## Запуск: основні сценарії
### Одноразовий скан спредів (REST)
```powershell
python -m src.main basis:scan --threshold 0.5 --min-vol 10000000 --limit 10
```

### Сигнали у консоль із фільтрами
```powershell
python -m src.main basis:alert --threshold 0.8 --min-vol 8000000 --limit 3
```

### Попередній перегляд форматування алерту
```powershell
python -m src.main alerts:preview --symbol BTCUSDT --spot 50000 --mark 50500 --min-vol 1000000 --threshold 0.5
```

### Відправка тестового повідомлення у Telegram
```powershell
python -m src.main tg:send --text "Hello from BybitArbBot"
```

### Запуск у реальному часі (WebSocket‑ядро)
```powershell
python -m src.main ws:run
```

> Під час роботи `ws:run` обчислення basis% відбувається на льоту з кешу. Задіяні тротлінг і захист від шуму.

---

## Експорт сигналів у CSV (Крок 5.4)
```powershell
python .\scripts\export_signals.py                 # останні 24 години
python .\scripts\export_signals.py --tz Europe/Kyiv
python .\scripts\export_signals.py --since 2025-08-10T00:00:00 --until 2025-08-14T23:59:59 --out .\exports\signals_aug10-14.csv
python .\scripts\export_signals.py --limit 100
python .\scripts\export_signals.py --keep 14       # ротація CSV
```

### Планувальник завдань Windows
У репозиторії є `launcher_export.cmd` для Task Scheduler. Приклад створення задачі:
```powershell
schtasks /Create /TN "BybitArbBot CSV Export Hourly" /TR "C:\Projectsybit-arb-bot\launcher_export.cmd" /SC HOURLY /ST 00:05 /F
```

---

## Тести та форматування
```powershell
pytest -q
pre-commit run -a
```

## Усунення несправностей (FAQ)
- **`token=None` у Telegram:** перевірте, що у `.env` використано `TELEGRAM__TOKEN` та `TELEGRAM__CHAT_ID`, або що присутні старі ключі з таблиці (бек‑міст підхопить їх).
- **`.env` не підхоплюється:** задайте повний шлях у `ENV_FILE`, перевірте, що файл збережений у UTF‑8 (BOM допускається).

## Структура проєкту (скорочено)
```text
src/
  core/            # обчислення, фільтри, алерти
  infra/           # логування, конфіги, інтеграції (dotenv_autoload, settings)
  storage/         # SQLite, збереження сигналів
  telegram/        # форматери та відправка
  ws/              # ядро WS + multiplexer (5.6)
tests/             # pytest
scripts/           # утиліти, export_signals.py
exports/, logs/, data/
```

## Ліцензія
MIT
