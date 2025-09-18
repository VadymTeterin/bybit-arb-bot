
# Changelog

Усі суттєві зміни цього проєкту документуються тут. Формат — за принципами
**[Keep a Changelog](https://keepachangelog.com/uk-UA/1.1.0/)** та **SemVer**.
Дати наведені у форматі **YYYY-MM-DD (Europe/Kyiv)**.

> Примітка: у записах можуть згадуватись етапи розробки *Phase N / Step-N.X*,
> що відповідають нашому внутрішньому Implementation Roadmap (IRM).


`------------------------------------------------------------------------------------------------`

## [6.3.8] — 2025-09-18
**Phase 6 — Step-6.3.8 · CI: покриття, бейдж**

### Added
- **CI workflow** `tests-coverage-badge.yml`: запуск на `pull_request` і `push` до `main` (+ ручний `workflow_dispatch`).
- **Покриття**: `pytest` + `pytest-cov` → `coverage.xml`; локальний бейдж `docs/coverage.svg` через `coverage-badge`.
- **Артефакти**: збереження `coverage-xml` і `coverage-badge` у GitHub Actions.
- **Авто-коміт бейджа на main** (`stefanzweifel/git-auto-commit-action@v5`) — автор і комітер **github-actions[bot]**;
  повідомлення: `chore(coverage): update docs/coverage.svg [skip ci]`.
- **README**: додано бейдж покриття у шапку.

### Changed
- `paths-ignore: ["docs/coverage.svg"]` щоб уникнути CI-циклів.
- Додано швидкий тест `tests/test_infra_notify_import.py` для стабілізації порогу ≥67%.

### Notes
- IRM: секція **6.3.8** відмічена як `done`; далі — крок **6.3.9** (генерація IRM з YAML).


`------------------------------------------------------------------------------------------------`

## [6.3.7b] - 2025-09-17
### Added
- README: розділ “IRM workflow (Phase 6)” (правильний процес редагування IRM)
- Pre-commit guard: заборона ручних правок `docs/IRM.md` без `docs/irm.phase6.yaml`
- CI (GitHub Actions): `irm-check.yml` перевіряє синхронність на PR/push

### Notes
— Документація та інфраструктурні перевірки, без змін рантайму.


`------------------------------------------------------------------------------------------------`

## [Unreleased]
### Ops
- Windows Task Scheduler: hardened runner — sets working directory to repo root, resolves absolute DB path, forces UTF-8 I/O, uses direct `.py` call; fixed `schtasks` flags and full path to `powershell.exe`.


`------------------------------------------------------------------------------------------------`
## [6.3.7] — 2025-09-14
**Phase 6 — Step-6.3.7 · Documentation update (README/CHANGELOG/HISTORY_AND_FILTERS)**

### Added
- **Docs**: `README.md` section on SQLite Maintenance expanded (CLI usage, daily scheduler, logs, troubleshooting).
- **Docs**: `docs/HISTORY_AND_FILTERS.md` appendix on retention policy (signals 14d, alerts_log 30d, quotes 7d).
- **CHANGELOG**: this entry.

### Changed
- IRM 6.3.6 marked as **done**; synced documentation.
- Updated examples to use `python .\scripts\sqlite_maint.py` instead of `-m`.

### Ops
- Daily scheduler task: `BybitBot_SQLiteMaint_Daily` @ 03:15 (local), runner `scripts/sqlite.maint.daily.ps1`.
- Re-registration helper: `scripts/schedule_sqlite_maint.ps1`.
- Manual trigger & log validation documented in README.

### Notes
- Safe usage: run `--dry-run` first, take DB backup before `--execute`.
- Logs: `logs/sqlite_maint.log`.

[6.3.7]: https://github.com/VadymTeterin/bybit-arb-bot/compare/v6.3.6b...v6.3.7


`------------------------------------------------------------------------------------------------`

## [6.3.6b] — 2025-09-12
**Phase 6 — Step-6.3.6 · SQLite Maintenance (retention & compaction)**

### Added
- **SQLite maintenance CLI** (`scripts/sqlite_maint.py`):
  - Modes: `--dry-run`, `--execute`, `--retention-only`, `--compact-only`.
  - Safe guard: requires `SQLITE_MAINT_ENABLE=1` for `--execute`.
  - Index creation only if table exists.
  - JSON metrics output (size_before/after, counts, deleted, elapsed_ms).
- **PowerShell wrapper** `scripts/sqlite.maint.ps1` for Windows Task Scheduler integration.
- **ENV variables** (`.env.example`): `SQLITE_DB_PATH`, `SQLITE_MAINT_ENABLE`, `SQLITE_RETENTION_*_DAYS`,
  `SQLITE_MAINT_VACUUM_STRATEGY`, `SQLITE_MAINT_MAX_DURATION_SEC`.
- **README.md** updated: section "6.3.6 — SQLite Maintenance".

### Changed
- Guarded index creation in `sqlite_maint.py` to avoid errors on missing tables.

### Notes
- Incremental vacuum requires DB created with `auto_vacuum=INCREMENTAL`. If DB was created with `NONE`, run a one-time FULL VACUUM off-hours.
- Recommended schedule: daily at 03:15, retention first, then compact.
- IRM: this release closes Step-6.3.6 as **done**.
- Release tag: **v6.3.6b**.

[6.3.6b]: https://github.com/VadymTeterin/bybit-arb-bot/compare/v6.3.6...v6.3.6b

`------------------------------------------------------------------------------------------------`

## [6.3.6] — 2025-09-07
**Phase 6 — Step-6.3.6a · DEMO env (api-demo) + WS host=demo + env loader hardening**

### Added
- **DEMO середовище (`api-demo.bybit.com`)** під ключами з `.env` і змінними оточення.
  - `scripts/load.bybit.env.ps1` — коректно підтягує DEMO URL-и для **REST** і маскує ключі.
  - `scripts/safe.show.bybit.env.ps1` — безпечно показує замасковані ключі та **api-demo** в host.
  - **WS-ендпоїнти можна перевизначити** через `WS_PUBLIC_URL_SPOT` і `WS_PUBLIC_URL_LINEAR`.
  - `scripts/smoke_bybit_ws.py` — читає ці змінні та логікує **host=demo** в заголовку.
  - `scripts/e2e_bybit.py` — банер середовища (REST/WS) і делегація до легасі-раннера для e2e.

### Changed
- `scripts/e2e_bybit_testnet.py` — узгоджено повідомлення для DEMO‑рунів; шлях створення/скасування ордера
  лишився попереднім і активується прапором `BYBIT_PLACE_ORDER=1`.

### Notes
- Тестовий прогін: REST підпис/баланси (`retCode: 0`), WS тікери з **host=demo**, e2e створення/скасування ордера — ок.
- IRM: цей реліз відповідає підкроку **6.3.6a (DEMO env)**; підкрок **6.3.6 (SQLite maintenance)** лишається `todo` у IRM.
- Релізний тег: **v6.3.6**.

[6.3.6]: https://github.com/VadymTeterin/bybit-arb-bot/compare/v6.3.5...v6.3.6


`------------------------------------------------------------------------------------------------`
## [6.3.5] — 2025-08-27
**Phase 6 — Step-6.3.4 / 6.3.5 · Alerts cooldown + suppression + persistence**

### Added
- **AlertGate**: троттлінг алертів + **приглушення майже-дублікатів** (epsilon у відсоткових пунктах)
  — **приглушення застосовується лише під час дії cooldown-вікна**.
  - Конфіг: `ALERTS__SUPPRESS_EPS_PCT`, `ALERTS__SUPPRESS_WINDOW_MIN` *(flat-дзеркала:*
    `ALERTS_SUPPRESS_EPS_PCT`, `ALERTS_SUPPRESS_WINDOW_MIN`)*.
  - 5/5 юніт-тестів для гейта (`tests/test_alerts_gate.py`).

- **Персист стану гейта у SQLite** (`SqliteAlertGateRepo`):
  - Зберігання останнього відправленого сигналу на символ (timestamp + basis).
  - WAL-режим; живе через рестарти; інтегровано в `alerts_hook`.
  - Конфіг шляху: `ALERTS_DB_PATH` (*альтернатива nested:* `ALERTS__DB_PATH`).

- **Telegram chat label prefix** (позначка середовища на початку повідомлення):
  - Джерело: `TELEGRAM__LABEL` (якщо не задано — може виводитись на основі `RUNTIME__ENV`).
  - Збережено API `send_telegram(text, enabled=True)`.
  - Юніт-тест: `tests/test_notify_telegram_label.py` (перевіряє префікс).

- **pytest.ini**: обмежено пошук тестів до `tests/`, ігнор `dev/tmp` (щоб не ловити тимчасові файли).

### Tests
- Локально: **144 passed, 1 skipped**.

### Migration Notes
- Для активації приглушення задайте `ALERTS__SUPPRESS_EPS_PCT` (напр. `0.2`) і `ALERTS__SUPPRESS_WINDOW_MIN` (напр. `15`).
- Щоб увімкнути префікс середовища у Telegram, задайте `TELEGRAM__LABEL` (напр. `DEV`).
- Для персистенції стану гейта створіть/задайте шлях до БД: `ALERTS_DB_PATH=./data/alerts.db` (каталог буде створено автоматично).

[6.3.5]: https://github.com/VadymTeterin/bybit-arb-bot/compare/v6.2.0...v6.3.5

`------------------------------------------------------------------------------------------------`

## [6.3.4] — 2025-08-27
**Phase 6 — Step-6.3.4 · Мітка чату & приглушення алертів**
### Added
- Конфіг **`TELEGRAM__CHAT_LABEL`** для маркування чатів (прод/тест) і розмежування стримів алертів.
- Механізм **приглушення/дедуплікації**: cooldown + придушення майже дубльованих алертів (символ/напрям/база).
- Персист стану **AlertGate** у SQLite (останній алерт по символу) — збереження через рестарти.
### Changed
- `alerts.py`: алерт відправляється лише якщо пройдено cooldown і він не дубль поточного стану.
- `alerts_repo.py`: розширено модель запису останнього алерта (ts_epoch, basis_pct, side, chat_label).
### Docs
- README: пояснення тегування чату та приклади `.env` із `TELEGRAM__CHAT_LABEL`.
- CHANGELOG: цей запис; IRM 6.3 оновлено (6.3.4 — done).
### Notes
- Поля стану збережено у WAL‑режимі; сумісність із попереднім форматом збережено (бек‑компат).
- Дедуплікація працює у тандемі з 6.3.3 (фільтр ліквідності).

`------------------------------------------------------------------------------------------------`

## [6.3.3] — 2025-08-26
**Phase 6 — Step-6.3.3 · Фільтр ліквідності**
### Added
- Конфіги **`LIQUIDITY__MIN_VOL_24H_USD`**, **`LIQUIDITY__MIN_PRICE`** для відсікання тонких ринків.
- Пайплайн **LiquidityGate** перед AlertGate: не пропускає сигнали, що нижче порогів.
- Тести: фікстури котирувань низької/високої ліквідності; інтеграційні тести алерт‑пайплайну.
### Changed
- `signals.py`/`pipeline.py`: вставлено стадію перевірки ліквідності перед формуванням повідомлень.
### Docs
- README: секція «Фільтри ліквідності» (24h обсяг USD та мінімальна ціна).
- CHANGELOG/IRM: відмічено крок 6.3.3 як завершений.
### Notes
- Джерело обсягу — REST тікери біржі; fallback на останній відомий обсяг з БД за відсутності свіжих даних.

`------------------------------------------------------------------------------------------------`

## [6.3.2] — 2025-08-25
**Phase 6 — Step-6.3.2 · DAO + retention + тести**
### Added
- DAO для `signals`, `quotes`, `meta` з типізацією і batch‑вставками.
- Індекси: `signals(symbol, ts)`, `quotes(symbol, ts)` — прискорення вибірок для алертів.
- Політика **retention** (ENV `SQLITE__RETENTION_DAYS`) + службовий job видалення старих записів.
### Changed
- Перехід з ad‑hoc INSERT на DAO‑шару; уніфікація інтерфейсу доступу до SQLite.
### Docs
- README: згадка про retention і місце розташування БД (`RUNTIME__DB_PATH`).
- CHANGELOG: цей запис; IRM: 6.3.2 відмічено як `done`.
### Notes
- WAL + `synchronous=NORMAL` для швидкого запису; VACUUM лишається у 6.3.6.

`------------------------------------------------------------------------------------------------`

## [6.3.1] — 2025-08-24
**Phase 6 — Step-6.3.1 · Схема SQLite (signals/quotes/meta)**
### Added
- Створено таблиці: **`signals`**, **`quotes`**, **`meta`** (ключі, індекси, обмеження).
- Міграція ініціалізації БД (idempotent) + утиліти створення/перевірки схеми.
### Docs
- README: первинний опис структури БД.
- CHANGELOG: цей запис; IRM 6.3.1 — `done`.
### Notes
- Схема проєктувалась під високочастотні вставки з мінімальною фрагментацією файлу.


`------------------------------------------------------------------------------------------------`

## [6.3.0] — 2025-09-04
**Phase 6 — Step-6.3.0 · SQLite persistence for alerts & signals**

### Added
- `infra/alerts_repo.py`: додано таблицю історії **`alerts_log`** (append-only), збережено **`alerts`** (останній алерт на символ для cooldown).
- `core/alerts_hook.py`: перехід на **persistent** `SqliteAlertGateRepo` (не `:memory:`) + новий wrapper `log_history()`.
- `core/alerts.py`: запис історії **після успішної відправки** у Telegram (`reason=sent`).
- Тести: `tests/test_alerts_repo_history.py`, `tests/test_alerts_history_integration.py`.

### Changed
- Стиль/сумісність: `get_last()` повертає `(ts_epoch, basis_pct) | None`; `set_last()` приймає `ts_epoch` **або** `ts` (бек-сумісність).

### Notes
- WAL + `synchronous=NORMAL` для БД алертів.
- Документація/ENV приклади оновлені (`ALERTS__DB_PATH`, `RUNTIME__DB_PATH`).

`------------------------------------------------------------------------------------------------`

## [6.2.7] — 2025-08-31
**Phase 6 — Step-6.2.7 · WS hardening (QS P0)**

### Added
- Unified exponential backoff with jitter in WS-layer (`src/ws/backoff.py`).

### Changed
- Removed duplicated backoff code from Bybit WS client — now uses shared WS backoff module (`src/exchanges/bybit/ws.py`).
- Typing pass (**mypy green**) for `src/ws/*` та `src/exchanges/bybit/ws.py`.
- Added jitter/backoff tests (`tests/test_ws_backoff_jitter.py`).

### Coverage
- WS package coverage **≥ 85%** (current ≈ 88%).

### IRM / CI
- IRM (SSOT-lite for 6.2) залишено без змін; крок 6.2.7 зафіксовано окремо в SSOT (див. `docs/irm.phase6.yaml`).
- `pre-commit` green.
[6.2.7]: https://github.com/VadymTeterin/bybit-arb-bot/compare/v6.2.5...v6.2.7

`------------------------------------------------------------------------------------------------`


## [6.2.5] — 2025-08-30
**Phase 6 — Step-6.2.5 · IRM sync + Repo Hygiene (docs-only)**

### Changed
- **IRM (Phase 6.2.5)** синхронізовано з SSOT: оновлено `docs/irm.phase6.yaml` та згенеровано `docs/IRM.md` (тільки генератором).
- Нормалізовано `.gitattributes` / `.gitignore` (LF для коду, CRLF для Windows-скриптів), узгоджено **pre-commit / Ruff / isort**.
- **Жодних змін у runtime-логіці.**

### Notes
- Канонічний SSOT: `docs/irm.phase6.yaml` (**UTF‑8, без BOM**). Дублікати на кшталт `docs/irm.phase6.6.2.5.yaml` — вилучені.
- Генерація IRM: `python .\tools\irm_phase6_gen.py --check|--write` (залежність: `pyyaml`).



> Статус: **в черзі до релізу**. Зміни не впливають на виконання коду — це документація та CI.

### Додано
- **Quality Standard (QS) v1.0** — `docs/QUALITY.md`, узгоджено з **Working Agreements v2.0**.
- **Definition of Done** — `docs/DoD.md`.
- **Testing Guide** — `docs/TESTING.md`.
- **План безпечного впровадження** — `docs/Plan_bezpechnogo_vprovadzhennya_po_etapakh.md`.
- **Шаблон Pull Request** — `.github/PULL_REQUEST_TEMPLATE.md`.
- Конфігурації інструментів якості на корені репозиторію:
  - `ruff.toml`, `isort.cfg`, `pre-commit-config.yaml`, `requirements-dev.txt`.

### Змінено
- **README.md** — додано розділ *Quality & Delivery Standards* з посиланнями на QS/DoD/Testing/Plan. (PR #40)

### CI
- Для подій **pull_request** `pre-commit` запускається **лише по змінених файлах** — швидше та без зайвого шуму.
- Для подій **push** лишається повний прогін `--all-files`.
- Файл змін: `.github/workflows/ci.yml`. (PR #39)

### Перевірка
1. `pip install -r requirements-dev.txt`
2. *(опціонально)* `pre-commit install`
3. `pre-commit run -a` — всі хуки мають пройти.
4. Відкрити `README.md` в `main` і перевірити, що лінки на QS/DoD/Testing/Plan працюють.

[6.2.5]: https://github.com/VadymTeterin/bybit-arb-bot/compare/v6.2.0...v6.2.5

`------------------------------------------------------------------------------------------------`


## [6.2.0] — 2025-08-24
**Phase 6 — Step-6.2.0 · WS Resilience & Health**

### Added
- **Парсер Bybit v5 `tickers`** (`src/exchanges/bybit/ws.py`): підтримка plain та `E4/E8` полів (`lastPriceE8/markPriceE4/...`), fallback символу з `topic`, стабільні ключі `symbol/last/mark/index`.
- **WS Multiplexer** (`src/ws/multiplexer.py`): *ледача відписка* (`unsubscribe()` вимикає доставку, але запис лишається до `clear_inactive()`), сумісний `stats()` для тестів.
- Каркас **health-метрик** (SPOT/LINEAR counters, uptime, last_event_ts) — база для `/status` у 6.2.1.
- Документація: `docs/WS_RESILIENCE.md` (короткий опис змін та семантики відписки).

### Tests
- Увесь набір `ws`-тестів зелений локально: **31 passed, 91 deselected**.

### Migration Notes
- API зовнішніх модулів не порушено. Для отримання метрик планується `/status` у 6.2.1.

[6.2.0]: https://github.com/VadymTeterin/bybit-arb-bot/compare/v6.1.1...v6.2.0

`------------------------------------------------------------------------------------------------`

## [6.1.1] — 2025-08-24

### Fixed
- Конфіги: визначений пріоритет для alerts — **flat (`ALERT_*`) > nested (`ALERTS__*`)**.
- Стиль: виправлено Ruff E402 (імпорт `lru_cache` на початку файлу).

### Changed
- Перезавантаження `.env` при кожному побудуванні конфігу (`autoload_env()` у білдері), що коректно враховує `ENV_FILE`.
- Єдина кеш-функція налаштувань: `load_settings = get_settings = _settings_cached`.

### Added
- `tests/test_config.py`: покриття nested env loading, flat overrides nested, пріоритет ENV над `.env`.

[6.1.1]: https://github.com/VadymTeterin/bybit-arb-bot/compare/v6.1.0...v6.1.1

`------------------------------------------------------------------------------------------------`


## [6.1.0] - 2025-08-23
**Phase 6 — Step-6.1.0 · Config Hardening на pydantic-settings v2** · PR #16

### Added
- Перехід на **pydantic-settings v2** з **nested-ключами** (роздільник `__`):
  - Секції: `runtime`, `telegram`, `bybit`, `alerts`, `liquidity`.
  - Кешований доступ `get_settings()` та детермінований `load_settings()`.
- **Валідації** полів конфігурації:
  - `ALERTS__THRESHOLD_PCT` ∈ [0..100], `ALERTS__COOLDOWN_SEC` ∈ [0..86400].
  - `LIQUIDITY__MIN_VOL_24H_USD` ≥ 0, `LIQUIDITY__MIN_PRICE` ≥ 0.
  - `RUNTIME__TOP_N_REPORT` ∈ [1..100].
- **Тестове покриття конфігів**: `tests/test_config.py` (nested/flat/validation).

### Changed
- Рефакторинг `src/infra/config.py` у стилі senior:
  - Хелпери для приведення типів (`_from_env_many*`, `_csv_list`), чіткі докстрінги.
  - Підтримка **legacy flat keys** з правилом: *flat overrides nested*.
  - WS-налаштування: узгодженість між top-level полями та `bybit.*` (теми можна задавати CSV або списком).
- `.env.example`: переписано — структуровані секції, безпечні дефолти, підказки з back-compat.

### Docs
- **README → Configuration**: детальний гайд по nested-ключах, таблиця відповідності legacy, приклади коду.

### Tests
- Увесь тестовий набір зелений локально: **117 passed, 1 skipped**.

### Migration Notes
- **Breaking changes — немає.** Усі legacy flat-ключі залишаються підтриманими.
- Рекомендовано поступово перейти на **nested**-ключі `SECTION__FIELD`.
- Якщо одночасно задані nested і flat — значення з flat мають пріоритет.

`------------------------------------------------------------------------------------------------`


### Versioning Notes
- До `6.1.0` використовувались pre-1.0 теги (`0.6.x`). Починаючи з `6.1.0`, мажор **6**
  синхронізовано з **Phase 6** IRM — це не ламає API; це узгодження з етапами розвитку.
- Використовуйте **Conventional Commits** та оновлюйте цей файл на кожен реліз.

`------------------------------------------------------------------------------------------------`

## [0.6.2] - 2025-08-22
### Added
- `GitHubClient`: автоматичні ретраї з бекофом для `429/5xx` та транзієнтних помилок (`httpx`),
  врахування `Retry-After` / `X-RateLimit-Reset` (з верхньою межею очікування).
- Юніт-тести на ретраї/бекоф та rate-limit поведінку.

### CI
- Додано відсутні залежності для тестів: `requests`, `pydantic-settings` (оновлено `requirements.txt`).

### Docs
- Оновлено README: розділи про Daily Digest та зауваги щодо ретраїв/лімітів.

### Release
- Тег `v0.6.2` та GitHub Release з нотатками.

`------------------------------------------------------------------------------------------------`

## [0.6.1] - 2025-08-22
### Added
- **Phase 6 — Step-6.0.4**: Windows Task Scheduler для щоденного **GitHub Daily Digest** (07:10 Europe/Kyiv).
  - Скрипти: `scripts/gh_digest_run.ps1`, `scripts/schedule_gh_digest.ps1`, `scripts/unschedule_gh_digest.ps1`.
  - Логи планувальника: `logs/gh_digest.YYYY-MM-DD.log`.

### Docs
- README: інструкції Manual — Schedule / Unschedule / Smoke-run.

`------------------------------------------------------------------------------------------------`

## [0.6.0] - 2025-08-22
### Added
- **Phase 6 — GitHub Daily Digest (база)**:
  - Клієнт GitHub API, моделі звіту, CLI-скелет.
  - Збір активності за «Kyiv-добу»: коміти, PR/мерджі, теги.
  - `.env`: `GH_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`; опція `--send` для Telegram.
  - Троттлінг: один digest на добу, `--force` для повторного запуску.

### Docs
- README: розділи Daily Digest, приклади запуску.

`------------------------------------------------------------------------------------------------`

## [0.5.8.4] - 2025-08-19
### Added
- WS-стабільність і моніторинг: керований бекоф (cap), health-метрики, `/status` у Telegram.
- **Supervisor** (однопроцесний): піднімає SPOT/LINEAR WS, Telegram-бота та meta-refresh;
  контролер `scripts/ws_supervisor_ctl.ps1`.

### Changed
- `.env` автозавантаження через `python-dotenv`; технічні деталі — `docs/WS_STABILITY.md`.

### Tooling
- pre-commit (ruff/format/isort), покриття тестами ключових підсистем.

`------------------------------------------------------------------------------------------------`

## [0.5.x] - 2025-08-14 .. 2025-08-16 (оглядово)
- WS Multiplexer + Bybit інтеграція; міст-шар `src/ws/bridge.py`, wildcard-підписки, статистики, відписки.
- Meta-refresh для `get_tickers('spot'|'linear')`; фічі Telegram-бота.
- Рефакторинг CLI та документації.

`------------------------------------------------------------------------------------------------`

## [0.4.x] - 2025-08-13 (оглядово)
- Парсинг та кеш оновлень з WS, розрахунок basis% у реальному часі, троттлінг алертів, авто-reconnect, healthcheck.

`------------------------------------------------------------------------------------------------`

## [0.3.x] - 2025-08-10 .. 2025-08-12 (оглядово)
- Фільтри ліквідності/глибини, **SQLite persistence**, базовий набір тестів, форматування коду.

`------------------------------------------------------------------------------------------------`

## [0.2.x] - 2025-08-09 .. 2025-08-10 (оглядово)
- Перший Bybit REST-клієнт і CLI-утиліти: `basis:scan`, `bybit:top`, `price:pair`, `basis:alert`.

`------------------------------------------------------------------------------------------------`

## [0.1.0] - 2025-08-09
- Старт проєкту: структура `src/`, `tests/`, конфіг і логування; вхідна точка `python -m src.main <command>`.

`------------------------------------------------------------------------------------------------`



