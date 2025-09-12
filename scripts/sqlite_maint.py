# scripts/sqlite_maint.py
# Purpose: SQLite maintenance CLI (retention & compaction)
# Comments: English only (per WA). Windows-friendly. No secrets printed.

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import os
import signal
import sqlite3
import sys
import time
from pathlib import Path

# ---------- Defaults (safe, non-breaking) ----------
DEF_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/signals.db")
RET_SIGNALS_DAYS = int(os.getenv("SQLITE_RETENTION_SIGNALS_DAYS", "14"))
RET_QUOTES_DAYS = int(os.getenv("SQLITE_RETENTION_QUOTES_DAYS", "7"))
RET_ALERTS_DAYS = int(os.getenv("SQLITE_RETENTION_ALERTS_DAYS", "30"))
MAINT_ENABLE = os.getenv("SQLITE_MAINT_ENABLE", "0") == "1"
VACUUM_STRATEGY = os.getenv(
    "SQLITE_MAINT_VACUUM_STRATEGY", "incremental"
)  # full|incremental|none
MAX_DURATION_SEC = int(os.getenv("SQLITE_MAINT_MAX_DURATION_SEC", "60"))

BUSY_TIMEOUT_MS = 4000
INCREMENTAL_PAGES = 4000  # can be tuned later

# ---------- Tables & timestamp columns ----------
TABLE_TS_MAP: dict[str, tuple[str, int]] = {
    "signals": ("ts", RET_SIGNALS_DAYS),
    "alerts_log": ("created_at", RET_ALERTS_DAYS),
    # Add quotes table if present in schema
    "quotes": ("ts", RET_QUOTES_DAYS),
}


@dataclasses.dataclass
class Metrics:
    size_before: int = 0
    size_after: int = 0
    counts_before: dict[str, int] = dataclasses.field(default_factory=dict)
    counts_after: dict[str, int] = dataclasses.field(default_factory=dict)
    deleted: dict[str, int] = dataclasses.field(default_factory=dict)
    elapsed_ms: int = 0
    strategy: str = VACUUM_STRATEGY


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def utc_now_seconds() -> int:
    return int(time.time())


def ensure_indexes(conn: sqlite3.Connection) -> None:
    """
    Idempotent index creation for timestamp-based retention.
    Creates indexes only if the table exists.
    """
    cur = conn.cursor()

    def table_exists(name: str) -> bool:
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        return cur.fetchone() is not None

    # signals(ts)
    if table_exists("signals"):
        cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(ts)")

    # alerts_log(created_at)
    if table_exists("alerts_log"):
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_log_created_at ON alerts_log(created_at)"
        )

    # quotes(ts)
    if table_exists("quotes"):
        cur.execute("CREATE INDEX IF NOT EXISTS idx_quotes_ts ON quotes(ts)")

    conn.commit()


def count_table(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.cursor()
    with contextlib.suppress(sqlite3.OperationalError):
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        row = cur.fetchone()
        return int(row[0]) if row else 0
    return 0


def retention_delete(
    conn: sqlite3.Connection, table: str, ts_col: str, days: int, dry_run: bool
) -> int:
    """
    Delete rows older than now - X days. Assumes ts_col is epoch seconds or comparable.
    """
    cutoff = utc_now_seconds() - days * 86400
    cur = conn.cursor()

    # Fast path: check if table exists
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    if not cur.fetchone():
        return 0

    # Guard: ensure ts_col exists
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if ts_col not in cols:
        return 0

    if dry_run:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {ts_col} < ?", (cutoff,))
        row = cur.fetchone()
        return int(row[0]) if row else 0

    cur.execute(f"DELETE FROM {table} WHERE {ts_col} < ?", (cutoff,))
    deleted = cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    return deleted


def compact_db(conn: sqlite3.Connection, strategy: str, dry_run: bool) -> None:
    """
    Compact database per strategy.
    """
    cur = conn.cursor()
    if strategy == "none":
        return
    if strategy == "incremental":
        # Enable incremental once; safe to set many times
        cur.execute("PRAGMA auto_vacuum=INCREMENTAL")
        conn.commit()
        if not dry_run:
            cur.execute(f"PRAGMA incremental_vacuum({INCREMENTAL_PAGES})")
            conn.commit()
    elif strategy == "full":
        # Full VACUUM blocks DB — should be used off-hours only.
        if not dry_run:
            cur.execute("VACUUM")
            conn.commit()

    # Always do optimize & analyze
    cur.execute("PRAGMA optimize")
    cur.execute("ANALYZE")
    conn.commit()


def busy_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(
        db_path, timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None
    )
    # WAL mode is controlled by the app; we do not force it here.
    # Short-lived transactions:
    conn.execute("PRAGMA journal_mode")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    return conn


def run_maintenance(
    db_path: str, do_retention: bool, do_compact: bool, dry_run: bool
) -> Metrics:
    metrics = Metrics(strategy=VACUUM_STRATEGY)
    p = Path(db_path)
    metrics.size_before = file_size(p)

    start = time.perf_counter()

    with contextlib.ExitStack() as stack:
        conn = stack.enter_context(busy_connection(db_path))
        ensure_indexes(conn)

        # Save before counts
        for tbl in TABLE_TS_MAP:
            metrics.counts_before[tbl] = count_table(conn, tbl)

        if do_retention:
            for tbl, (ts_col, days) in TABLE_TS_MAP.items():
                deleted = retention_delete(conn, tbl, ts_col, days, dry_run)
                metrics.deleted[tbl] = deleted

        if do_compact:
            compact_db(conn, VACUUM_STRATEGY, dry_run)

        # After counts
        for tbl in TABLE_TS_MAP:
            metrics.counts_after[tbl] = count_table(conn, tbl)

    metrics.size_after = file_size(p)
    metrics.elapsed_ms = int((time.perf_counter() - start) * 1000)
    return metrics


def guard_enable() -> None:
    if not MAINT_ENABLE:
        print(
            "Maintenance is disabled: set SQLITE_MAINT_ENABLE=1 to enable.",
            file=sys.stderr,
        )
        sys.exit(2)


def install_time_guard(seconds: int) -> None:
    if seconds <= 0:
        return

    def _handler(signum, frame):  # noqa: ARG001
        print(f"Time limit exceeded ({seconds}s). Aborting.", file=sys.stderr)
        sys.exit(3)

    # SIGALRM is not available on Windows; best-effort only on POSIX.
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SQLite maintenance CLI (retention & compaction)"
    )
    parser.add_argument(
        "--db", default=DEF_DB_PATH, help=f"Path to SQLite DB (default: {DEF_DB_PATH})"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be done, no changes"
    )
    parser.add_argument("--execute", action="store_true", help="Apply changes")
    parser.add_argument(
        "--retention-only", action="store_true", help="Run only retention"
    )
    parser.add_argument(
        "--compact-only", action="store_true", help="Run only compaction"
    )
    args = parser.parse_args(argv)

    if not (args.dry_run or args.execute):
        print("Choose one of: --dry-run | --execute", file=sys.stderr)
        return 2

    # Safety: require MAINT_ENABLE=1 for --execute
    if args.execute:
        guard_enable()

    do_ret = not args.compact_only
    do_cmp = not args.retention_only

    install_time_guard(MAX_DURATION_SEC)

    try:
        metrics = run_maintenance(args.db, do_ret, do_cmp, args.dry_run)
    except sqlite3.OperationalError as e:
        print(f"OperationalError: {e}", file=sys.stderr)
        return 1

    # Human summary
    mode = "DRY-RUN" if args.dry_run else "EXECUTE"
    print(f"[{mode}] DB: {args.db}")
    print(f"  Strategy: {VACUUM_STRATEGY}")
    print(f"  Size: {metrics.size_before} → {metrics.size_after} bytes")
    print(f"  Elapsed: {metrics.elapsed_ms} ms")
    print("  Deleted per table:")
    for tbl, n in metrics.deleted.items():
        print(f"    - {tbl}: {n}")

    # JSON line (for logs/automation)
    payload = {
        "mode": mode,
        "db": args.db,
        "strategy": metrics.strategy,
        "size_before": metrics.size_before,
        "size_after": metrics.size_after,
        "counts_before": metrics.counts_before,
        "counts_after": metrics.counts_after,
        "deleted": metrics.deleted,
        "elapsed_ms": metrics.elapsed_ms,
        "ts": utc_now_seconds(),
    }
    print(json.dumps(payload, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
