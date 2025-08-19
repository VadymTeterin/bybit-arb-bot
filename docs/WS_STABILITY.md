WS_STABILITY_MD
# WS Stability & Health — Гайд

Цей документ описує нові можливості моніторингу та стабілізації WS:
- `ws:health` — JSON-метрики у поточному процесі
- Telegram `/status` (aiogram v3) — аптайм і лічильники
- `scripts/ws_bot_runner.py` — один процес: WS + /status
- `scripts/ws_bot_supervisor.py` — те саме, але з **автоперезапуском** (експоненційний бекоф)
- Нові змінні середовища (ENV)

> **Примітка:** Метрики зберігаються **в памʼяті процесу**. Якщо читаєте їх з *іншого* процесу — побачите нулі (це очікувано).

---

## ⚡️ TL;DR (Quick Start)

1. Перевір `.env`:
   ```env
   WS_ENABLED=1
   TELEGRAM__BOT_TOKEN=your_bot_token_here
   # опційно — дозволити конкретний чат:
   TELEGRAM__ALERT_CHAT_ID=123456789
