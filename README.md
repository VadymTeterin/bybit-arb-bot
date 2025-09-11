# Bybit Arbitrage Bot

## Quality & Delivery Standards

This project follows **QS v1.0** aligned with **Working Agreements v2.0**.

- **Quality Standard (QS v1.0):** see [docs/QUALITY.md](docs/QUALITY.md)
- **Definition of Done:** see [docs/DoD.md](docs/DoD.md)
- **Testing Guide:** see [docs/TESTING.md](docs/TESTING.md)
- **Safe Rollout Plan:** see [docs/Plan_bezpechnogo_vprovadzhennya_po_etapakh.md](docs/Plan_bezpechnogo_vprovadzhennya_po_etapakh.md)

> Tooling: `ruff.toml`, `isort.cfg`, `pre-commit-config.yaml`, `requirements-dev.txt` (at repo root).


[![Digest E2E Smoke](https://github.com/VadymTeterin/bybit-arb-bot/actions/workflows/digest-e2e-smoke.yml/badge.svg?branch=main)](https://github.com/VadymTeterin/bybit-arb-bot/actions/workflows/digest-e2e-smoke.yml)

> Windows 11 · Python 3.11+ · aiogram 3 · Bybit REST & WebSocket v5 · pydantic-settings v2

**Мета:** Telegram-бот, що в реальному часі аналізує базис між **Spot** та **USDT-перпетуалами** на Bybit, відбирає **топ-3** монети за порогом (за замовчуванням **1%**), застосовує фільтри ліквідності, зберігає історію та надсилає алерти у Telegram з троттлінгом.

---

## Зміст
- [Особливості](#особливості)
- [WS Resilience (6.2.0)](#ws-resilience-620)
- [Alerts (6.3.x)](#alerts-63x)
- [Вимоги](#вимоги)
- [Швидкий старт (PowerShell)](#швидкий-старт-powershell)
- [Конфігурація](#конфігурація)
  - [Nested ключі (рекомендовано)](#nested-ключі-рекомендовано)
  - [Сумісність зі старими flat-ключами](#сумісність-зі-старими-flat-ключами)
  - [Мікроблок: Пріоритет ключів для alerts](#мікроблок-пріоритет-ключів-для-alerts)
  - [Програмний доступ](#програмний-доступ)
- [Запуск](#запуск)
  - [CLI (локальний smoke)](#cli-локальний-smoke)
  - [Під супервізором](#під-супервізором)
  - [Telegram-команди](#telegram-команди)
- [Тести та якість коду](#тести-та-якість-коду)
- [Структура проєкту](#структура-проєкту)
- [CI/CD](#cicd)
- [Документація](#документація)
- [Траблшутінг](#траблшутінг)
- [Ліцензія](#ліцензія)

---

## Особливості

- ⚡ **WS-стріми** Bybit v5 (spot + linear) із автоперепідключенням і троттлінгом алертів
- 🧮 **Basis%** між spot і ф’ючерсами, **Top-3** монети понад поріг
- 💧 **Фільтри ліквідності**: 24h обсяг (USD), мінімальна ціна
- 📨 **Telegram-алерти** з форматуванням, антиспам (**cooldown** на монету)
- 🧱 **pydantic-settings v2**: валідовані секції конфігурації + **back-compat** зі старими ключами
- 🗄️ **SQLite / Parquet** для історії (сигнали, котирування) + **персист стану AlertGate** (6.3.5)
- 🧪 **pytest** + **ruff/black/isort/mypy** через **pre-commit**
- 🔧 Windows-орієнтований DX: інструкції лише для **PowerShell / VS Code “Термінал”**

---
- 🧪 **DEMO env**: підтримка `api-demo` для REST та явні WS override (`WS_PUBLIC_URL_SPOT/LINEAR`), banner host=demo, безпечні E2E скрипти.

## WS Resilience (6.2.0)

Покращення стабільності WS-шару та метрик (Step **6.2.0**):

- **Парсер Bybit `tickers`**: підтримка plain-полів та `E4/E8` (напр. `lastPriceE8`), fallback символу з `topic`, стабільні ключі `symbol/last/mark/index`. Файл: `src/exchanges/bybit/ws.py`.
- **WS Multiplexer**: *ледача відписка* (`unsubscribe()` вимикає доставку, але запис зберігається до `clear_inactive()`), сумісний `stats()`; файл: `src/ws/multiplexer.py`.
- **Каркас health-метрик** (SPOT/LINEAR counters, uptime, last_event_ts) — готово для `/status` у 6.2.1.

Деталі: див. **docs/WS_RESILIENCE.md**.

---

## Alerts (6.3.x)

**6.3.4 — Приглушення майже-дублікатів + cooldown:**
При повторних алертах по тому самому символу протягом `cooldown` ми приглушуємо повідомлення,
якщо зміна базису менша за `SUPPRESS_EPS_PCT` (у відсоткових пунктах) протягом вікна `SUPPRESS_WINDOW_MIN`.
Приглушення активне **лише під час дії cooldown**.

**6.3.5 — Персист стану гейта у SQLite:**
Записуємо останній надісланий сигнал (час + basis) у `alerts.db` — завдяки цьому
троттлінг і приглушення виживають після рестартів. SQLite відкриваємо в WAL-режимі.

**Telegram Chat Label (ENV-префікс):**
Якщо задано `TELEGRAM__LABEL`, у повідомленнях Telegram додається префікс `"LABEL | ..."`. Зручно для `DEV`/`STAGE`.

---

**6.3.6a — DEMO env support (release v6.3.6):**
- REST: лоадер ENV і `scripts/diag_bybit_keys` підтримують `https://api-demo.bybit.com` (перевірка `retCode: 0` і балансів).
- WS: параметри `WS_PUBLIC_URL_SPOT`/`WS_PUBLIC_URL_LINEAR` дозволяють явно вказати DEMO-стріми, лог у `smoke_bybit_ws` показує `host=demo`.
- E2E: `scripts/e2e_bybit.py` друкує банер із активними DEMO-ендпоїнтами; `scripts/e2e_bybit_testnet` у DEMO-режимі вміє **create/cancel** ордер.
- Безпека: створення ордерів тільки якщо встановлено `BYBIT_PLACE_ORDER=1` (і ціна далеко від ринку для smoke).
- Документи оновлено: README/CHANGELOG, тег **v6.3.6**.

## Вимоги

- Windows 11
- Python **3.11+**
- Інтернет (Wi-Fi до 1 Гбіт, роутер Archer A64 — ок)
- Токени: **Telegram Bot Token**, **Telegram Chat ID**
- (Опц.) **Bybit API Key/Secret** для приватних методів; публічні WS/REST працюють і без них

---

## Швидкий старт (PowerShell)
### 1) Активація venv (Windows)
```powershell
& .\.venv\Scripts\Activate.ps1
```

### 2) Установити залежності
```powershell
pip install -r requirements.txt
```

### 3) Конфігурація ENV (.env або змінні середовища)

**DEMO (рекомендовано для тестів):**
```powershell
$env:BYBIT_PUBLIC_URL  = 'https://api-demo.bybit.com'
$env:BYBIT_PRIVATE_URL = 'https://api-demo.bybit.com'
# (опційно) явні DEMO WS-ендпоїнти
$env:WS_PUBLIC_URL_SPOT   = 'wss://stream-demo.bybit.com/v5/public/spot'
$env:WS_PUBLIC_URL_LINEAR = 'wss://stream-demo.bybit.com/v5/public/linear'
```
`.env` приклад (ключі з **Demo Trading** в кабінеті Bybit):
```dotenv
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
BYBIT_USE_SERVER_TIME=1
BYBIT_RECV_WINDOW_MS=20000
```
Завантаження `.env` і швидка перевірка масок:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\load.bybit.env.ps1
.\scripts\safe.show.bybit.env.ps1
```

### 4) Smoke‑тести
Підпис і баланси:
```powershell
python -m scripts.diag_bybit_keys
python -m scripts.smoke_bybit
```
WS тікери:
```powershell
python -m scripts.smoke_bybit_ws
```

### 5) E2E (без ордерів)
```powershell
python -m scripts.e2e_bybit
```

### 6) (опційно) тест create/cancel
```powershell
$env:BYBIT_ORDER_SIDE='buy'; $env:BYBIT_ORDER_QTY='0.001'; $env:BYBIT_ORDER_PRICE='100000'; $env:BYBIT_PLACE_ORDER='1'
python -m scripts.e2e_bybit_testnet
Remove-Item Env:BYBIT_PLACE_ORDER -ErrorAction SilentlyContinue
```
## Конфігурація

Лоадер: `src/infra/config.py` (**pydantic-settings v2**, роздільник **`__`**).
Пріоритет: **Environment** → **.env** → **дефолти в коді**.

### Nested ключі (рекомендовано)

```env
RUNTIME__ENV=dev
RUNTIME__ENABLE_ALERTS=true
RUNTIME__DB_PATH=./data/signals.db
RUNTIME__TOP_N_REPORT=10

TELEGRAM__TOKEN=
TELEGRAM__CHAT_ID=
TELEGRAM__LABEL=

BYBIT__API_KEY=
BYBIT__API_SECRET=

ALERTS__THRESHOLD_PCT=1.0        # 0..100
ALERTS__COOLDOWN_SEC=300         # 0..86400
ALERTS__SUPPRESS_EPS_PCT=0.2     # epsilon у відсоткових пунктах
ALERTS__SUPPRESS_WINDOW_MIN=15   # хвилинне вікно для epsilon
ALERTS__DB_PATH=./data/alerts.db # шлях до SQLite для гейта
# (планується) ALERTS__KEEP_DAYS=7

LIQUIDITY__MIN_VOL_24H_USD=10000000
LIQUIDITY__MIN_PRICE=0.001
```

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
| `TELEGRAM__LABEL`                           | `TELEGRAM_LABEL`, `TG_LABEL`, `ALERT_CHAT_LABEL`            |
| `BYBIT__API_KEY`                            | `BYBIT_API_KEY`                                             |
| `BYBIT__API_SECRET`                         | `BYBIT_API_SECRET`                                          |
| `ALERTS__THRESHOLD_PCT`                     | `ALERT_THRESHOLD_PCT`                                       |
| `ALERTS__COOLDOWN_SEC`                      | `ALERT_COOLDOWN_SEC`                                        |
| `ALERTS__SUPPRESS_EPS_PCT`                  | `ALERTS_SUPPRESS_EPS_PCT`                                   |
| `ALERTS__SUPPRESS_WINDOW_MIN`               | `ALERTS_SUPPRESS_WINDOW_MIN`                                |
| `ALERTS__DB_PATH`                           | `ALERTS_DB_PATH`                                            |
| (план) `ALERTS__KEEP_DAYS`                  | `ALERTS_KEEP_DAYS`                                          |
| `LIQUIDITY__MIN_VOL_24H_USD`                | `MIN_VOL_24H_USD`                                           |
| `LIQUIDITY__MIN_PRICE`                      | `MIN_PRICE`                                                 |

### Мікроблок: Пріоритет ключів для alerts

> Якщо одночасно задано `ALERTS__THRESHOLD_PCT` (nested) і `ALERT_THRESHOLD_PCT` (flat),
> перемагає **flat**. Так само для `COOLDOWN_SEC`, `SUPPRESS_*`, `DB_PATH`.

### Програмний доступ

```python
from src.infra.config import load_settings

s = load_settings()
print("env:", s.env)                                  # mirrors s.runtime.env
print("enable_alerts:", s.enable_alerts)              # mirrors s.runtime.enable_alerts
print("alerts:", s.alerts.threshold_pct, s.alerts.cooldown_sec)
print("suppress:", s.alerts.suppress_eps_pct, s.alerts.suppress_window_min)
print("alerts db:", s.alerts.db_path)
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

**pytest**: **144 passed, 1 skipped** (локально).
**pre-commit**: `ruff`, `ruff-format`, `isort`, `black`, `mypy`, trim-whitespace, EOF check.
Комміти — у стилі **Conventional Commits**.

---

## Структура проєкту

```
src/
  exchanges/
    bybit/
      ws.py
  ws/
    multiplexer.py
    backoff.py
    health.py
    bridge.py
  core/
  infra/
    config.py
  telegram/
  storage/
scripts/
tests/
docs/
```

---

## CI/CD

- **GitHub Actions**: лінтинг (ruff/black/isort), тести (pytest), типізація (mypy)
- **Reusable notify** workflow з `secrets: inherit`
- **Digest E2E Smoke**: збірка дайджесту, артефакт, опційне повідомлення у Telegram

---

## Документація

**IRM Maintenance**

- Канонічний SSOT: `docs/irm.phase6.yaml` (**UTF‑8, без BOM**).
- Генерація IRM:
  ```powershell
  # перевірка синхронності
  python .\tools\irm_phase6_gen.py --check
  # оновлення MD з SSOT
  python .\tools\irm_phase6_gen.py --write
  ```
- Уникайте ручного редагування `docs/IRM.md` — тільки генератор.


- **WS Resilience (6.2.0)** — `docs/WS_RESILIENCE.md`
- **IRM** — оновлюється **лише генератором** (`Render IRM.view.md`)

---

## Траблшутінг

- **`pip install -r requirements.txt` падає через \x00** — не використовуйте `-Encoding Unicode` для `requirements.txt`; зберігайте файл у **UTF-8**.
- **`git diff` «нескінченний»** — ви у пейджері; натисніть `q` або використайте `git --no-pager diff`.
- **CRLF/LF попередження** — додайте `.gitattributes` із правилами EOL; Python-файли краще з **LF**.
- **PowerShell і лапки у git commit -m** — для складних повідомлень використовуйте одинарні лапки або `-F file.txt`.
- **Digest не шле у Telegram** — перевірте `TELEGRAM__TOKEN/CHAT_ID` (секрети не логуються).

---

- **Bybit: `API key is invalid`**
  - Перевір, що **тип акаунта відповідає ендпоїнту**:
    - Demo Trading → `https://api-demo.bybit.com` (+ WS `wss://stream-demo.bybit.com/...`)
    - Testnet → `https://api-testnet.bybit.com`
    - Mainnet → `https://api.bybit.com`
  - Ключі з Demo/Testnet **не працюють** на іншому ендпоїнті.
  - Перевір таймінг підпису: додай `BYBIT_USE_SERVER_TIME=1` і `BYBIT_RECV_WINDOW_MS=20000`.
  - Швидка перевірка: `python -m scripts.diag_bybit_keys` (очікуємо `retCode: 0`).

- **WS показує host=mainnet, коли очікується DEMO**
  - Вкажи явні WS‑ендпоїнти:
    ```powershell
    $env:WS_PUBLIC_URL_SPOT   = 'wss://stream-demo.bybit.com/v5/public/spot'
    $env:WS_PUBLIC_URL_LINEAR = 'wss://stream-demo.bybit.com/v5/public/linear'
    ```
  - Перевір: `python -m scripts.smoke_bybit_ws` (у банері має бути `host=demo`).

## Ліцензія

MIT © 2025
