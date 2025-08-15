from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_DB = "data/signals.db"

ISO_FMT = "%Y-%m-%dT%H:%M:%S.%f"


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _parse_iso(s: str) -> datetime:
    try:
        return datetime.strptime(s, ISO_FMT).replace(tzinfo=timezone.utc)

    except ValueError:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _select_rows(
    con: sqlite3.Connection,
    last_hours: Optional[int],
    since: Optional[str],
    until: Optional[str],
    limit: Optional[int],
) -> List[Tuple]:
    base_sql = """

      SELECT symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp

      FROM signals

    """

    where = []

    params: List[object] = []

    if since or until:
        if since:
            where.append("timestamp >= ?")

            params.append(since)

        if until:
            where.append("timestamp <= ?")

            params.append(until)

    elif last_hours is not None:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=int(last_hours))
        ).isoformat()

        where.append("timestamp >= ?")

        params.append(cutoff)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    order_sql = " ORDER BY timestamp DESC"

    limit_sql = " LIMIT ?" if (limit is not None and int(limit) > 0) else ""

    if limit_sql:
        params.append(int(limit))

    sql = base_sql + where_sql + order_sql + limit_sql

    cur = con.cursor()

    cur.execute(sql, params)

    return cur.fetchall()


def _localize_ts(ts: str, tz_name: Optional[str]) -> str:
    if not tz_name:
        return ts

    try:
        if tz_name.upper() == "EUROPE/KYIV" or tz_name.lower() == "europe/kyiv":
            offset = timedelta(hours=3)  # літній час (спрощено)

        elif tz_name.startswith(("+", "-")) and len(tz_name) in (6, 9):
            parts = tz_name[1:].split(":")

            sign = 1 if tz_name[0] == "+" else -1

            hours = int(parts[0]) if len(parts) > 0 else 0

            minutes = int(parts[1]) if len(parts) > 1 else 0

            seconds = int(parts[2]) if len(parts) > 2 else 0

            offset = sign * timedelta(hours=hours, minutes=minutes, seconds=seconds)

        else:
            return ts

        dt_utc = _parse_iso(ts)

        dt_local = dt_utc.astimezone(timezone(offset))

        return dt_local.replace(microsecond=0).isoformat()

    except Exception:
        return ts


def export_signals(
    out_path: Path,
    last_hours: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: Optional[int] = None,
    tz: Optional[str] = None,
    keep: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Path:
    if last_hours is not None and (since or until):
        raise ValueError("Use either --last-hours OR (--since/--until), not both.")

    if last_hours is not None and last_hours <= 0:
        raise ValueError("--last-hours must be > 0")

    if limit is not None and limit <= 0:
        raise ValueError("--limit must be > 0")

    db = db_path or os.getenv("DB_PATH", DEFAULT_DB)

    con = sqlite3.connect(db)

    rows = _select_rows(
        con, last_hours=last_hours, since=since, until=until, limit=limit
    )

    con.close()

    _ensure_parent_dir(out_path)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        w.writerow(
            [
                "timestamp",
                "symbol",
                "spot_price",
                "futures_price",
                "basis_pct",
                "volume_24h_usd",
            ]
        )

        for symbol, spot, fut, basis, vol, ts in rows:
            ts_out = _localize_ts(ts, tz)

            w.writerow([ts_out, symbol, spot, fut, basis, vol])

    if keep is not None and keep > 0:
        stem = out_path.stem

        prefix = stem.split("_")[0]

        all_csv = sorted(
            out_path.parent.glob(f"{prefix}_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for old in all_csv[keep:]:
            try:
                old.unlink()

            except Exception:
                pass

    return out_path


def _default_out_name(prefix: str = "signals") -> str:
    now = datetime.now(timezone.utc)

    return f"{prefix}_{now.strftime('%Y-%m-%d_%H%M')}.csv"


def main() -> None:
    p = argparse.ArgumentParser(
        description="Export arbitrage signals from SQLite to CSV (Windows-friendly)."
    )

    p.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output CSV path (e.g., exports/signals_YYYY-MM-DD_HHMM.csv)",
    )

    p.add_argument(
        "--last-hours",
        type=int,
        default=24,
        help="Export only last N hours (default: 24)",
    )

    p.add_argument(
        "--since",
        type=str,
        default=None,
        help="Export from UTC ISO time (e.g., 2025-08-10T00:00:00)",
    )

    p.add_argument("--until", type=str, default=None, help="Export until UTC ISO time")

    p.add_argument("--limit", type=int, default=None, help="Limit rows")

    p.add_argument(
        "--tz",
        type=str,
        default=None,
        help='Localize timestamp to "Europe/Kyiv" or offset like "+03:00"',
    )

    p.add_argument(
        "--keep",
        type=int,
        default=None,
        help="Keep only last N CSV files with the same prefix",
    )

    args = p.parse_args()

    out = Path(args.out) if args.out else Path("exports") / _default_out_name("signals")

    path = export_signals(
        out_path=out,
        last_hours=(
            args.last_hours if (args.since is None and args.until is None) else None
        ),
        since=args.since,
        until=args.until,
        limit=args.limit,
        tz=args.tz,
        keep=args.keep,
    )

    print(f"CSV saved to: {path}")


if __name__ == "__main__":
    main()
