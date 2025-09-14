# HISTORY_AND_FILTERS.md

## Data Retention & Filters (Phase 6.3.7 · 2025-09-14)

This document summarizes the retention policies and alert-related filters
for the Bybit Arbitrage Bot. It complements the README by providing
canonical defaults and operational notes.

### Retention policy (SQLite)
The bot applies automatic data retention via the maintenance CLI (`scripts/sqlite_maint.py`)
and daily scheduler (`scripts/sqlite.maint.daily.ps1`).

**Default windows (can be overridden via ENV):**
- **signals** — 14 days (`SQLITE_RETENTION_SIGNALS_DAYS`)
- **alerts_log** — 30 days (`SQLITE_RETENTION_ALERTS_DAYS`)
- **quotes** — 7 days (`SQLITE_RETENTION_QUOTES_DAYS`)

These defaults are applied during the `--execute --retention-only` phase.

### Alert cooldown & suppression
- **Cooldown**: 300 seconds by default (`ALERTS__COOLDOWN_SEC`).
- **Suppression**: near-duplicates within the cooldown window are suppressed
  if the basis% delta is below `ALERTS__SUPPRESS_EPS_PCT` (epsilon, in % points).

Cross-reference: see **Alerts (6.3.x)** section in README for details.

### Demo environment notes
- Signals/alerts generated in DEMO env (Step 6.3.6a) are **not persisted** in the production DB.
- Retention policies apply only to production DB (`data/signals.db` by default).

---

**Operational notes:**
- Always run a **dry run** (`--dry-run`) first before executing retention on production DB.
- Verify scheduled task logs in `logs/sqlite_maint.log` after daily runs.
