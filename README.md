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
- [CI: Digest E2E Smoke (Step-6.0.6)](#ci-digest-e2e-smoke-step-606)
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
```

## .env

> Змінні підхоплюються через **python-dotenv** в усіх раннерах (включно з супервізором та digest). Після змін — зробіть `restart`.

```env
# базові
WS_ENABLED=1
LOG_LEVEL=INFO

# Telegram (обовʼязково для /status і алертів)
TELEGRAM__BOT_TOKEN=123456:AA...
TELEGRAM__ALERT_CHAT_ID=123456789

# Bybit (не обовʼязково для публічних WS/REST)
BYBIT_API_KEY=
BYBIT_API_SECRET=

# --- GitHub Daily Digest ---
GH_TOKEN=
GITHUB_OWNER=VadymTeterin
GITHUB_REPO=bybit-arb-bot

# --- Telegram для Digest (CI notify) ---
TG_BOT_TOKEN=
TG_CHAT_ID=
```

---

## Запуск під супервізором

Контролер (PowerShell 5.1): `scripts/ws_supervisor_ctl.ps1`

```powershell
.\scripts\ws_supervisor_ctl.ps1 start
.\scripts\ws_supervisor_ctl.ps1 status
.\scripts\ws_supervisor_ctl.ps1 tail -TailLines 200
.\scripts\ws_supervisor_ctl.ps1 restart
.\scripts\ws_supervisor_ctl.ps1 stop
```

---

## Telegram `/status`

- Напишіть боту `/status` у чат, ID якого вказано у `TELEGRAM__ALERT_CHAT_ID`.
- Відповідь: JSON-знімок з метриками.

---

## Метрики WS

Клас: `src/ws/health.py` — потокобезпечний синглтон-реєстр.

---

## GitHub Daily Digest

**Що це:** зведення активності репозиторію (коміти, PR/мерджі, теги) за **«Kyiv-добу»** з можливістю відправки у Telegram.

**Надійність GitHub клієнта (v0.6.2):**
- Ретраї з експоненційним бекофом для `429/5xx` та тимчасових помилок мережі.
- Повага до заголовків **`Retry-After`** та **`X-RateLimit-Reset`** (із верхньою межею очікування).
- Юніт-тести покривають сценарії: `500→200`, `429 (Retry-After)`, `rate-limit reset`, «неретраємі» `4xx`.

### Приклади запуску

```powershell
# Mock + друк у консоль
python -m scripts.gh_daily_digest --mock --date 2025-08-22

# Реальний режим (GH_TOKEN обовʼязково в .env)
python -m scripts.gh_daily_digest --no-mock --owner VadymTeterin --repo bybit-arb-bot --date 2025-08-22

# Надсилання у Telegram (1 раз на добу; можна --force для повтору)
python -m scripts.gh_daily_digest --mock --date 2025-08-22 --send --force
```

### Особливості
- **Kyiv-доба**: 00:00–23:59 за Києвом, конвертовано у UTC.
- **Троттлінг**: один digest на день (мітки у `run/gh_digest.sent.*.stamp`).
- **.env**: використовує `GH_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`, а також `TG_BOT_TOKEN`, `TG_CHAT_ID`.

---

## Manual: Schedule / Unschedule

> **Мета:** автоматично відправляти GitHub Daily Digest щодня о **07:10 (Europe/Kyiv)** через Windows Task Scheduler.
> Скрипти: `scripts/gh_digest_run.ps1`, `scripts/schedule_gh_digest.ps1`, `scripts/unschedule_gh_digest.ps1`.

### Запланувати щоденний запуск
```powershell
# Регіструємо задачу BybitBot-GH-Digest (щодня 07:10 локального часу Windows; має бути Kyiv TZ)
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\schedule_gh_digest.ps1

# Перевіряємо, що задача зʼявилася
Get-ScheduledTask | Where-Object { $_.TaskName -like "BybitBot-GH-Digest" } | Format-Table TaskName,State,LastRunTime,NextRunTime

# Разово запустити вручну (smoke)
Start-ScheduledTask -TaskName "BybitBot-GH-Digest"
Get-Content .\logs\gh_digest.*.log -Tail 80
```

### Вимкнути планування
```powershell
# Видаляємо задачу з планувальника
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\unschedule_gh_digest.ps1

# Перевірка: має нічого не знайти
Get-ScheduledTask | Where-Object { $_.TaskName -like "BybitBot-GH-Digest" }
```

> ⚠️ Потрібні змінні `.env`: `GH_TOKEN` (для real-режиму), `TG_BOT_TOKEN`, `TG_CHAT_ID`.
> Один digest на **Kyiv-добу** (троттлінг через `run/gh_digest.sent.YYYY-MM-DD.stamp`). Для повтору використовуйте `--force`.

---

## CI: Digest E2E Smoke (Step-6.0.6)

**Що робить:** збирає псевдо-дайджест (`tools/digest_smoke.py`) і публікує як артефакт `digest-smoke-<run_id>`; опційно шле повідомлення в Telegram.

**Secrets (Repo → Settings → Secrets → Actions):**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

**Запуск у GitHub UI:**
- Actions → **Digest E2E Smoke** → **Run workflow** (обрати гілку).

**Запуск через gh CLI (PowerShell):**
```powershell
# Список воркфлоу
gh workflow list
# Ручний запуск на гілці
gh workflow run .github/workflows/digest-e2e-smoke.yml --ref step-6.0.6-digest-e2e
# Знайти RUN_ID workflow_dispatch
gh run list --workflow digest-e2e-smoke.yml --branch step-6.0.6-digest-e2e --event workflow_dispatch --limit 5
# Подивитись логи / скачати ZIP логів
gh run view <RUN_ID> --log
gh api "repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/runs/<RUN_ID>/logs" --output run_<RUN_ID>.zip
# Завантажити артефакт
gh run download <RUN_ID> -n "digest-smoke-<RUN_ID>" -D artifacts
```

---

## Що запускає супервізор

`scripts/ws_bot_supervisor.py` піднімає:
- **SPOT WS**, **LINEAR WS**
- **Telegram-бот**
- **Meta refresh**
- Повторні спроби через **бекоф**.

---

## Корисні CLI-команди

```powershell
pytest -q
pre-commit run -a
python -m src.main bybit:ping
python -m scripts.gh_daily_digest --mock --date 2025-08-22
```

---

## Логи

- Для планувальника: `logs/gh_digest.YYYY-MM-DD.log`
- Загальні: `logs/app.log`, `logs/supervisor.*.log`
- Для digest: stdout + мітки в `run/`.

---

## Тести

- Локально та в CI: ✅ **pre-commit** (ruff/format/isort) і ✅ **unit tests** (Digest, GitHubClient, core).

---

## Структура проєкту (скорочено)

```
scripts/
  ws_supervisor_ctl.ps1
  gh_daily_digest.py     # GitHub Daily Digest CLI

src/github/
  client.py              # GitHub API client (ретраї/бекоф, rate-limit guard)

src/reports/
  gh_digest.py           # моделі та агрегація Digest

tests/
  test_github_client_retry.py   # юніт-тести ретраїв GitHub клієнта
```

---

## Траблшутінг

- **Digest не відправляє у Telegram** — перевірте `TG_BOT_TOKEN` і `TG_CHAT_ID`.
- **Rate limit GitHub** — дочекайтесь reset; при необхідності зменште частоту.
- **Повторне відправлення Digest** — використовуйте `--force`.

---

## Ліцензія

MIT
