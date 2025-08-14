# Bybit Arbitrage Bot

## Опис / Description
**UA:** Telegram-бот для моніторингу різниці між цінами на спотовому та ф’ючерсному ринках Bybit у режимі реального часу.  
**EN:** A Telegram bot that monitors spot vs. futures price spreads on Bybit in real time.

## Функціонал / Features
- Bybit REST API & WebSocket API v5
- Basis % (spot vs futures) calculation
- Top-N selection by threshold
- Liquidity filters
- Telegram alerts
- SQLite signal history
- **CSV export of signals**

## Встановлення / Installation
```powershell
# Clone the repository
git clone https://github.com/<your-repo>.git
cd bybit-arb-bot

# Create & activate virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Налаштування / Configuration
Create your `.env` from `.env.example` and fill the values:
```env
BYBIT__API_KEY=
BYBIT__API_SECRET=
TELEGRAM__BOT_TOKEN=
TELEGRAM__ALERT_CHAT_ID=
ALERT_THRESHOLD_PCT=1.0
ALERT_COOLDOWN_SEC=300
DB_PATH=data/signals.db
```
> Keep `.env` local (git-ignored). Commit only `.env.example` without secrets.

## Експорт у CSV / CSV Export
```powershell
# 1) Last 24h to exports/ with default name
python .\scripts\export_signals.py

# 2) Localize timestamps to Kyiv time (UTC+3 in summer)
python .\scripts\export_signals.py --tz Europe/Kyiv

# 3) Exact UTC interval and custom filename
python .\scripts\export_signals.py --since 2025-08-10T00:00:00 --until 2025-08-14T23:59:59 --out .\exports\signals_aug10-14.csv

# 4) Limit to 100 latest rows
python .\scripts\export_signals.py --limit 100

# 5) Rotation: keep only 14 latest CSV files (prefix: signals_*)
python .\scripts\export_signals.py --keep 14
```

**Параметри / Arguments:**
- `--last-hours N` — default 24h
- `--since` / `--until` — UTC ISO bounds
- `--tz` — e.g. `Europe/Kyiv` or `+03:00`
- `--limit N` — limit rows
- `--keep N` — rotate old CSVs
- `--out PATH` — output file path

---

# 🔁 Автоматичний експорт через Windows Task Scheduler / Automatic Export via Windows Task Scheduler

## UA — Коротко
Налаштуй планувальник завдань Windows, щоб `scripts/export_signals.py` запускався автоматично (щогодини або щодня). Це гарантує регулярне створення CSV та підтримку історичного архіву без ручних дій.

### Варіант A — Через інтерфейс (GUI)
1. Відкрий **Task Scheduler** → *Create Task…*  
   - Name: `BybitArbBot CSV Export`  
   - (Опційно) *Run with highest privileges*
2. **Triggers** → *New…* → *Daily* або *Hourly* (рекомендовано щогодини **:05**).
3. **Actions** → *New…*  
   - **Program/script**: `C:\Projects\bybit-arb-bot\.venv\Scripts\python.exe`  
   - **Add arguments**: `scripts\export_signals.py --last-hours 24 --keep 14`  
   - **Start in**: `C:\Projects\bybit-arb-bot`
4. **Conditions** → (опційно) *Wake the computer to run this task*.
5. **Settings** → дозволити перезапуск при збої, обмежити тривалість.
6. Збережи й натисни *Run* для перевірки.

### Варіант B — Через PowerShell
Створи лончер і задачу:
```powershell
# In project root
Set-Content -Path .\launcher_export.cmd -Encoding ASCII -Value @'
@echo off
setlocal
cd /d C:\Projectsybit-arb-bot
C:\Projectsybit-arb-bot\.venv\Scripts\python.exe scripts\export_signals.py --last-hours 24 --keep 14 >> logs\export.log 2>&1
endlocal
'@

New-Item -ItemType Directory -Path .\logs -ErrorAction Ignore | Out-Null

# Create hourly task at HH:05 under current user
schtasks /Create /TN "BybitArbBot CSV Export Hourly" /TR "C:\Projectsybit-arb-bot\launcher_export.cmd" /SC HOURLY /ST 00:05 /F
```

### Перевірка
```powershell
schtasks /Run /TN "BybitArbBot CSV Export Hourly"
Get-ChildItem .\exports\signals_*.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content .\logs\export.log -Tail 20
```

> Поради: використовуйте **повні шляхи**, зберігайте CSV поза git (`exports/` у `.gitignore`), а `.env` — локально.

---

## EN — Summary
Use Windows Task Scheduler to run `scripts/export_signals.py` automatically (hourly/daily). This ensures continuous CSV generation and a rolling history without manual runs.

### Option A — GUI
1. Open **Task Scheduler** → *Create Task…*  
   - Name: `BybitArbBot CSV Export`  
   - (Optional) *Run with highest privileges*
2. **Triggers** → *New…* → *Daily* or *Hourly* (recommended hourly at **:05**).
3. **Actions** → *New…*  
   - **Program/script**: `C:\Projects\bybit-arb-bot\.venv\Scripts\python.exe`  
   - **Add arguments**: `scripts\export_signals.py --last-hours 24 --keep 14`  
   - **Start in**: `C:\Projects\bybit-arb-bot`
4. **Conditions** → optionally *Wake the computer to run this task*.
5. **Settings** → allow retry on failure, set a max run time.
6. Save and click *Run* to test.

### Option B — PowerShell
Create the launcher and the task:
```powershell
# In project root
Set-Content -Path .\launcher_export.cmd -Encoding ASCII -Value @'
@echo off
setlocal
cd /d C:\Projectsybit-arb-bot
C:\Projectsybit-arb-bot\.venv\Scripts\python.exe scripts\export_signals.py --last-hours 24 --keep 14 >> logs\export.log 2>&1
endlocal
'@

New-Item -ItemType Directory -Path .\logs -ErrorAction Ignore | Out-Null

# Create hourly task at HH:05 under current user
schtasks /Create /TN "BybitArbBot CSV Export Hourly" /TR "C:\Projectsybit-arb-bot\launcher_export.cmd" /SC HOURLY /ST 00:05 /F
```

### Verify
```powershell
schtasks /Run /TN "BybitArbBot CSV Export Hourly"
Get-ChildItem .\exports\signals_*.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content .\logs\export.log -Tail 20
```

> Tips: always use **absolute paths**, keep CSV out of git (`exports/` in `.gitignore`), and keep your real `.env` local.

---

## Тести / Tests
```powershell
pytest -q
```

## Ліцензія / License
MIT
