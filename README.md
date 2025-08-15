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
- **WS Multiplexer (Крок 5.6)** — модуль маршрутизації подій із `*`‑wildcard (мітка 5.6 не змінює чинний 5.5)
- **Інтеграція WS‑мультиплексора в `ws:run` (Крок 5.6 — підкрок)** через міст `src/ws/bridge.py` — `ws:run` публікує тікери у мультиплексор (опційні підписники)

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
TELEGRAM__BOT_TOKEN=
TELEGRAM__ALERT_CHAT_ID=
ALERT_THRESHOLD_PCT=1.0
ALERT_COOLDOWN_SEC=300
DB_PATH=data/signals.db
WS_ENABLED=1
```

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
> **Крок 5.6 (інтеграція):** всередині `ws:run` події SPOT/LINEAR публікуються у `WSMultiplexer` через `publish_bybit_ticker(...)` (див. `src/ws/bridge.py`). Це не змінює поточну поведінку — підписники опційні.

---

## Усі CLI‑команди (довідка)
```text
version           — показати версію застосунку
env               — друк активної конфігурації (безпечні поля)
logtest           — тест логування
healthcheck       — внутрішня перевірка ядра
bybit:ping        — пінг до Bybit REST
bybit:top         — топ‑пари за обсягом/ліквідністю (конфігурується)
basis:scan        — одноразовий скан спредів
basis:alert       — скан з виводом/відбором сигналів за порогами
alerts:preview    — друк відформатованого алерту для перевірки
tg:send           — надіслати довільний текст у Telegram
report:print      — друк звіту з БД (SQLite)
report:send       — відправка звіту у Telegram
select:save       — збереження добірки сигналів у БД
price:pair        — швидкий запит ціни для пари
ws:run            — запуск WS‑ядра (real‑time)
```

Параметри, що часто використовуються:
- `--threshold <pct>` — поріг basis% (наприклад, `0.5`)
- `--min-vol <usd>` — мінімальний обсяг (24h), наприклад `10000000`
- `--limit <N>` — обмеження кількості результатів
- `--symbol <TICKER>` — фільтр за символом

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
schtasks /Create /TN "BybitArbBot CSV Export Hourly" /TR "C:\Projects\bybit-arb-bot\launcher_export.cmd" /SC HOURLY /ST 00:05 /F
```

---

## WS Multiplexer (Крок 5.6)
### Мітка (marker)
`src/ws/multiplexer.py` — потокобезпечний маршрутизатор подій із підтримкою `*`‑wildcard для `source/channel/symbol`. Не створює мережевих підключень і не залежить від asyncio.  
Семантика `stats()` узгоджена з «ледачою відпискою» (поки не викликаємо `clear_inactive()`, кількість підписок відображається стало).

### Інтеграція в `ws:run` (підкрок)
`src/ws/bridge.py` — міст публікації тікерів у мультиплексор. `src/main.py` ініціалізує `WSMultiplexer` та викликає `publish_bybit_ticker(...)` у хендлерах SPOT/LINEAR.

Приклад:
```python
from src.ws.multiplexer import WSMultiplexer, WsEvent
from src.ws.bridge import publish_bybit_ticker
import time

mux = WSMultiplexer(name="core")
unsubscribe = mux.subscribe(handler=lambda e: None, source="SPOT", channel="tickers", symbol="BTCUSDT")

evt = WsEvent(source="SPOT", channel="tickers", symbol="BTCUSDT", payload={"last": "50000"}, ts=time.time())
mux.publish(evt)

publish_bybit_ticker(mux, "SPOT", {"symbol": "BTCUSDT", "last": 50000.0})
unsubscribe()
mux.clear_inactive()
```

---

## Тести
```powershell
pytest -q
```
- Покриття охоплює фільтри ліквідності, кеш котирувань, збереження в БД, форматування алертів, CSV‑експорт, WS‑мультиплексор і міст `ws:bridge`.

## Стиль коду
- Форматування: `black`
- Лінтинг: (за бажанням) `ruff`
- Принципи: мінімум зайвих змінних, читаємість, модульність.

## Структура проєкту (скорочено)
```
src/
  core/            # обчислення, фільтри, алерти
  infra/           # логування, конфіги, інтеграції
  storage/         # SQLite, збереження сигналів
  telegram/        # форматери та відправка
  ws/              # ядро WS + multiplexer (5.6), bridge
tests/             # pytest
scripts/           # утиліти, export_signals.py
exports/, logs/, data/
```

## Ліцензія
MIT
