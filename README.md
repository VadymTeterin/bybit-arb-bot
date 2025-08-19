# Bybit Arbitrage Bot — WS Stability, Health & Telegram `/status` (Step 5.8.4)

> Windows 11 · Python 3.11+ · aiogram 3.7+ · Bybit Public WS/REST

Цей реліз фокусується на **стабільності WebSocket**, **метриках здоровʼя**, сервісній команді **Telegram `/status`** та **зручному запуску під супервізором** на Windows.

---

## Зміст
- [Швидкий старт](#швидкий-старт)
- [Запуск під супервізором](#запуск-під-супервізором)
- [Telegram `/status`](#telegram-status)
- [Метрики WS](#метрики-ws)
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

> Змінні підхоплюються через **python-dotenv** в усіх раннерах (включно з супервізором). Після змін — зробіть `restart`.

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
```

Перевірити, що процес бачить змінні:

```powershell
python -c "import os; print('TOKEN set:', bool(os.getenv('TELEGRAM__BOT_TOKEN'))); print('CHAT_ID:', os.getenv('TELEGRAM__ALERT_CHAT_ID'))"
```

---

## Запуск під супервізором

Контролер (PowerShell 5.1): `scripts/ws_supervisor_ctl.ps1`

```powershell
.\scripts\ws_supervisor_ctl.ps1 start         # console-режим (python.exe) з редиректом у logs/
.\scripts\ws_supervisor_ctl.ps1 status        # PID + останній лог
.\scripts\ws_supervisor_ctl.ps1 tail -TailLines 200   # “tail -f”
.\scripts\ws_supervisor_ctl.ps1 restart       # перезапуск (підхопить новий .env)
.\scripts\ws_supervisor_ctl.ps1 stop          # зупинка
```

> За замовчуванням — **console-режим** з файлами `logs/supervisor.stdout.log`/`logs/supervisor.stderr.log`.
> Windowless — `start -NoConsole` / `restart -NoConsole` (менш зручний для дебагу).

Альтернатива:

```powershell
python -m scripts.ws_bot_supervisor
```

---

## Telegram `/status`

- Напишіть боту `/status` у чат, ID якого вказано у `TELEGRAM__ALERT_CHAT_ID`.
- Відповідь: JSON-знімок (лічильники `spot`/`linear`, `started_at_utc`, `uptime_ms`, timestamps останніх подій).
- **aiogram 3.7+**: використовується `DefaultBotProperties` замість застарілого `parse_mode` у конструкторі.

---

## Метрики WS

Клас: `src/ws/health.py` — потокобезпечний синглтон-реєстр:

- Лічильники подій: `spot`, `linear`.
- Мітки часу останніх подій (per-type і загальна).
- Аптайм (`started_ts`, `uptime_ms`).

Знімки:

```powershell
python -m src.main ws:health
python -m src.main ws:health --reset
python -m scripts.ws_health_cli
```

> Якщо викликаєте з **іншого процесу**, лічильники можуть бути нульові — це очікувано (процесно-локальні метрики).

---

## Що запускає супервізор

`scripts/ws_bot_supervisor.py` піднімає:

- **SPOT WS** — `wss://stream.bybit.com/v5/public/spot`
- **LINEAR WS** — `wss://stream.bybit.com/v5/public/linear`
- **Telegram бот** — відповідає на `/status`
- **Meta refresh** — періодичне оновлення `24h vol` для фільтрів (REST)
- Повторні спроби через **експоненційний бекоф** (без оверсуту) з `src/ws/backoff.py`

---

## Корисні CLI-команди

```powershell
# Пінг Bybit (серверний час)
python -m src.main bybit:ping

# Превʼю форматування алерту
python -m src.main alerts:preview --symbol BTCUSDT --spot 50000 --mark 50500 --threshold 1.0

# Тести та автоформат
pytest -q
pre-commit run -a
```

---

## Логи

- `logs/app.log` — основний лог застосунку (`loguru`).
- У режимі супервізора (console):
  - `logs/supervisor.stdout.log`
  - `logs/supervisor.stderr.log`

Зменшення шуму:

```env
LOG_LEVEL=INFO
WS_DEBUG_NORMALIZED=0
WS_DEBUG_SAMPLE_MS=3000
```

---

## Тести (стан на 2025-08-19)

```
107 passed, 1 skipped
```

---

## Структура проєкту (скорочено)

```
scripts/
  ws_bot_supervisor.py     # супервізор: WS + Telegram + meta-refresh (1 процес)
  ws_health_cli.py         # тимчасовий CLI для метрик
  ws_supervisor_ctl.ps1    # PowerShell-контролер start/stop/status/restart/tail

src/ws/
  backoff.py               # експоненційний бекоф (cap, no-overshoot)
  health.py                # метрики WS (синглтон)

src/telegram/
  bot.py                   # /status
```

---

## Траблшутінг

- **`TelegramNetworkError: Server disconnected`** — супервізор зробить ретраї з бекофом. Якщо часто — перевірте інтернет/фаєрвол та рівень логів.
- **Бот не відповідає на `/status`** — перевірте `TELEGRAM__BOT_TOKEN` та `TELEGRAM__ALERT_CHAT_ID` у `.env`, далі `restart`, подивіться `supervisor.stderr.log`.
- **`pythonw.exe` завершується одразу** — використовуйте console-режим (`start` без `-NoConsole`) для видимих логів.

---

## Ліцензія

MIT
