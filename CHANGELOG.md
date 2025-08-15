# Changelog

> Історія змін структурована за фазами і підкроками. Дати подані у форматі YYYY-MM-DD (Europe/Kyiv).

## Phase #5 — Productization & Ops (2025-08-14 → 2025-08-16)

### Step 5.8 — WS multiplexer + Bybit (integration & ops) — 2025-08-16
- **Integrated:** `ws:run` працює через **WSMultiplexer** з мостом Bybit:
  - `src/ws/multiplexer.py` — маршрутизація подій (wildcards: source/channel/symbol).
  - `src/ws/bridge.py` — міст із Bybit WS у мультиплексор.
  - `src/ws/subscribers/alerts_subscriber.py` — підписник, що шле алерти (cooldown/threshold/allow/deny).
- **Changed:** `src/main.py`
  - meta-refresh тепер через **Bybit v5 `get_tickers('spot'|'linear')`** (оновлення `vol24h`), без залежності від `get_spot_map()`/`get_linear_map()`.
  - додано сумісність для імпорту: **`BybitWS = BybitPublicWS`** (legacy alias).
- **Fixed (Windows/Repo hygiene):**
  - `.gitattributes` для нормалізації EOL.
  - оновлено `.gitignore`, припинено трекати `__tmp/` артефакти.
- **Tooling:**
  - додано **`.pre-commit-config.yaml`**: `ruff`, `ruff-format`, `isort`, `end-of-file-fixer`, `trailing-whitespace`.
- **CI:**
  - **GitHub Actions** workflow `CI` — `pre-commit` + `pytest` (Python 3.12).
- **Docs:**
  - `docs/STEP-5.8-WS-MUX.md` — інструкції запуску WS (PowerShell), змінні `BYBIT__WS_*`, FAQ.
- **Status:**
  - локально **57/57 tests passed**; `ws:run` з’єднується зі `spot` і `linear`; у логах регулярне **“Refreshed vol24h for 314 symbols”**.
- **Branches/PR:**
  - `step-5.8-ws-mux → step-5.8-RT` — **merged**.
  - `step-5.8-ws-run` — підготовлено для PR у `step-5.8-RT` (правки `ws:run`, alias, docs).

### Step 5.6 — WS Multiplexer (marker) — 2025-08-15
- Added: `src/ws/multiplexer.py` — потокобезпечний маршрутизатор подій із підтримкою `*`-wildcard (source/channel/symbol); без мережевої логіки та без asyncio.
- Added: `tests/test_ws_multiplexer.py` — subscribe/wildcards/unsubscribe (lazy)/publish-count/invalid-input.
- Changed: `stats()` — семантика «ледачої відписки»: `active_subscriptions == total_subscriptions` до `clear_inactive()`. Додано `active_handlers` для діагностики.
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
