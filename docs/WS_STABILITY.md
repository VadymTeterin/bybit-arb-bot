# WS Stability & Monitoring (Step 5.8.4)

Мета: стабільна робота WebSocket-стрімів (SPOT/LINEAR), нагляд за станом, метрики, та сервісний Telegram `/status`.

---

## Архітектура (ASCII)

```
+--------------------------------------------------------------+
|                   ws_bot_supervisor.py                       |
|--------------------------------------------------------------|
|  SPOT WS loop   |  LINEAR WS loop  |  Meta Refresh  |  Bot   |
|  (public/spot)  | (public/linear)  | (24h vol REST) | /status|
+-----------------+------------------+----------------+--------+
          |                 |                 |           |
          v                 v                 v           v
   Bybit WS (SPOT)   Bybit WS (LINEAR)   Bybit REST   Telegram API
          \_______________________  _______________________/
                                  \/
                      MetricsRegistry (src/ws/health.py)
                           counters: spot, linear
                           timestamps: last_spot/linear/event
                           uptime: started_ts -> now
```

---

## Backoff (без оверсуту)

```
delay = min(cap, base * 2^attempt) + jitter
attempts++ при кожному збої, скидається при успіху.
```

Реалізація: `src/ws/backoff.py`

---

## Метрики

- `MetricsRegistry.get()` — синглтон.
- Подієві лічильники: `inc_spot()`, `inc_linear()`.
- Знімок: `snapshot()` → dict (counters, timestamps, uptime).

CLI:

```powershell
python -m src.main ws:health
python -m src.main ws:health --reset
python -m scripts.ws_health_cli
```

---

## Telegram `/status`

- Модуль: `src/telegram/bot.py`
- Відповідь — JSON із:
  - `counters.spot`, `counters.linear`
  - `started_at_utc`, `uptime_ms`
  - `last_*_at_utc` / `last_*_ts`

**aiogram 3.7+** (використано `DefaultBotProperties`).

---

## Запуск

```powershell
# .env
WS_ENABLED=1
LOG_LEVEL=INFO
TELEGRAM__BOT_TOKEN=...
TELEGRAM__ALERT_CHAT_ID=...

# керування
.\scripts\ws_supervisor_ctl.ps1 start
.\scripts\ws_supervisor_ctl.ps1 status
.\scripts\ws_supervisor_ctl.ps1 tail -TailLines 200
.\scripts\ws_supervisor_ctl.ps1 restart
.\scripts\ws_supervisor_ctl.ps1 stop
```

---

## Логи

- `logs/app.log`
- `logs/supervisor.stdout.log`, `logs/supervisor.stderr.log` (console-режим)

Налаштування шуму:

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

## FAQ

**Чому `/status` інколи не відповідає?**
Тимчасові мережеві збої Telegram або обмеження polling. Супервізор робить ретраї з бекофом.

**Чому `ws:health` з іншого терміналу показує нулі?**
Метрики процесно-локальні. Для зовнішньої агрегації додамо експортер (SQLite/Prometheus) у наступних ітераціях.
