# Bybit Arbitrage Bot (MVP)

## Quick start (Windows 11)
1. Create venv: `py -3.11 -m venv .venv`
2. Activate: `. .\.venv\Scripts\Activate.ps1`
3. Upgrade pip: `pip install --upgrade pip`
4. Install deps: see below
5. Copy `.env.example` to `.env` and fill keys
6. Run checks: `pytest -q`, `ruff .`, `black .`, `isort .`

## Structure
src/ - app code
tests/ - tests
logs/ - runtime logs
