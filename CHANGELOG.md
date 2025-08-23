# CHANGELOG.md

> Усі суттєві зміни цього проєкту документуються тут. Дати у форматі **YYYY-MM-DD (Europe/Kyiv)**.
> Формат натхненний Keep a Changelog і принципом **SemVer-like тагів**.

---

## [Unreleased]
### Added
- **Step-6.0.6 — Digest E2E smoke (CI):** додано workflow `.github/workflows/digest-e2e-smoke.yml`, який збирає артефакт `digest-smoke-<run_id>` з псевдо-дайджестом (`.md` + `.json`).
- **Reusable notify:** новий файл `.github/workflows/_notify-telegram.yml`; нотифікація в Telegram виконується тільки за наявності `TELEGRAM_BOT_TOKEN` і `TELEGRAM_CHAT_ID` (перевірка на рівні step).

### Docs
- **README.md:** додано розділ “CI: Digest E2E Smoke (Step-6.0.6)” з інструкціями запуску (UI/gh), секретами та артефактами.

---

## [0.6.2] - 2025-08-22
### Added
- **GitHubClient: автоматичні ретраї з бекофом** для `429` та `5xx`, а також для транзієнтних транспортних помилок (`httpx`).
- **Захист від ліміту GitHub:** враховується `Retry-After` і `X-RateLimit-Reset` (із верхньою межею очікування).
- **Юніт-тести** на ретраї/бекоф та rate-limit поведінку (`tests/test_github_client_retry.py`).

### CI
- Додано відсутні залежності для тестів: `requests` та `pydantic-settings` (оновлено `requirements.txt`).

### Docs
- Оновлено **README.md**: розділи про GitHub Daily Digest та зауваги щодо ретраїв/лімітів.

### Release
- Тег: `v0.6.2` і GitHub Release з нотатками.

---

## [0.6.1] - 2025-08-22
### Added
- **Step-6.0.4 — Windows Task Scheduler** для щоденного **GitHub Daily Digest** (о 07:10 Europe/Kyiv).
  - Скрипти: `scripts/gh_digest_run.ps1`, `scripts/schedule_gh_digest.ps1`, `scripts/unschedule_gh_digest.ps1`.
  - Логи планувальника: `logs/gh_digest.YYYY-MM-DD.log`.

### Docs
- **README.md**: інструкції **Manual: Schedule / Unschedule** (smoke-run, перевірка, видалення задачі).

---

## [0.6.0] - 2025-08-22
### Added
- **Phase 6 — GitHub Daily Digest (базовий функціонал)**
  - Клієнт GitHub API, моделі звіту та CLI-скелет.
  - Збір активності репозиторію за «Kyiv-добу»: коміти, PR/мерджі, теги.
  - `.env`: `GH_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`; інтеграція з Telegram (`TG_BOT_TOKEN`, `TG_CHAT_ID`), опція `--send`.
  - Троттлінг — **один digest на добу**, флаг `--force` для повтору.

### Docs
- Додано розділи про Daily Digest у README, приклади запуску.

---

## [0.5.8.4] - 2025-08-19
### Added
- **WS стабільність та моніторинг**: керований бекоф (cap, без «перестрибувань»), health-метрики, Telegram-команда `/status`.
- **Supervisor** (однопроцесний): піднімає SPOT/LINEAR WS, Telegram-бот і meta-refresh; PowerShell-контролер `scripts/ws_supervisor_ctl.ps1`.

### Changed
- `.env` автозавантаження через `python-dotenv`; документація у `docs/WS_STABILITY.md`.

### Tests/Tooling
- Pre-commit (ruff/format/isort), покриття тестами основних підсистем.

---

## [0.5.x] - 2025-08-14 .. 2025-08-16 (оглядово)
- **WS Multiplexer + Bybit інтеграція**, міст-шар (`src/ws/bridge.py`), wildcard-підписки, статистики та відписки.
- **Meta refresh** для `get_tickers('spot'|'linear')`, фічи Telegram-бота.
- Рефакторинг CLI та документації.

---

## [0.4.x] - 2025-08-13 (оглядово)
- Парсинг та кеш оновлень із WS, розрахунок basis% у реальному часі, троттлінг алертів, авто-reconnect та healthcheck.

---

## [0.3.x] - 2025-08-10 .. 2025-08-12 (оглядово)
- Фільтри ліквідності/глибини, **SQLite persistence**, базовий набір тестів, форматування коду.

---

## [0.2.x] - 2025-08-09 .. 2025-08-10 (оглядово)
- Перший Bybit REST-клієнт і CLI-утиліти (`basis:scan`, `bybit:top`, `price:pair`, `basis:alert`).

---

## [0.1.0] - 2025-08-09
- Старт проєкту: структура `src/`, `tests/`, конфіг і логування, вхідна точка `python -m src.main <command>`.
