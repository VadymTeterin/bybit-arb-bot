# IMPLEMENTATION ROADMAP (IRM)
Проєкт: **БОТ АРБІТРАЖНИЙ BYBIT**
Версія документа: ** 1.7 1.6(IRM.md)** • Дата: ** 2025-08-24 (Europe/Kyiv)**
Власник: VadymTeterin • Мітки: Implementation Roadmap (IRM), **Фаза 5 — WS (5.8.x)**, **Фаза 6 — Daily Digest (6.0/6.1)**, **Фаза 6.2 — WS Health/Resilience (6.2.x)**

---

## 🔎 Легенда статусів
- [x] **Done** — виконано / на `main` або в тегах.
- [ ] **Planned / In progress** — у процесі або заплановано.
- ⧗ **DoD pending** — реалізовано технічно, але не закрито повний DoD (тести/документація/стабільні прогони).

---

## 0) Вступ
**Мета:** стабільний бот арбітражу Bybit (Spot/Derivatives/Margin) з Telegram-алертами; звітність (GitHub Daily Digest); подальша розбудова до paper/real.
**MVP:** WS/REST сканер; фільтри ліквідності; Telegram-алерти з cooldown; стабільний рантайм; SQLite; README/CHANGELOG; тести.
**Середовище:** Windows 11, PowerShell, VS Code «Термінал», секрети в `.env`.

> Довідка: `README.md`, Releases/Tags, GitHub Actions.

---

## 1) Фази та кроки (чек-листи)

### Фаза 0 — Bootstrap / Інфраструктура
- [x] Базова структура (`src/`, `tests/`, `scripts/`, `docs/`), pre-commit гачки.
- [x] Конфіги та інструменти якості (ruff/black/isort/mypy).
- [x] `.env.example`, `.gitignore` (виключення секретів/логів/venv/тимчасових).
- [x] Windows утиліти/профілі: `use-profile.safe.ps1`, `launcher_export.cmd`.

### Фаза 1 — Каркас застосунку
- [x] CLI-вхід `python -m src.main`, базові підкоманди, логер.
- [x] README: швидкий старт (PowerShell), структура, запуск, тести.

### Фаза 2 — Bybit REST (public)
- [x] Базові REST-утиліти (foundation під сканер/звітність). ⧗ DoD pending (ретраї/ліміти/покриття).
- [ ] Повне покриття довідників/агрегованих обсягів та політик ретраїв.

### Фаза 3 — Збереження та моделі (SQLite)
- [x] Локальне збереження сигналів (SQLite/Parquet, за README). ⧗ DoD pending (бекапи/інваріанти).

### Фаза 4 — Логіка арбітражу (сканер)
- [x] Розрахунок basis/spread; відбір top-N за порогом.
- [x] Фільтри ліквідності (24h обсяг, мін. ціна).
- [x] Anti-chatter: cooldown/throttle для Telegram.
- [ ] Розширені тести (golden/edge cases).

### Фаза 5 — Повна інтеграція з Bybit (REST + WS)
**Орієнтири тегів:** `v0.5.8.3 — WS MUX normalizer & alerts (Step 5.8.3)`, `v0.5.8.4 — WS stability & supervisor` (19 Aug 2025).
- [x] 5.1 Secrets & конфіги (`.env.example`, ключі Telegram/Bybit).
- [ ] 5.2 REST-довідники/кеші (повна версія).
- [x] 5.3 Нормалізація символів (SPOT/LINEAR).
- [ ] 5.4 Агрегація обсягів 15m/30m/1h/4h — planned.
- [x] 5.5 Telegram-форматери + throttle/cooldown.
- [x] 5.6 CLI-рантайм (`ws:run`, `basis:scan`, `alerts:preview`).
- [x] 5.7 Дев-автоматизація (pre-commit/CI, reusable notify).
- [x] 5.8.3 WS MUX normalizer & alerts — **Done** (тег `v0.5.8.3`).
- [ ] 5.8.4 WS Stability — **In progress** (гілка `Step-5.8.4-ws-stability` оновлена 19 Aug).
- [ ] 5.9 Soak/Recovery (довгі прогони, авто-відновлення).

### Фаза 6 — Операційна звітність (GitHub Daily Digest)
**Орієнтири тегів:** `v0.6.1 — Digest scheduler + docs`, `v0.6.2 — GitHub client retries + rate-limit guard`, `v0.6.3 — Docs refresh` (22 Aug 2025).
- [x] 6.0.1 Каркас + GitHub-клієнт (HTTPX, auth, ретраї/ліміти).
- [x] 6.0.2 Збір подій (commits/PR/branches/tags/actions) + нормалізація.
- [x] 6.0.3 Форматери (Telegram Markdown; основа для DOCX).
- [x] 6.0.4 CI/cron (06:10 UTC ≈ 09:10 Kyiv) + секрети.
- [x] 6.0.5 Документація, .gitignore (fixtures/tmp).
- [ ] 6.0.6 E2E smoke (доставка, телеметрія) — **in progress** (ручні запуски 23–24 Aug).

### Фаза 6.1 — Config Hardening & Env Precedence
**Орієнтири тегів:** `v6.1.0 — Config Hardening (pydantic-settings v2)`, `v6.1.1 — Env precedence fix + tests` (23 Aug 2025).
- [x] 6.1.0 Harden settings (nested секції, валідація, flat-аліаси).
- [x] 6.1.1 Env precedence (flat > nested для alerts), тести, Ruff E402.
- [ ] 6.1.2 DOCX-експорт для дайджесту — planned.
- [ ] 6.1.3 Аналітика дайджестів (тижд./місячні агрегати) — planned.

### Фаза 6.2 — WS Health & Observability
- [x] 6.2.0 — WS Resilience
  - Нормалізатор Bybit `tickers` (plain + `E4/E8`), стабільні ключі `symbol/last/mark/index`, fallback символу з `topic`.
    _Файл:_ `src/exchanges/bybit/ws.py`
  - **WS Multiplexer**: *ледача відписка* (lazy unsubscribe), `stats()` для тестів.
    _Файл:_ `src/ws/multiplexer.py`
  - Базові health-поля: `uptime`, `counters.spot/linear`, `last_event_ts`.
  - **Docs/Tests:** `docs/WS_RESILIENCE.md`; ws-тести зелені.

- [x] 6.2.1 — WS Health / Manager / Status (CLI)
  - **CLI-аліас `status`** (дзеркалить `ws:health`): `uptime_ms`, `counters.spot/linear`, `reconnects_total`, `last_*`, `*_at_utc`, `last_msg_age_ms`.
    _Файли:_ `src/main.py`, `src/ws/health.py`
  - **`WSManager`**: збереження тем, heartbeat-мітки, підрахунок реконектів, **replay тем** (вмикатиметься у 6.2.2).
    _Файл:_ `src/ws/manager.py`
  - **Tests:** `tests/test_ws_resubscribe.py`, `tests/test_ws_heartbeat.py`, `tests/test_status_snapshot.py`; pre-commit green; PR у `main` — merged.

- [ ] 6.2.2 — Runtime wiring & Telegram `/status`
  - Під’єднати `WSManager` у `ws:run`: `on_connect()` → replay `subscribe`, `on_message(payload)`, `on_disconnect(reason)` + `MetricsRegistry.inc_reconnects()`.
  - **Heartbeat timeout** (15–20s) у WS-клієнті; контрольований `reconnect()`; **reset backoff** на валідних повідомленнях.
  - **Telegram `/status`**: форматований звіт метрик (CLI-поля): `uptime_ms`, counters, `reconnects_total`, `last_*`, `*_at_utc`, `last_msg_age_ms`.
    _Файли:_ `src/telegram/bot.py` (+ `formatters.py`)
  - **Integration tests:** resubscribe integration (обрив → реконект ≤ 5s → topics replayed), heartbeat-timeout, telegram-status.
  - **Docs:** README/CHANGELOG (секція 6.2.2).

- [ ] 6.2.3 — Soak & Failure Drills (planned)
  - Довгі прогони (≥ 2 год), симуляції мережевих збоїв, валідація `last_msg_age_ms`, SLO для реконектів та часу відновлення.

- [ ] 6.2.4 — Release polish (planned)
  - Оновити README/CHANGELOG (фінал 6.2.2), підготовка реліз-заміток; за потреби — тег релізу.

### Подальші фази (укрупнено)
- [ ] 7 — Risk & Money Management (quality-gates, ліміти, dry-run).
- [ ] 8 — Бектест і симулятор (історія/офлайн).
- [ ] 9 — Paper Trading (Bybit Testnet).
- [ ] 10 — Продакшн та моніторинг.
- [ ] 11 — Масштабування: мульти-біржі.
- [ ] 12 — Продуктивність/оптимізація.
- [ ] 13 — Безпека та відповідність.
- [ ] 14 — Документація й навчання.
- [ ] 15 — Передача та Roadmap v2.

---

## 2) Definition of Done (витяг)
- Крок позначається **Done** коли: код на `main`/у тегу; тести/лінтери — зелені; README/CHANGELOG оновлені; інструкції PowerShell/VS Code «Термінал» додані.
- Для WS-кроків: метрики латентності, логи ресабскрайбів; пройдені smoke/soak.

---

## 3) Операційні посилання
- README (команди, .env, запуск, структура).
- Releases/Tags (віхи `v0.5.8.x`, `v0.6.x`, `v6.1.x`).
- Actions: Workflows (`gh-digest.yml`, `Digest E2E Smoke`, `Verify Windows Launcher`, `CI`).

---

## 4) Working Agreements (витяг)
1) Перед змінами — **запит/фіксація дерева проєкту**.
2) Для copy‑paste — **повні файли**.
3) Після суттєвих змін — **README/CHANGELOG**.
4) Суттєві оновлення покриваємо **тестами**.
5) Інструкції — лише **PowerShell** та VS Code «Термінал».
6) `.gitignore` — актуальний; секрети не потрапляють у Git.

---

## 5) Наступні дії (as of 2025-08-24)
- **WS Runtime (6.2.2):** підключення `WSManager` у `ws:run`, heartbeat timeout, Telegram `/status`, інтеграційні тести resubscribe/timeouts.
- **REST покриття (2, 5.2, 5.4):** довідники/агрегації, ретраї/ліміти.
- **Операційна звітність (Фаза 6):** завершити 6.0.6, додати 6.1.2 DOCX, 6.1.3 аналітику.

---

_Підтримка: оновлювати IRM **перед кожним** новим кроком/підкроком/фіче._
