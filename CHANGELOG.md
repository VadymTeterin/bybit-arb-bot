# Changelog

Усі суттєві зміни цього проєкту документуються тут. Формат — за принципами
**[Keep a Changelog](https://keepachangelog.com/uk-UA/1.1.0/)** та **SemVer**.
Дати наведені у форматі **YYYY-MM-DD (Europe/Kyiv)**.

> Примітка: у записах можуть згадуватись етапи розробки *Phase N / Step-N.X*,
> що відповідають нашому внутрішньому Implementation Roadmap (IRM).

---

## [Unreleased]

---

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

---
---

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

---

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

---

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

---

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

---

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

---

## [0.6.1] - 2025-08-22
### Added
- **Phase 6 — Step-6.0.4**: Windows Task Scheduler для щоденного **GitHub Daily Digest** (07:10 Europe/Kyiv).
  - Скрипти: `scripts/gh_digest_run.ps1`, `scripts/schedule_gh_digest.ps1`, `scripts/unschedule_gh_digest.ps1`.
  - Логи планувальника: `logs/gh_digest.YYYY-MM-DD.log`.

### Docs
- README: інструкції Manual — Schedule / Unschedule / Smoke-run.

---

## [0.6.0] - 2025-08-22
### Added
- **Phase 6 — GitHub Daily Digest (база)**:
  - Клієнт GitHub API, моделі звіту, CLI-скелет.
  - Збір активності за «Kyiv-добу»: коміти, PR/мерджі, теги.
  - `.env`: `GH_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`; опція `--send` для Telegram.
  - Троттлінг: один digest на добу, `--force` для повторного запуску.

### Docs
- README: розділи Daily Digest, приклади запуску.

---

## [0.5.8.4] - 2025-08-19
### Added
- WS-стабільність і моніторинг: керований бекоф (cap), health-метрики, `/status` у Telegram.
- **Supervisor** (однопроцесний): піднімає SPOT/LINEAR WS, Telegram-бота та meta-refresh;
  контролер `scripts/ws_supervisor_ctl.ps1`.

### Changed
- `.env` автозавантаження через `python-dotenv`; технічні деталі — `docs/WS_STABILITY.md`.

### Tooling
- pre-commit (ruff/format/isort), покриття тестами ключових підсистем.

---

## [0.5.x] - 2025-08-14 .. 2025-08-16 (оглядово)
- WS Multiplexer + Bybit інтеграція; міст-шар `src/ws/bridge.py`, wildcard-підписки, статистики, відписки.
- Meta-refresh для `get_tickers('spot'|'linear')`; фічі Telegram-бота.
- Рефакторинг CLI та документації.

---

## [0.4.x] - 2025-08-13 (оглядово)
- Парсинг та кеш оновлень з WS, розрахунок basis% у реальному часі, троттлінг алертів, авто-reconnect, healthcheck.

---

## [0.3.x] - 2025-08-10 .. 2025-08-12 (оглядово)
- Фільтри ліквідності/глибини, **SQLite persistence**, базовий набір тестів, форматування коду.

---

## [0.2.x] - 2025-08-09 .. 2025-08-10 (оглядово)
- Перший Bybit REST-клієнт і CLI-утиліти: `basis:scan`, `bybit:top`, `price:pair`, `basis:alert`.

---

## [0.1.0] - 2025-08-09
- Старт проєкту: структура `src/`, `tests/`, конфіг і логування; вхідна точка `python -m src.main <command>`.

---

### Versioning Notes
- До `6.1.0` використовувались pre-1.0 теги (`0.6.x`). Починаючи з `6.1.0`, мажор **6**
  синхронізовано з **Phase 6** IRM — це не ламає API; це узгодження з етапами розвитку.
- Використовуйте **Conventional Commits** та оновлюйте цей файл на кожен реліз.
