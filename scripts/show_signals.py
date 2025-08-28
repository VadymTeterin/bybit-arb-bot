from __future__ import annotations

import os
import sqlite3


def show_signals(limit: int = 10, last_hours: int | None = None) -> None:
    db = os.getenv("DB_PATH", "data/signals.db")
    con = sqlite3.connect(db)
    cur = con.cursor()

    base_sql = """
      SELECT symbol, spot_price, futures_price, basis_pct, volume_24h_usd, timestamp
      FROM signals
    """
    where = ""
    params = []
    if last_hours is not None:
        # SQLite не має now(); використовуємо datetime('now','-X hours')
        where = "WHERE timestamp >= datetime('now', ?)"
        params.append(f"-{int(last_hours)} hours")

    order = " ORDER BY timestamp DESC"
    limit_sql = " LIMIT ?"
    params.append(int(limit))

    cur.execute(base_sql + (" " + where if where else "") + order + limit_sql, params)
    rows = cur.fetchall()
    con.close()

    if not rows:
        print("No signals found.")
        return

    for r in rows:
        # r: (symbol, spot, fut, basis_pct, vol_usd, ts)
        print(f"{r[5]}  {r[0]:<10}  spot={r[1]}  fut={r[2]}  basis%={r[3]}  vol={r[4]}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Show recent arbitrage signals from SQLite.")
    p.add_argument("--limit", type=int, default=10, help="How many rows to show (default: 10)")
    p.add_argument("--last-hours", type=int, default=None, help="Only rows within the last N hours")
    args = p.parse_args()
    show_signals(limit=args.limit, last_hours=args.last_hours)
