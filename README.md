# Bybit Arbitrage Bot

## Quality & Delivery Standards

This project follows **QS v1.0** aligned with **Working Agreements v2.0**.

- **Quality Standard (QS v1.0):** see [docs/QUALITY.md](docs/QUALITY.md)
- **Definition of Done:** see [docs/DoD.md](docs/DoD.md)
- **Testing Guide:** see [docs/TESTING.md](docs/TESTING.md)
- **Safe Rollout Plan:** see [docs/Plan_bezpechnogo_vprovadzhennya_po_etapakh.md](docs/Plan_bezpechnogo_vprovadzhennya_po_etapakh.md)

> Tooling: `ruff.toml`, `isort.cfg`, `pre-commit-config.yaml`, `requirements-dev.txt` (at repo root).


[![Digest E2E Smoke](https://github.com/VadymTeterin/bybit-arb-bot/actions/workflows/digest-e2e-smoke.yml/badge.svg?branch=main)](https://github.com/VadymTeterin/bybit-arb-bot/actions/workflows/digest-e2e-smoke.yml)

> Windows 11 В· Python 3.11+ В· aiogram 3 В· Bybit REST & WebSocket v5 В· pydantic-settings v2

**РњРµС‚Р°:** Telegram-Р±РѕС‚, С‰Рѕ РІ СЂРµР°Р»СЊРЅРѕРјСѓ С‡Р°СЃС– Р°РЅР°Р»С–Р·СѓС” Р±Р°Р·РёСЃ РјС–Р¶ **Spot** С‚Р° **USDT-РїРµСЂРїРµС‚СѓР°Р»Р°РјРё** РЅР° Bybit, РІС–РґР±РёСЂР°С” **С‚РѕРї-3** РјРѕРЅРµС‚Рё Р·Р° РїРѕСЂРѕРіРѕРј (Р·Р° Р·Р°РјРѕРІС‡СѓРІР°РЅРЅСЏРј **1%**), Р·Р°СЃС‚РѕСЃРѕРІСѓС” С„С–Р»СЊС‚СЂРё Р»С–РєРІС–РґРЅРѕСЃС‚С–, Р·Р±РµСЂС–РіР°С” С–СЃС‚РѕСЂС–СЋ С‚Р° РЅР°РґСЃРёР»Р°С” Р°Р»РµСЂС‚Рё Сѓ Telegram Р· С‚СЂРѕС‚С‚Р»С–РЅРіРѕРј.

---

## Р—РјС–СЃС‚
- [РћСЃРѕР±Р»РёРІРѕСЃС‚С–](#РѕСЃРѕР±Р»РёРІРѕСЃС‚С–)
- [WS Resilience (6.2.0)](#ws-resilience-620)
- [Alerts (6.3.x)](#alerts-63x)
- [Р’РёРјРѕРіРё](#РІРёРјРѕРіРё)
- [РЁРІРёРґРєРёР№ СЃС‚Р°СЂС‚ (PowerShell)](#С€РІРёРґРєРёР№-СЃС‚Р°СЂС‚-powershell)
- [РљРѕРЅС„С–РіСѓСЂР°С†С–СЏ](#РєРѕРЅС„С–РіСѓСЂР°С†С–СЏ)
  - [Nested РєР»СЋС‡С– (СЂРµРєРѕРјРµРЅРґРѕРІР°РЅРѕ)](#nested-РєР»СЋС‡С–-СЂРµРєРѕРјРµРЅРґРѕРІР°РЅРѕ)
  - [РЎСѓРјС–СЃРЅС–СЃС‚СЊ Р·С– СЃС‚Р°СЂРёРјРё flat-РєР»СЋС‡Р°РјРё](#СЃСѓРјС–СЃРЅС–СЃС‚СЊ-Р·С–-СЃС‚Р°СЂРёРјРё-flat-РєР»СЋС‡Р°РјРё)
  - [РњС–РєСЂРѕР±Р»РѕРє: РџСЂС–РѕСЂРёС‚РµС‚ РєР»СЋС‡С–РІ РґР»СЏ alerts](#РјС–РєСЂРѕР±Р»РѕРє-РїСЂС–РѕСЂРёС‚РµС‚-РєР»СЋС‡С–РІ-РґР»СЏ-alerts)
  - [РџСЂРѕРіСЂР°РјРЅРёР№ РґРѕСЃС‚СѓРї](#РїСЂРѕРіСЂР°РјРЅРёР№-РґРѕСЃС‚СѓРї)
- [Р—Р°РїСѓСЃРє](#Р·Р°РїСѓСЃРє)
  - [CLI (Р»РѕРєР°Р»СЊРЅРёР№ smoke)](#cli-Р»РѕРєР°Р»СЊРЅРёР№-smoke)
  - [РџС–Рґ СЃСѓРїРµСЂРІС–Р·РѕСЂРѕРј](#РїС–Рґ-СЃСѓРїРµСЂРІС–Р·РѕСЂРѕРј)
  - [Telegram-РєРѕРјР°РЅРґРё](#telegram-РєРѕРјР°РЅРґРё)
- [РўРµСЃС‚Рё С‚Р° СЏРєС–СЃС‚СЊ РєРѕРґСѓ](#С‚РµСЃС‚Рё-С‚Р°-СЏРєС–СЃС‚СЊ-РєРѕРґСѓ)
- [РЎС‚СЂСѓРєС‚СѓСЂР° РїСЂРѕС”РєС‚Сѓ](#СЃС‚СЂСѓРєС‚СѓСЂР°-РїСЂРѕС”РєС‚Сѓ)
- [CI/CD](#cicd)
- [Р”РѕРєСѓРјРµРЅС‚Р°С†С–СЏ](#РґРѕРєСѓРјРµРЅС‚Р°С†С–СЏ)
- [РўСЂР°Р±Р»С€СѓС‚С–РЅРі](#С‚СЂР°Р±Р»С€СѓС‚С–РЅРі)
- [Р›С–С†РµРЅР·С–СЏ](#Р»С–С†РµРЅР·С–СЏ)

---

## РћСЃРѕР±Р»РёРІРѕСЃС‚С–

- вљЎ **WS-СЃС‚СЂС–РјРё** Bybit v5 (spot + linear) С–Р· Р°РІС‚РѕРїРµСЂРµРїС–РґРєР»СЋС‡РµРЅРЅСЏРј С– С‚СЂРѕС‚С‚Р»С–РЅРіРѕРј Р°Р»РµСЂС‚С–РІ
- рџ§® **Basis%** РјС–Р¶ spot С– С„вЂ™СЋС‡РµСЂСЃР°РјРё, **Top-3** РјРѕРЅРµС‚Рё РїРѕРЅР°Рґ РїРѕСЂС–Рі
- рџ’§ **Р¤С–Р»СЊС‚СЂРё Р»С–РєРІС–РґРЅРѕСЃС‚С–**: 24h РѕР±СЃСЏРі (USD), РјС–РЅС–РјР°Р»СЊРЅР° С†С–РЅР°
- рџ“Ё **Telegram-Р°Р»РµСЂС‚Рё** Р· С„РѕСЂРјР°С‚СѓРІР°РЅРЅСЏРј, Р°РЅС‚РёСЃРїР°Рј (**cooldown** РЅР° РјРѕРЅРµС‚Сѓ)
- рџ§± **pydantic-settings v2**: РІР°Р»С–РґРѕРІР°РЅС– СЃРµРєС†С–С— РєРѕРЅС„С–РіСѓСЂР°С†С–С— + **back-compat** Р·С– СЃС‚Р°СЂРёРјРё РєР»СЋС‡Р°РјРё
- рџ—„пёЏ **SQLite / Parquet** РґР»СЏ С–СЃС‚РѕСЂС–С— (СЃРёРіРЅР°Р»Рё, РєРѕС‚РёСЂСѓРІР°РЅРЅСЏ) + **РїРµСЂСЃРёСЃС‚ СЃС‚Р°РЅСѓ AlertGate** (6.3.5)
- рџ§Є **pytest** + **ruff/black/isort/mypy** С‡РµСЂРµР· **pre-commit**
- рџ”§ Windows-РѕСЂС–С”РЅС‚РѕРІР°РЅРёР№ DX: С–РЅСЃС‚СЂСѓРєС†С–С— Р»РёС€Рµ РґР»СЏ **PowerShell / VS Code вЂњРўРµСЂРјС–РЅР°Р»вЂќ**

---

## WS Resilience (6.2.0)

РџРѕРєСЂР°С‰РµРЅРЅСЏ СЃС‚Р°Р±С–Р»СЊРЅРѕСЃС‚С– WS-С€Р°СЂСѓ С‚Р° РјРµС‚СЂРёРє (Step **6.2.0**):

- **РџР°СЂСЃРµСЂ Bybit `tickers`**: РїС–РґС‚СЂРёРјРєР° plain-РїРѕР»С–РІ С‚Р° `E4/E8` (РЅР°РїСЂ. `lastPriceE8`), fallback СЃРёРјРІРѕР»Сѓ Р· `topic`, СЃС‚Р°Р±С–Р»СЊРЅС– РєР»СЋС‡С– `symbol/last/mark/index`. Р¤Р°Р№Р»: `src/exchanges/bybit/ws.py`.
- **WS Multiplexer**: *Р»РµРґР°С‡Р° РІС–РґРїРёСЃРєР°* (`unsubscribe()` РІРёРјРёРєР°С” РґРѕСЃС‚Р°РІРєСѓ, Р°Р»Рµ Р·Р°РїРёСЃ Р·Р±РµСЂС–РіР°С”С‚СЊСЃСЏ РґРѕ `clear_inactive()`), СЃСѓРјС–СЃРЅРёР№ `stats()`; С„Р°Р№Р»: `src/ws/multiplexer.py`.
- **РљР°СЂРєР°СЃ health-РјРµС‚СЂРёРє** (SPOT/LINEAR counters, uptime, last_event_ts) вЂ” РіРѕС‚РѕРІРѕ РґР»СЏ `/status` Сѓ 6.2.1.

Р”РµС‚Р°Р»С–: РґРёРІ. **docs/WS_RESILIENCE.md**.

---

## Alerts (6.3.x)

**6.3.4 вЂ” РџСЂРёРіР»СѓС€РµРЅРЅСЏ РјР°Р№Р¶Рµ-РґСѓР±Р»С–РєР°С‚С–РІ + cooldown:**
РџСЂРё РїРѕРІС‚РѕСЂРЅРёС… Р°Р»РµСЂС‚Р°С… РїРѕ С‚РѕРјСѓ СЃР°РјРѕРјСѓ СЃРёРјРІРѕР»Сѓ РїСЂРѕС‚СЏРіРѕРј `cooldown` РјРё РїСЂРёРіР»СѓС€СѓС”РјРѕ РїРѕРІС–РґРѕРјР»РµРЅРЅСЏ,
СЏРєС‰Рѕ Р·РјС–РЅР° Р±Р°Р·РёСЃСѓ РјРµРЅС€Р° Р·Р° `SUPPRESS_EPS_PCT` (Сѓ РІС–РґСЃРѕС‚РєРѕРІРёС… РїСѓРЅРєС‚Р°С…) РїСЂРѕС‚СЏРіРѕРј РІС–РєРЅР° `SUPPRESS_WINDOW_MIN`.
РџСЂРёРіР»СѓС€РµРЅРЅСЏ Р°РєС‚РёРІРЅРµ **Р»РёС€Рµ РїС–Рґ С‡Р°СЃ РґС–С— cooldown**.

**6.3.5 вЂ” РџРµСЂСЃРёСЃС‚ СЃС‚Р°РЅСѓ РіРµР№С‚Р° Сѓ SQLite:**
Р—Р°РїРёСЃСѓС”РјРѕ РѕСЃС‚Р°РЅРЅС–Р№ РЅР°РґС–СЃР»Р°РЅРёР№ СЃРёРіРЅР°Р» (С‡Р°СЃ + basis) Сѓ `alerts.db` вЂ” Р·Р°РІРґСЏРєРё С†СЊРѕРјСѓ
С‚СЂРѕС‚С‚Р»С–РЅРі С– РїСЂРёРіР»СѓС€РµРЅРЅСЏ РІРёР¶РёРІР°СЋС‚СЊ РїС–СЃР»СЏ СЂРµСЃС‚Р°СЂС‚С–РІ. SQLite РІС–РґРєСЂРёРІР°С”РјРѕ РІ WAL-СЂРµР¶РёРјС–.

**Telegram Chat Label (ENV-РїСЂРµС„С–РєСЃ):**
РЇРєС‰Рѕ Р·Р°РґР°РЅРѕ `TELEGRAM__LABEL`, Сѓ РїРѕРІС–РґРѕРјР»РµРЅРЅСЏС… Telegram РґРѕРґР°С”С‚СЊСЃСЏ РїСЂРµС„С–РєСЃ `"LABEL | ..."`. Р—СЂСѓС‡РЅРѕ РґР»СЏ `DEV`/`STAGE`.

---

## Р’РёРјРѕРіРё

- Windows 11
- Python **3.11+**
- Р†РЅС‚РµСЂРЅРµС‚ (Wi-Fi РґРѕ 1 Р“Р±С–С‚, СЂРѕСѓС‚РµСЂ Archer A64 вЂ” РѕРє)
- РўРѕРєРµРЅРё: **Telegram Bot Token**, **Telegram Chat ID**
- (РћРїС†.) **Bybit API Key/Secret** РґР»СЏ РїСЂРёРІР°С‚РЅРёС… РјРµС‚РѕРґС–РІ; РїСѓР±Р»С–С‡РЅС– WS/REST РїСЂР°С†СЋСЋС‚СЊ С– Р±РµР· РЅРёС…

---

## РЁРІРёРґРєРёР№ СЃС‚Р°СЂС‚ (PowerShell)

```powershell
# 1) РљР»РѕРЅ СЂРµРїРѕР·РёС‚РѕСЂС–СЋ
git clone https://github.com/VadymTeterin/bybit-arb-bot.git
cd bybit-arb-bot

# 2) Р’С–СЂС‚СѓР°Р»СЊРЅРµ СЃРµСЂРµРґРѕРІРёС‰Рµ
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Р—Р°Р»РµР¶РЅРѕСЃС‚С–
pip install -r requirements.txt

# 4) РљРѕРЅС„С–Рі
Copy-Item .\.env.example .\.env
# Р·Р°РїРѕРІРЅС–С‚СЊ TELEGRAM__TOKEN, TELEGRAM__CHAT_ID, (РѕРїС†.) BYBIT__API_KEY/SECRET

# 5) РџРµСЂРµРІС–СЂРєР°
pytest -q
pre-commit run -a
```

> **Р‘РµР·РїРµРєР°:** РЅС–РєРѕР»Рё РЅРµ РєРѕРјС–С‚СЊС‚Рµ `.env`. Р¤Р°Р№Р» СѓР¶Рµ Сѓ `.gitignore`.

---

## РљРѕРЅС„С–РіСѓСЂР°С†С–СЏ

Р›РѕР°РґРµСЂ: `src/infra/config.py` (**pydantic-settings v2**, СЂРѕР·РґС–Р»СЊРЅРёРє **`__`**).
РџСЂС–РѕСЂРёС‚РµС‚: **Environment** в†’ **.env** в†’ **РґРµС„РѕР»С‚Рё РІ РєРѕРґС–**.

### Nested РєР»СЋС‡С– (СЂРµРєРѕРјРµРЅРґРѕРІР°РЅРѕ)

```env
RUNTIME__ENV=dev
RUNTIME__ENABLE_ALERTS=true
RUNTIME__DB_PATH=./data/signals.db
RUNTIME__TOP_N_REPORT=10

TELEGRAM__TOKEN=
TELEGRAM__CHAT_ID=
TELEGRAM__LABEL=

BYBIT__API_KEY=
BYBIT__API_SECRET=

ALERTS__THRESHOLD_PCT=1.0        # 0..100
ALERTS__COOLDOWN_SEC=300         # 0..86400
ALERTS__SUPPRESS_EPS_PCT=0.2     # epsilon Сѓ РІС–РґСЃРѕС‚РєРѕРІРёС… РїСѓРЅРєС‚Р°С…
ALERTS__SUPPRESS_WINDOW_MIN=15   # С…РІРёР»РёРЅРЅРµ РІС–РєРЅРѕ РґР»СЏ epsilon
ALERTS__DB_PATH=./data/alerts.db # С€Р»СЏС… РґРѕ SQLite РґР»СЏ РіРµР№С‚Р°
# (РїР»Р°РЅСѓС”С‚СЊСЃСЏ) ALERTS__KEEP_DAYS=7

LIQUIDITY__MIN_VOL_24H_USD=10000000
LIQUIDITY__MIN_PRICE=0.001
```

### РЎСѓРјС–СЃРЅС–СЃС‚СЊ Р·С– СЃС‚Р°СЂРёРјРё flat-РєР»СЋС‡Р°РјРё

РЈСЃС– legacy-РєР»СЋС‡С– **РїС–РґС‚СЂРёРјСѓСЋС‚СЊСЃСЏ**. РЇРєС‰Рѕ Р·Р°РґР°РЅРѕ С– nested, С– flat вЂ” **flat РїРµСЂРµРІР°Р¶Р°С”**.

| Nested (recommended)                        | Legacy (supported)                                          |
|---------------------------------------------|-------------------------------------------------------------|
| `RUNTIME__ENV`                              | `ENV`                                                       |
| `RUNTIME__DB_PATH`                          | `DB_PATH`                                                   |
| `RUNTIME__TOP_N_REPORT`                     | `TOP_N_REPORT`                                              |
| `RUNTIME__ENABLE_ALERTS`                    | `ENABLE_ALERTS`                                             |
| `TELEGRAM__TOKEN`                           | `TELEGRAM_TOKEN`, `TELEGRAM_BOT_TOKEN`                      |
| `TELEGRAM__CHAT_ID`                         | `TELEGRAM_CHAT_ID`, `TG_CHAT_ID`, `TELEGRAM_ALERT_CHAT_ID`  |
| `TELEGRAM__LABEL`                           | `TELEGRAM_LABEL`, `TG_LABEL`, `ALERT_CHAT_LABEL`            |
| `BYBIT__API_KEY`                            | `BYBIT_API_KEY`                                             |
| `BYBIT__API_SECRET`                         | `BYBIT_API_SECRET`                                          |
| `ALERTS__THRESHOLD_PCT`                     | `ALERT_THRESHOLD_PCT`                                       |
| `ALERTS__COOLDOWN_SEC`                      | `ALERT_COOLDOWN_SEC`                                        |
| `ALERTS__SUPPRESS_EPS_PCT`                  | `ALERTS_SUPPRESS_EPS_PCT`                                   |
| `ALERTS__SUPPRESS_WINDOW_MIN`               | `ALERTS_SUPPRESS_WINDOW_MIN`                                |
| `ALERTS__DB_PATH`                           | `ALERTS_DB_PATH`                                            |
| (РїР»Р°РЅ) `ALERTS__KEEP_DAYS`                  | `ALERTS_KEEP_DAYS`                                          |
| `LIQUIDITY__MIN_VOL_24H_USD`                | `MIN_VOL_24H_USD`                                           |
| `LIQUIDITY__MIN_PRICE`                      | `MIN_PRICE`                                                 |

### РњС–РєСЂРѕР±Р»РѕРє: РџСЂС–РѕСЂРёС‚РµС‚ РєР»СЋС‡С–РІ РґР»СЏ alerts

> РЇРєС‰Рѕ РѕРґРЅРѕС‡Р°СЃРЅРѕ Р·Р°РґР°РЅРѕ `ALERTS__THRESHOLD_PCT` (nested) С– `ALERT_THRESHOLD_PCT` (flat),
> РїРµСЂРµРјР°РіР°С” **flat**. РўР°Рє СЃР°РјРѕ РґР»СЏ `COOLDOWN_SEC`, `SUPPRESS_*`, `DB_PATH`.

### РџСЂРѕРіСЂР°РјРЅРёР№ РґРѕСЃС‚СѓРї

```python
from src.infra.config import load_settings

s = load_settings()
print("env:", s.env)                                  # mirrors s.runtime.env
print("enable_alerts:", s.enable_alerts)              # mirrors s.runtime.enable_alerts
print("alerts:", s.alerts.threshold_pct, s.alerts.cooldown_sec)
print("suppress:", s.alerts.suppress_eps_pct, s.alerts.suppress_window_min)
print("alerts db:", s.alerts.db_path)
```

---

## Р—Р°РїСѓСЃРє

### CLI (Р»РѕРєР°Р»СЊРЅРёР№ smoke)

```powershell
# С‚РѕРї-3 Р·Р° РґРµС„РѕР»С‚РЅРёРј РїРѕСЂРѕРіРѕРј
python -m src.main basis:alert --limit 3

# С–Р· РєР°СЃС‚РѕРјРЅРёРј РїРѕСЂРѕРіРѕРј С– РјС–РЅС–РјР°Р»СЊРЅРёРј РѕР±СЃСЏРіРѕРј
python -m src.main basis:alert --limit 3 --threshold 0.8 --min-vol 12000000
```

### РџС–Рґ СЃСѓРїРµСЂРІС–Р·РѕСЂРѕРј

РЎРєСЂРёРїС‚ РєРµСЂСѓРІР°РЅРЅСЏ (PowerShell): `scripts/ws_supervisor_ctl.ps1`

```powershell
.\scripts\ws_supervisor_ctl.ps1 start
.\scripts\ws_supervisor_ctl.ps1 status
.\scripts\ws_supervisor_ctl.ps1 tail -TailLines 200
.\scripts\ws_supervisor_ctl.ps1 restart
.\scripts\ws_supervisor_ctl.ps1 stop
```

Р›РѕРіРё: `logs/app.log`, `logs/supervisor.*.log`. PID: `run/supervisor.pid`.

### Telegram-РєРѕРјР°РЅРґРё

- `/start` вЂ” РєРѕСЂРѕС‚РєР° РґРѕРІС–РґРєР° С– РїР°СЂР°РјРµС‚СЂРё
- `/top3` вЂ” РїРѕС‚РѕС‡РЅС– С‚РѕРї-3 РјРѕРЅРµС‚Рё
- `/set_threshold 1.5` вЂ” Р·РјС–РЅРёС‚Рё РїРѕСЂС–Рі Сѓ %
- `/status` вЂ” РїРµСЂРµРІС–СЂРєР° СЃС‚Р°РЅСѓ (WS/REST/Р°Р»РµСЂС‚Рё)
- `/report` вЂ” Р·РІРµРґРµРЅРЅСЏ Р·Р° РїРµСЂС–РѕРґ

---

## РўРµСЃС‚Рё С‚Р° СЏРєС–СЃС‚СЊ РєРѕРґСѓ

```powershell
pytest -q
pre-commit run -a
```

**pytest**: **144 passed, 1 skipped** (Р»РѕРєР°Р»СЊРЅРѕ).
**pre-commit**: `ruff`, `ruff-format`, `isort`, `black`, `mypy`, trim-whitespace, EOF check.
РљРѕРјРјС–С‚Рё вЂ” Сѓ СЃС‚РёР»С– **Conventional Commits**.

---

## РЎС‚СЂСѓРєС‚СѓСЂР° РїСЂРѕС”РєС‚Сѓ

```
src/
  exchanges/
    bybit/
      ws.py
  ws/
    multiplexer.py
    backoff.py
    health.py
    bridge.py
  core/
  infra/
    config.py
  telegram/
  storage/
scripts/
tests/
docs/
```

---

## CI/CD

- **GitHub Actions**: Р»С–РЅС‚РёРЅРі (ruff/black/isort), С‚РµСЃС‚Рё (pytest), С‚РёРїС–Р·Р°С†С–СЏ (mypy)
- **Reusable notify** workflow Р· `secrets: inherit`
- **Digest E2E Smoke**: Р·Р±С–СЂРєР° РґР°Р№РґР¶РµСЃС‚Сѓ, Р°СЂС‚РµС„Р°РєС‚, РѕРїС†С–Р№РЅРµ РїРѕРІС–РґРѕРјР»РµРЅРЅСЏ Сѓ Telegram

---

## Р”РѕРєСѓРјРµРЅС‚Р°С†С–СЏ

**IRM Maintenance**

- РљР°РЅРѕРЅС–С‡РЅРёР№ SSOT: `docs/irm.phase6.yaml` (**UTFвЂ‘8, Р±РµР· BOM**).
- Р“РµРЅРµСЂР°С†С–СЏ IRM:
  ```powershell
  # РїРµСЂРµРІС–СЂРєР° СЃРёРЅС…СЂРѕРЅРЅРѕСЃС‚С–
  python .\tools\irm_phase6_gen.py --check
  # РѕРЅРѕРІР»РµРЅРЅСЏ MD Р· SSOT
  python .\tools\irm_phase6_gen.py --write
  ```
- РЈРЅРёРєР°Р№С‚Рµ СЂСѓС‡РЅРѕРіРѕ СЂРµРґР°РіСѓРІР°РЅРЅСЏ `docs/IRM.md` вЂ” С‚С–Р»СЊРєРё РіРµРЅРµСЂР°С‚РѕСЂ.


- **WS Resilience (6.2.0)** вЂ” `docs/WS_RESILIENCE.md`
- **IRM** вЂ” РѕРЅРѕРІР»СЋС”С‚СЊСЃСЏ **Р»РёС€Рµ РіРµРЅРµСЂР°С‚РѕСЂРѕРј** (`Render IRM.view.md`)

---

## РўСЂР°Р±Р»С€СѓС‚С–РЅРі

- **`pip install -r requirements.txt` РїР°РґР°С” С‡РµСЂРµР· \x00** вЂ” РЅРµ РІРёРєРѕСЂРёСЃС‚РѕРІСѓР№С‚Рµ `-Encoding Unicode` РґР»СЏ `requirements.txt`; Р·Р±РµСЂС–РіР°Р№С‚Рµ С„Р°Р№Р» Сѓ **UTF-8**.
- **`git diff` В«РЅРµСЃРєС–РЅС‡РµРЅРЅРёР№В»** вЂ” РІРё Сѓ РїРµР№РґР¶РµСЂС–; РЅР°С‚РёСЃРЅС–С‚СЊ `q` Р°Р±Рѕ РІРёРєРѕСЂРёСЃС‚Р°Р№С‚Рµ `git --no-pager diff`.
- **CRLF/LF РїРѕРїРµСЂРµРґР¶РµРЅРЅСЏ** вЂ” РґРѕРґР°Р№С‚Рµ `.gitattributes` С–Р· РїСЂР°РІРёР»Р°РјРё EOL; Python-С„Р°Р№Р»Рё РєСЂР°С‰Рµ Р· **LF**.
- **PowerShell С– Р»Р°РїРєРё Сѓ git commit -m** вЂ” РґР»СЏ СЃРєР»Р°РґРЅРёС… РїРѕРІС–РґРѕРјР»РµРЅСЊ РІРёРєРѕСЂРёСЃС‚РѕРІСѓР№С‚Рµ РѕРґРёРЅР°СЂРЅС– Р»Р°РїРєРё Р°Р±Рѕ `-F file.txt`.
- **Digest РЅРµ С€Р»Рµ Сѓ Telegram** вЂ” РїРµСЂРµРІС–СЂС‚Рµ `TELEGRAM__TOKEN/CHAT_ID` (СЃРµРєСЂРµС‚Рё РЅРµ Р»РѕРіСѓСЋС‚СЊСЃСЏ).

---

## Р›С–С†РµРЅР·С–СЏ

MIT В© 2025
