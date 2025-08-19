# Changelog

Формат: [Keep a Changelog](https://keepachangelog.com). Дати у форматі YYYY‑MM‑DD. Семантичне версіонування.

## [Unreleased]

### Added
- `/status` (Telegram) та `ws:health` (CLI) — **план** для Step 5.8.4 (ще не реліз).
- `src/ws/backoff.py` — експоненційний бекоф (cap, no‑overshoot) — **план**.
- `src/ws/health.py` — метрики WS (SPOT/LINEAR), аптайм — **план**.

---

## [v0.5.8.3] — 2025-08-19
### Added
- **CLI `alerts:preview`** — прев’ю алерта без відправки у Telegram (смуговий тест CLI).
- **Windows‑лаунчер `launcher_export.cmd`**:
  - `cd /d %~dp0` (зміна диску і директорії до кореня проекту),
  - створення `logs\` якщо відсутня,
  - посилання на `scripts\export_signals.py`,
  - редирект логу `>> logs\export.log 2>&1`,
  - пріоритет `.venv\Scripts\python.exe`,
  - прокидання аргументів у `python -m src.main`.
- **WS MUX counters**: лічильники нормалізованих подій (SPOT/LINEAR).
- **Тести**: CLI смоук для `src.main`, базові тести на лаунчер.

### Changed
- **argparse type fixes** для стабільності CLI (`positive_float`, `nonneg_int`).
- **pre-commit auto-fixes** (ruff format, isort, тощо).

### CI
- Оновлено перевірки, локально: **103 passed, 1 skipped**.
- (Рекомендація) окремий workflow, що валідуює наявність `launcher_export.cmd` (див. нижче).

---

## [v0.5.6] — 2025-08-15
- WS Multiplexer + `ws:run` інтеграція. (Стислий запис; деталі див. історію PR).

## [v0.5.0] — 2025-08-10
- Фаза 2/3: REST‑MVP, Telegram‑алерти, базові фільтри, історія сигналів.
