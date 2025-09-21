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

### Фаза 6.2 — SSOT-lite (автоматизація IRM)
> Оновлено: 2025-08-27T00:00:00Z

_Статуси_: **todo** — ще не почато, **doing** — в роботі, **done** — завершено, **blocked** — заблоковано

- [x] **6.2.0 — Каркас SSOT-lite (YAML + генератор + CI)**  `status: done`
  - [ ] Створено docs/irm.phase6.yaml
  - [ ] Додано tools/irm_phase6_gen.py
  - [ ] Налаштовано .github/workflows/irm_phase6_sync.yml

- [x] **6.2.1 — Інтеграція з docs/IRM.md (сентинели)**  `status: done`
  - [ ] Додати/перевірити блок  …
  - [ ] Генерувати секцію з YAML

- [x] **6.2.2 — Перевірки у PR (--check)**  `status: done`
  - [ ] GitHub Actions запускає генератор у режимі --check
  - [ ] PR фейлиться, якщо IRM не синхронізований

- [x] **6.2.3 — Ручне оновлення (--write)**  `status: done`
  - [ ] Можливість локально запускати оновлення IRM
  - [ ] Додати ops-ноту в README

- [x] **6.2.4 — QS v1.0 + README + CI + CHANGELOG (Quality Gate)**  `status: done`
  - [ ] Додано docs/QUALITY.md (QS v1.0, узгоджено з WA v2.0)
  - [ ] Додано docs/DoD.md (Definition of Done)
  - [ ] Додано docs/TESTING.md (Testing Guide)
  - [ ] Додано docs/Plan_bezpechnogo_vprovadzhennya_po_etapakh.md (Safe Rollout Plan)
  - [ ] Додано .github/PULL_REQUEST_TEMPLATE.md (шаблон PR)
  - [ ] Додано ruff.toml, isort.cfg, pre-commit-config.yaml, requirements-dev.txt (tooling на корені)
  - [ ] Оновлено README.md: розділ 'Quality & Delivery Standards' (посилання на QS/DoD/Testing/Plan), PR #40
  - [ ] Оновлено .github/workflows/ci.yml: PR — pre-commit тільки по змінених файлах; push — --all-files, PR #39
  - [ ] Оновлено CHANGELOG: секція [Unreleased] у табличному форматі (QS/README/CI)

- [x] **6.2.5 — Реліз 6.2.5 — IRM sync + repo hygiene**  `status: done`
  - [ ] Синхронізовано IRM 6.2.5 з SSOT (docs/irm.phase6.yaml  docs/IRM.md)
  - [ ] CHANGELOG: секція 6.2.5 (без змін у runtime-логіці)
  - [ ] Нормалізовано .gitattributes/.gitignore; узгоджено pre-commit/Ruff/isort
  - [ ] Жодних змін у виконуваній логіці
  - [ ] Нормалізовано line-endings через .gitattributes (LF для коду; CRLF для Windows-скриптів); виконано git add --renormalize.
  - [ ] Уніфіковано pre-commit конфіг: лишено .pre-commit-config.yaml; hook isort оновлено до 6.0.1.
  - [ ] Налаштовано isort (black profile, line_length=120); Ruff: перенесено extend-select у [lint], line-length=120, вимкнено I (import sorting).
  - [ ] Масовий autofix код-стилю (ruff-format, pyupgrade до PEP 604, isort); без зміни логіки.
  - [ ] Repo hygiene: прибрано зайві файли/логи/бекапи; додано правила до .gitignore; перенесено dev/ → docs/dev/; додано ігнор для root IRM.md.
  - [ ] pre-commit manual stage: усі хуки проходять без змін.

- [x] **6.2.6 — QS/mypy: alerts & telegram label; generator hygiene**  `status: done`
  - [ ] fix(telegram): LABEL prefix: LABEL  у сповіщеннях; експорт send_telegram() для прямого виклику; сумісність з тестом tests/test_notify_telegram_label.py.
  - [ ] fix(alerts): уніфіковано API AlertGate/SqliteAlertGateRepo: commit(), should_send(), normalized reasons (cooldown, suppressed-by-eps, Δbasis_…).
  - [ ] chore(dev): додано types-requests для mypy; приведено дотичні модулі до mypy clean.
  - [ ] refactor: легкий mypy/ruff clean у змінених файлах (без зміни бізнес-логіки).
  - [ ] mypy clean: src/core/alerts_gate.py, src/infra/alerts_repo.py, src/infra/notify_telegram.py, src/core/alerts_hook.py.
  - [ ] pytest -q: тестові набори alerts/tg/ws — 10/10 passed; повний прогін: 144 passed, 1 skipped.
  - [ ] pre-commit OK (ruff, ruff-format, isort, whitespace hooks).
  - [ ] WA: виконано на тимчасовій гілці; один-крок-за-раз; мінімальний ризик — лише формат повідомлень TG.

- [x] **6.2.7 — WS hardening (QS P0)**  `status: done`
  - [ ] Unified exponential backoff with jitter in WS-layer (shared module).
  - [ ] Bybit WS client now uses shared backoff; removed duplicates.
  - [ ] Typing pass (mypy green) for src/ws/* and exchanges/bybit/ws.py.
  - [ ] Added jitter/backoff tests; WS coverage achieved 88%.
  - [ ] IRM SSOT-lite for 6.2 left unchanged; this entry records WS QS step.

### Фаза 6.3 —

_Статуси_: **todo** — заплановано, **wip** — в роботі, **done** — завершено

- [x] **6.3.0 — SQLite persistence for alerts & signals**  `status: done`
  - [ ] alerts_repo: add alerts_log (history), keep alerts (last)
  - [ ] alerts_hook: persistent repo + log_history wrapper
  - [ ] alerts.py: log history after successful send
  - [ ] tests: repo history + integration
  - [ ] docs: README/CHANGELOG/.env.example

- [x] **6.3.1 — Схема SQLite (signals/quotes/meta)**  `status: done`

- [x] **6.3.2 — DAO + retention + тести**  `status: done`

- [x] **6.3.3 — Фільтр ліквідності**  `status: done`

- [x] **6.3.4 — Мітка чату & приглушення алертів**  `status: done`

- [x] **6.3.5 — Персист стану Gate у SQLite**  `status: done`

- [x] **6.3.6 — Maintenance SQLite (retention/VACUUM)**  `status: done`
  - [ ] {'text': 'Design/plan SQLite maintenance (schema & retention)', 'checked': True}
  - [ ] {'text': 'Implement VACUUM/compaction job + retention policy', 'checked': True}
  - [ ] {'text': 'Smoke tests for maintenance tasks', 'checked': True}

- [x] **6.3.6a — DEMO env support (linked release v6.3.6)**  `status: done`
  - [ ] REST: support api-demo endpoints in env loader + diag
  - [ ] WS: WS_PUBLIC_URL_SPOT/LINEAR overrides; host=demo in logs
  - [ ] Diag: /v5/user/query-api retCode=0; wallet-balance retCode=0
  - [ ] E2E: create/cancel order on demo env
  - [ ] Docs: README/CHANGELOG updated; tag v6.3.6

- [x] **6.3.7 — Документи: docs/HISTORY_AND_FILTERS.md, README, CHANGELOG**  `status: done`

- [x] **6.3.7a — Ops: Windows scheduler runner hardened (UTF-8, abs DB path, Set-Location; schtasks flags, full PowerShell path)**  `status: done`
  - [ ] scripts/sqlite.maint.daily.ps1: Set-Location to repo root; absolute DB path; PYTHONIOENCODING=utf-8; direct .py
  - [ ] scripts/schedule_sqlite_maint.ps1: full path to powershell.exe; correct flags for /SC DAILY
  - [ ] README: add scheduler note (Start In not required; absolute DB path)
  - [ ] CHANGELOG: add Unreleased ops entry
  - [ ] Release: tag v6.3.7a

- [x] **6.3.7b — CI/Pre-commit: IRM guards (strict local + GH Actions)**  `status: done`
  - [ ] pre-commit: forbid manual IRM.md without YAML
  - [ ] CI (GitHub Actions): irm-check.yml runs generator check on PR/push
  - [ ] README: contributor note about IRM workflow

- [x] **6.3.8 — CI: покриття, бейдж**  `status: done`
  - [ ] pytest-cov configured; coverage.xml generated
  - [ ] CI workflow runs tests w/ coverage, uploads artifact
  - [ ] Local coverage badge (docs/coverage.svg) generated in CI
  - [ ] README badge added

- [x] **6.3.9 — Генерувати секцію з YAML**  `status: done`

- [x] **6.3.10 — IRM View (read-only) з YAML → docs/IRM.view.md**  `status: done`
  - [ ] Єдине джерело правди: docs/irm.phase6.yaml → генерує docs/IRM.view.md
  - [ ] Локальний/CI-гвард блокують ручні правки IRM.view.md
  - [ ] Додати секцію 6.3.10 у YAML (status=todo)
  - [ ] Налаштувати генерацію docs/IRM.view.md: tools/render_irm_view.py --write
  - [ ] Додати CI-перевірку (irm-view-check.yml): --check
  - [ ] Оновлений docs/irm.phase6.yaml (6.3.10)
  - [ ] Згенерований docs/IRM.view.md
  - [ ] Зелений PR з новим CI-гвардом (irm-view-check.yml)
  - [ ] Не правити IRM.view.md вручну; тільки через YAML
  - [ ] Windows/PowerShell; контроль CRLF/LF через .gitattributes

- [x] **6.3.11 — Локальний guard: заборона ручних правок IRM.view.md**  `status: done`
  - [ ] Додати pre-commit хук, що виконує tools/render_irm_view.py --check
  - [ ] Розкоментувати або переозначити .gitignore для docs/IRM.view.md
  - [ ] IRM.view.md редагується тільки через YAML → генератор

### Подальші фази (укрупнено)
- [ ] 7 — Risk & Money Management (quality-gates, ліміти, dry-run).

### Фаза 7.0 —

_Статуси_: **todo** — заплановано, **wip** — в роботі, **done** — завершено

- [ ] **7.0.0 — Phase 7 kickoff & scaffolding**  `status: wip`
  - [ ] Додати файл docs/irm.phase7.yaml (каркас)
  - [ ] Оновити pre-commit перевірку IRM.view → додати irm.phase7.yaml
  - [ ] Підготувати місце для модуля ризик-менеджменту: src/core/risk_manager.py
  - [ ] Додати плейсхолдери в .env.example: RISK_DRY_RUN, RISK_MAX_POS_USD, RISK_MAX_EXPOSURE_PCT
  - [ ] Підготувати каркас тестів: tests/test_risk_manager.py
  - [ ] README/CHANGELOG: додати розділи для Phase 7 (чернетка)

- [ ] **7.1.0 — Dry-run & базові ліміти (read-only guard)**  `status: todo`
  - [ ] Імплементувати RiskManager (read-only): перевірка лімітів перед виконанням дій
  - [ ] Ліміти: max position size (USD), max exposure (%) на портфель
  - [ ] Флаг DRY_RUN: блокувати реальні дії, логувати причину відмови
  - [ ] Юніт-тести граничних значень і режимів (dry-run / live-off)
  - [ ] Документація: README (розділ Risk & Money Management), CHANGELOG запис

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
