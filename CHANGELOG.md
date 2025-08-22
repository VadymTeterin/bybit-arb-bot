## v0.6.2 � 2025-08-22
- GitHub client: ������ �����/����� �� 429/5xx �� ����������� �������
- ������� X-RateLimit-Reset
- ����-����� ��� retry-�����
# Changelog

> Історія змін структурована за фазами і підкроками. Дати подані у форматі YYYY-MM-DD (Europe/Kyiv).

---

## [0.6.1] - 2025-08-22
### Додано
- **Step-6.0.4**: Windows Task Scheduler інтеграція для GitHub Daily Digest (щодня о 07:10 Europe/Kyiv).
  - Нові скрипти: `scripts/gh_digest_run.ps1`, `scripts/schedule_gh_digest.ps1`, `scripts/unschedule_gh_digest.ps1`.
  - Форсування UTF‑8 для друку в Windows консолі (у раннері + CLI), стабільний вивід emoji.
### Змінено
- README.md: додано розділ **Manual: Schedule / Unschedule** (команди для реєстрації/видалення задачі, smoke‑перевірка).
- Логи: описано `logs/gh_digest.YYYY-MM-DD.log` для Scheduler.

---


## [0.6.0] - 2025-08-22
### Додано
- **Фаза 6 — GitHub Daily Digest**
  - Step-6.0.1: каркас (client, report, CLI scaffold, базові тести).
  - Step-6.0.2: реальна інтеграція з GitHub API (commits, merges, tags), owner/repo прапорці, .env (`GH_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`).
  - Step-6.0.3: інтеграція з Telegram `--send`, щоденний троттлінг (1 digest/доба), підтримка `--force`, автозавантаження `.env`.

### Змінено
- README.md: додано розділ **GitHub Daily Digest** з прикладами запуску.
- .env.example: нові змінні (`GH_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`, `TG_BOT_TOKEN`, `TG_CHAT_ID`).

---

## [0.5.8.4] - 2025-08-19
### Додано
- WS стабільність (Step-5.8.4), health-метрики, команда Telegram `/status`.
- Супервізор (PowerShell контролер + Python supervisor).


## v0.5.8.4 — 2025-08-19
### Added
- **WS stability & monitoring**
  - `src/ws/backoff.py` — експоненційний бекоф (cap, no-overshoot).
  - `src/ws/health.py` — локальні метрики WS (лічильники SPOT/LINEAR, аптайм, timestamps).
  - **Telegram `/status`** (`src/telegram/bot.py`) — JSON-знімок метрик.
  - **One-process supervisor** (`scripts/ws_bot_supervisor.py`) — SPOT/LINEAR WS + Telegram бот + meta-refresh.
  - **Health CLI** (`scripts/ws_health_cli.py`) — швидкий знімок метрик.
  - **Windows control** (`scripts/ws_supervisor_ctl.ps1`) — start/stop/status/restart/tail (PowerShell 5.1).

### Changed
- Раннери завантажують `.env` через **python-dotenv** (Windows-friendly).
- Оновлено README та `docs/WS_STABILITY.md` під уніфікований стиль: TOC, секції, приклади PowerShell/ENV.
- Сумісність із **aiogram 3.7+** (`DefaultBotProperties`).

### Fixed
- Дрібні попередження `ruff/isort`; стабілізація логування/винятків у раннерах.

#### 2025-08-22 — DoD підтверджено
- `ws:run` стабільно відпрацював (8+ хв smoke).
- `ws:health` завершується з `ExitCode=0`.
- Документацію вирівняно зі справжніми командами (без `--duration`).

---

## Phase #5 — Productization & Ops (2025-08-14 → 2025-08-16)

### Step 5.8 — WS multiplexer + Bybit (integration & ops) — 2025-08-16
- **Integrated:** `ws:run` працює через **WSMultiplexer** з мостом Bybit.
  - `src/ws/multiplexer.py` — маршрутизація подій (wildcards: source/channel/symbol).
  - `src/ws/bridge.py` — міст із Bybit WS у мультиплексор.
  - `src/ws/subscribers/alerts_subscriber.py` — підписник, що шле алерти (cooldown/threshold/allow/deny).
- **Changed:** `src/main.py`
  - meta-refresh через **Bybit v5 `get_tickers('spot'|'linear')`** (оновлення `vol24h`).
  - сумісність для імпорту: **`BybitWS = BybitPublicWS`** (legacy alias).
- **New (this step): stdlib .env autoload**
  - `src/infra/dotenv_autoload.py` — простий loader `.env` без зовнішніх бібліотек (UTF-8/BOM-safe, `export`/лапки, inline `#` коментарі, `${VAR}` експансія).
  - `src/infra/config.py` — виклик `autoload_env()` під час імпорту та всередині `load_settings()`; back-compat містки:
    - `TELEGRAM__TOKEN | TELEGRAM_TOKEN | TELEGRAM_BOT_TOKEN → telegram.token`
    - `TELEGRAM__CHAT_ID | TELEGRAM_CHAT_ID | TG_CHAT_ID | TELEGRAM_ALERT_CHAT_ID → telegram.chat_id`
  - **Tests:** `tests/test_env_autoload.py`, `tests/test_settings_back_compat.py`.
  - **Docs:** README/Інструкція оновлені (нові ключі, приклади PowerShell).
- **Repo hygiene:**
  - Оновлено `.gitignore` (venv/caches/logs/.env.*, *.patch, *.zip); прибрано випадкові артефакти.
  - `pre-commit` (ruff/format/isort) зелений на коміті.
- **Status:**
  - локально **tests passed**; `ws:run` з’єднується з `spot` і `linear`.
- **Next (5.8 підзадачі):**
  - RT-мітка чату (`step-5.8-RT`).
  - WS reconnect/health (`step-5.8-ws-reconnect`).

### Step 5.6 — WS Multiplexer (marker) — 2025-08-15
- Added: `src/ws/multiplexer.py` — потокобезпечний маршрутизатор подій із підтримкою `*`-wildcard (source/channel/symbol); без мережевої логіки та без asyncio.
- Added: `tests/test_ws_multiplexer.py` — subscribe/wildcards/unsubscribe (lazy)/publish-count/invalid-input.
- Changed: `stats()` — семантика «ледачої відписки». Додано `active_handlers` для діагностики.
- Notes: **Marker-only**. Чинний 5.5 не змінено.

### Step 5.6 — Integration substep (ws:run → WSMultiplexer) — 2025-08-15
- Integrated: `src/main.py` — `ws:run` публікує `tickers` у WSMultiplexer через `src/ws/bridge.py`.
- Added: `src/ws/bridge.py` — міст для публікації item-ів Bybit у мультиплексор.
- Added: `tests/test_ws_bridge.py` — перевірка доставки подій у підписників.
- Notes: Без зміни поведінки 5.5; підписники опційні.

### Step 5.5 — WS baseline & alerts stabilization — 2025-08-14
- Stabilized: `ws:run` базова конфігурація, узгодження форматерів алертів.
- Fixed: дрібні неточності CLI-довідки, перевірка входів для прев’ю алертів.
- Tests: доповнення для стабільності функціонала 5.5.

### Step 5.4 — CSV Export & Scheduling — 2025-08-14
- Added: `scripts/export_signals.py` — експорт сигналів у CSV (локалізація часу, межі за інтервалом, `--limit`, ротація `--keep`).
- Added: `launcher_export.cmd` — універсальний Windows-лаунчер для Планувальника завдань.
- Docs: інструкції UA/EN у README (VS Code “Термінал”, PowerShell).

### Step 5.3 — Docs & CLI polish — 2025-08-14
- Changed: рефакторинг документації, уніфікація структури Phase/Step, приклади PowerShell.
- Improved: опис CLI-команд та параметрів.

---

## Phase #4 — Realtime & Stability (2025-08-13 → 2025-08-14)
### Step 4.2 — WS parsing + cache update — 2025-08-13
- Implemented: парсинг WS-повідомлень (SPOT/LINEAR), нормалізація чисел, оновлення `QuoteCache`.

### Step 4.3 — Basis calc in realtime — 2025-08-13
- Real-time: обчислення basis% при оновленні кешу; застосування фільтрів ліквідності (vol, depth).

### Step 4.4 — WS alert throttling — 2025-08-13
- Added: cooldown per symbol, форматований алерт у Telegram при події.

### Step 4.5 — Auto-reconnect & healthcheck — 2025-08-13
- Added: автоматичний перепідключення WS і healthcheck ядра.

---

## Phase #3 — Filters, Persistence, QA (2025-08-10 → 2025-08-13)
### Step 3.1 — Liquidity filter — 2025-08-10
- Added: фільтр 24h обсягу.

### Step 3.2 — Depth filter — 2025-08-10
- Added: фільтр глибини ринку.

### Step 3.3 — Persistence (SQLite) — 2025-08-11
- Added: збереження сигналів, вибірки, звітність.

### Step 3.4 — Tests & Tooling — 2025-08-12
- Added: юніт-тести (фільтри, збереження, форматери алертів).
- Tooling: форматування `black`; перевірка конфігів; базове покриття.

---

## Phase #2 — REST & CLI foundation (2025-08-09 → 2025-08-10)
### Step 2.1 — Bybit client & ping — 2025-08-09
- Added: пінг до REST, первинні ендпоїнти.

### Step 2.2 — Basis scan — 2025-08-09
- Added: `basis:scan` — одноразовий аналіз спредів із порогами й сортуванням.

### Step 2.3 — Alerts (console) — 2025-08-10
- Added: `basis:alert` з вибором топ-N і фільтрами.

### Step 2.4 — CLI utilities — 2025-08-10
- Added: `bybit:top`, `price:pair`, утиліти для діагностики.

---

## Phase #1 — App skeleton (2025-08-09)
### Step 1.1 — Project layout
- Створено каркас `src/`, `tests/`, базову конфігурацію.

### Step 1.2 — Config & logging
- Налаштовано `.env`, валідацію конфігу, структуроване логування.

### Step 1.3 — CLI entrypoint
- Додано `python -m src.main <command>` та перші заглушки.

### Step 1.4 — CI-ready tests (локально)
- Додано перші тести та базову інфраструктуру під pytest.
