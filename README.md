# Bybit Arbitrage Bot — WS Stability, Health & Telegram `/status` (Step 5.8.4)

> Windows 11 · Python 3.11+ · aiogram 3.7+ · Bybit Public WS/REST

Цей реліз фокусується на **стабільності WebSocket**, **метриках здоровʼя**, сервісній команді **Telegram `/status`** та **зручному запуску під супервізором** на Windows.
У **Фазі 6** додано модуль **GitHub Daily Digest** з інтеграцією у Telegram.

---

## Зміст
- [Швидкий старт](#швидкий-старт)
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
```

### .env (корінь репозиторію)

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

# --- Telegram для Digest ---
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


---

## Manual: Schedule / Unschedule

> **Мета:** автоматично відправляти GitHub Daily Digest щодня о **07:10 (Europe/Kyiv)** через Windows Task Scheduler.
> Скрипти: `scripts/gh_digest_run.ps1`, `scripts/schedule_gh_digest.ps1`, `scripts/unschedule_gh_digest.ps1`.

### Запланувати щоденний запуск
```powershell
# Регіструємо задачу BybitBot-GH-Digest (щодня 07:10 локального часу Windows; має бути Kyiv TZ)
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\schedule_gh_digest.ps1

# Перевірити, що задача є
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

> ⚠️ Потрібні змінні `.env`: `GH_TOKEN` (для real‑режиму), `TG_BOT_TOKEN`, `TG_CHAT_ID`.
> Один digest на **Kyiv‑добу** (троттлінг через `run/gh_digest.sent.YYYY-MM-DD.stamp`). Для повтору використовуйте `--force` в CLI.


Функціонал Step-6.0.x: збір активності репозиторію (коміти, PR, теги) за “Kyiv-добу” з можливістю відправки у Telegram.

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

## Що запускає супервізор

`scripts/ws_bot_supervisor.py` піднімає:
- **SPOT WS**, **LINEAR WS**
- **Telegram бот**
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

- `logs/app.log`
- `logs/supervisor.*.log`
- Для digest: стандартний stdout + мітки в `run/`.

---

## Тести (стан на 2025-08-22)

```
110 passed
```

---

## Структура проєкту (скорочено)

```
scripts/
  ws_supervisor_ctl.ps1
  gh_daily_digest.py     # GitHub Daily Digest CLI

src/github/
  client.py              # GitHub API client

src/reports/
  gh_digest.py           # моделі та агрегація Digest
```

---

## Траблшутінг

- **Digest не відправляє у Telegram** — перевірте `TG_BOT_TOKEN` і `TG_CHAT_ID`.
- **Rate limit GitHub** — дочекайтесь reset, зменште частоту.
- **Повторне відправлення Digest** — використовуйте `--force`.

---

## Ліцензія

MIT
