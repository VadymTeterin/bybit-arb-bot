# Bybit Arbitrage Bot

> Windows 11 · Python 3.11+ · aiogram 3 · Bybit REST & WebSocket v5 · pydantic-settings v2

**Мета:** Telegram-бот, що в реальному часі аналізує базис між **Spot** та **USDT-перпетуалами** на Bybit, відбирає **топ-3** монети за порогом (за замовчуванням **1%**), застосовує фільтри ліквідності, зберігає історію та надсилає алерти у Telegram з троттлінгом.

---

## Зміст
- [Особливості](#особливості)
- [Вимоги](#вимоги)
- [Швидкий старт (PowerShell)](#швидкий-старт-powershell)
- [Конфігурація](#конфігурація)
  - [Nested ключі (рекомендовано)](#nested-ключі-рекомендовано)
  - [Сумісність зі старими flat-ключами](#сумісність-зі-старими-flatключами)
  - [Програмний доступ](#програмний-доступ)
- [Запуск](#запуск)
  - [CLI (локальний smoke)](#cli-локальний-smoke)
  - [Під супервізором](#під-супервізором)
  - [Telegram-команди](#telegramкоманди)
- [Тести та якість коду](#тести-та-якість-коду)
- [Структура проєкту](#структура-проєкту)
- [CI/CD](#cicd)
- [Траблшутінг](#траблшутінг)
- [Ліцензія](#ліцензія)

---

## Особливості

- ⚡ **WS-стріми** Bybit v5 (spot + linear) із автоперепідключенням і троттлінгом алертів
- 🧮 **Basis%** між spot і ф’ючерсами, **Top-3** монети понад поріг
- 💧 **Фільтри ліквідності**: 24h обсяг (USD), мінімальна ціна
- 📨 **Telegram-алерти** з форматуванням, антиспам (**cooldown** на монету)
- 🧱 **pydantic-settings v2**: валідовані секції конфігурації + **back-compat** зі старими ключами
- 🗄️ **SQLite / Parquet** для історії (сигнали, котирування)
- 🧪 **pytest** + **ruff/black/isort/mypy** через **pre-commit**
- 🔧 Windows-орієнтований DX: інструкції лише для **PowerShell / VS Code “Термінал”**

---

## Вимоги

- Windows 11
- Python **3.11+**
- Доступ до Інтернету (Wi-Fi до 1 Гбіт, роутер Archer A64 — ок)
- Токени: **Telegram Bot Token**, **Telegram Chat ID** (для надсилання алертів)
- (Опційно) **Bybit API Key/Secret** для приватних методів; публічні WS/REST працюють і без них

---

## Швидкий старт (PowerShell)

```powershell
# 1) Клон репозиторію
git clone https://github.com/VadymTeterin/bybit-arb-bot.git
cd bybit-arb-bot

# 2) Віртуальне середовище
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Залежності
pip install -r .
equirements.txt

# 4) Конфіг
Copy-Item .\.env.example .\.env
# заповніть TELEGRAM__TOKEN, TELEGRAM__CHAT_ID, (опційно) BYBIT__API_KEY/SECRET

# 5) Перевірка
pytest -q
pre-commit run -a
```

> **Безпека:** ніколи не комітьте `.env`. Файл уже у `.gitignore`.

---

## Конфігурація

Файл-лоадер: `src/infra/config.py` (pydantic-settings v2, **nested delimiter** `__`).
Пріоритет: **Environment** → **.env** → **дефолти в коді**.
Булеві: `true/false`, `1/0`, `yes/no`, `on/off` (без урахування регістру).
Списки (CSV): `BTCUSDT,ETHUSDT` → `["BTCUSDT", "ETHUSDT"]`.

### Nested ключі (рекомендовано)

```env
RUNTIME__ENV=dev
RUNTIME__ENABLE_ALERTS=true
RUNTIME__DB_PATH=./data/signals.db
RUNTIME__TOP_N_REPORT=10

TELEGRAM__TOKEN=
TELEGRAM__CHAT_ID=

BYBIT__API_KEY=
BYBIT__API_SECRET=
# BYBIT__WS_PUBLIC_URL_LINEAR=wss://stream.bybit.com/v5/public/linear
# BYBIT__WS_PUBLIC_URL_SPOT=wss://stream.bybit.com/v5/public/spot
# BYBIT__WS_SUB_TOPICS_LINEAR=tickers.BTCUSDT,tickers.ETHUSDT
# BYBIT__WS_SUB_TOPICS_SPOT=tickers.BTCUSDT,tickers.ETHUSDT

ALERTS__THRESHOLD_PCT=1.0      # 0..100
ALERTS__COOLDOWN_SEC=300       # 0..86400

LIQUIDITY__MIN_VOL_24H_USD=10000000
LIQUIDITY__MIN_PRICE=0.001
```

**Валідація:**
- `ALERTS__THRESHOLD_PCT` ∈ `[0..100]`
- `ALERTS__COOLDOWN_SEC` ∈ `[0..86400]`
- `LIQUIDITY__MIN_VOL_24H_USD` ≥ `0`, `LIQUIDITY__MIN_PRICE` ≥ `0`
- `RUNTIME__TOP_N_REPORT` ∈ `[1..100]`

### Сумісність зі старими flat-ключами

Усі legacy-ключі **підтримуються**. Якщо задано і nested, і flat — **flat переважає**.

| Nested (recommended)                        | Legacy (supported)                                          |
|---------------------------------------------|-------------------------------------------------------------|
| `RUNTIME__ENV`                              | `ENV`                                                       |
| `RUNTIME__DB_PATH`                          | `DB_PATH`                                                   |
| `RUNTIME__TOP_N_REPORT`                     | `TOP_N_REPORT`                                              |
| `RUNTIME__ENABLE_ALERTS`                    | `ENABLE_ALERTS`                                             |
| `TELEGRAM__TOKEN`                           | `TELEGRAM_TOKEN`, `TELEGRAM_BOT_TOKEN`                      |
| `TELEGRAM__CHAT_ID`                         | `TELEGRAM_CHAT_ID`, `TG_CHAT_ID`, `TELEGRAM_ALERT_CHAT_ID`  |
| `BYBIT__API_KEY`                            | `BYBIT_API_KEY`                                             |
| `BYBIT__API_SECRET`                         | `BYBIT_API_SECRET`                                          |
| `ALERTS__THRESHOLD_PCT`                     | `ALERT_THRESHOLD_PCT`                                       |
| `ALERTS__COOLDOWN_SEC`                      | `ALERT_COOLDOWN_SEC`                                        |
| `LIQUIDITY__MIN_VOL_24H_USD`                | `MIN_VOL_24H_USD`                                           |
| `LIQUIDITY__MIN_PRICE`                      | `MIN_PRICE`                                                 |
| `BYBIT__WS_PUBLIC_URL_LINEAR`               | `WS_PUBLIC_URL_LINEAR` *(override)*                         |
| `BYBIT__WS_PUBLIC_URL_SPOT`                 | `WS_PUBLIC_URL_SPOT` *(override)*                           |
| `BYBIT__WS_SUB_TOPICS_LINEAR`               | `WS_SUB_TOPICS_LINEAR` *(override)*                         |
| `BYBIT__WS_SUB_TOPICS_SPOT`                 | `WS_SUB_TOPICS_SPOT` *(override)*                           |

### Програмний доступ

```python
# comments: English only
from src.infra.config import load_settings

s = load_settings()
print("env:", s.env)                                  # mirrors s.runtime.env
print("enable_alerts:", s.enable_alerts)              # mirrors s.runtime.enable_alerts
print("alerts:", s.alerts.threshold_pct, s.alerts.cooldown_sec)
print("liquidity:", s.liquidity.min_vol_24h_usd, s.liquidity.min_price)
print("telegram token present:", bool(s.telegram.token))  # never print secrets
```

---

## Запуск

### CLI (локальний smoke)

```powershell
# топ-3 за дефолтним порогом
python -m src.main basis:alert --limit 3

# із кастомним порогом і мінімальним обсягом
python -m src.main basis:alert --limit 3 --threshold 0.8 --min-vol 12000000
```

### Під супервізором

Скрипт керування (PowerShell): `scripts/ws_supervisor_ctl.ps1`

```powershell
.\scripts\ws_supervisor_ctl.ps1 start
.\scripts\ws_supervisor_ctl.ps1 status
.\scripts\ws_supervisor_ctl.ps1 tail -TailLines 200
.\scripts\ws_supervisor_ctl.ps1 restart
.\scripts\ws_supervisor_ctl.ps1 stop
```

Логи: `logs/app.log`, `logs/supervisor.*.log`. PID: `run/supervisor.pid`.

### Telegram-команди

- `/start` — коротка довідка і параметри
- `/top3` — поточні топ-3 монети
- `/set_threshold 1.5` — змінити поріг у %
- `/status` — перевірка стану (WS/REST/алерти)
- `/report` — зведення за період

---

## Тести та якість коду

```powershell
pytest -q
pre-commit run -a
```

**pre-commit** (repo-level): `ruff`, `ruff-format`, `isort`, `black`, `mypy`, trim-whitespace, EOF check.
Гайд-коммітів: **Conventional Commits** (наприклад, `feat(config): ...`).

---

## Структура проєкту

```
src/
  core/                 # business-логіка (basis, selector, alerts)
  infra/                # конфіг, логування, сховище, планувальник
    config.py           # pydantic-settings v2 (nested + back-compat)
  telegram/             # bot handlers, форматування повідомлень
  bybit/                # REST/WS клієнти, утиліти
  storage/              # SQLite/Parquet
scripts/
  ws_supervisor_ctl.ps1 # керування рантаймом
  gh_daily_digest.py    # (опц.) GitHub Daily Digest CLI
tests/                  # pytest (юніт + інтеграційні)
```

---

## CI/CD

- **GitHub Actions**: лінтинг (ruff/black/isort), тести (pytest), типізація (mypy)
- **Reusable notify** workflow з передачею `secrets: inherit`
- **Digest E2E Smoke**: збірка дайджесту, артефакт, опційне повідомлення у Telegram

> Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, (опц.) `GH_TOKEN`.

---

## Траблшутінг

- **`pip install -r requirements.txt` падає через \x00** — не використовуйте `-Encoding Unicode` для `requirements.txt`; зберігайте в **UTF-8**.
- **`git diff` «нескінченний»** — ви у пейджері; натисніть `q` для виходу або `git --no-pager diff`.
- **CRLF/LF попередження** — додайте `.gitattributes` із правилами EOL; Python-файли краще з **LF**.
- **Digest не шле у Telegram** — перевірте `TELEGRAM_TOKEN/CHAT_ID` (секрети не логуються).

---

## Ліцензія

MIT © 2025
