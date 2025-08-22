# CHANGELOG.md

> Усі суттєві зміни цього проєкту документуються тут. Дати у форматі **YYYY-MM-DD (Europe/Kyiv)**.
> Формат натхненний [Keep a Changelog](https://keepachangelog.com/) і принципом **SemVer-like тагів**.

---

## [0.6.2] - 2025-08-22
### Added
- **GitHubClient: автоматичні ретраї з бекофом** для `429` та `5xx`, а також для транзієнтних транспортних помилок (`httpx`).
- **Захист від ліміту GitHub:** враховується заголовок `Retry-After` і `X-RateLimit-Reset` (із верхньою межею очікування), щоб не «молотити» API.
- **Юніт-тести** на ретраї/бекоф та rate-limit поведінку (`tests/test_github_client_retry.py`).

### CI
- Додано відсутні залежності для тестів: **`requests`** та **`pydantic-settings`** (оновлено `requirements.txt`).

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
'@ | Set-Content -Encoding UTF8 CHANGELOG.md

# README.md
@'
# Bybit Arbitrage Bot — GitHub Daily Digest + WS Stability (v0.6.2)

> Windows 11 · Python 3.11+ · aiogram 3.7+ · Bybit Public WS/REST · GitHub API

Цей реліз додає **GitHub Daily Digest** та робить клієнт GitHub значно надійнішим завдяки **автоматичним ретраям з бекофом** і коректній обробці **rate-limit**. Також збережено фокус на **стабільності WebSocket**, **метриках здоровʼя** та сервісній команді **Telegram `/status`**.

---

## Зміст
- [Швидкий старт](#швидкий-старт)
- [.env](#env)
- [Запуск під супервізором](#запуск-під-супервізором)
- [Telegram `/status`](#telegram-status)
- [Метрики WS](#метрики-ws)
- [GitHub Daily Digest](#github-daily-digest)
- [Manual: Schedule / Unschedule](#manual-schedule--unschedule)
- [Що запускає супервізор](#що-запускає-супервізор)
- [Корисні CLI-команди](#корисні-cli-команди)
- [Логи](#логи)
- [Тести](#тести)
- [Структура проєкту (скорочено)](#структура-проєкту-скорочено)
- [Траблшутінг](#траблшутінг)
- [Ліцензія](#ліцензія)

---

## Швидкий старт

```powershell
git clone <your-repo-url> bybit-arb-bot
cd bybit-arb-bot

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
