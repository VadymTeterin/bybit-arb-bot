# scripts/gh_daily_digest.py
# CLI for GitHub Daily Digest — supports --date, --send, and offline mock mode
from __future__ import annotations

import argparse
from datetime import date, datetime
from typing import List

from src.reports.gh_digest import (
    CommitEvent,
    MergeEvent,
    TagEvent,
    build_digest,
    kyiv_day_bounds,
    render_text_report,
)

# Note:
#  - This CLI intentionally avoids network I/O at this stage (Step-6.0.1 scaffold).
#  - In Step-6.0.2 we will wire src.github.client.GitHubClient and real API calls.
#  - --send flag is reserved; for now it only prints a hint to integrate Telegram later.


def _mock_events(d: date):
    # Build a tiny, deterministic set of events inside the Kyiv day window
    start_utc, end_utc = kyiv_day_bounds(d)
    mid = start_utc + (end_utc - start_utc) / 2

    commits = [
        CommitEvent(
            sha="a1b2c3d",
            message="Implement GH digest scaffold",
            author="dev",
            branch="step-6.0.1",
            committed_at=mid,
        ),
        CommitEvent(
            sha="d4e5f6g",
            message="fix: minor typos",
            author="dev",
            branch="main",
            committed_at=mid,
        ),
    ]
    merges = [
        MergeEvent(
            number=123,
            title="feat: WS stability finalized",
            merged_by="VadymTeterin",
            merged_at=mid,
            base_branch="main",
        )
    ]
    tags = [TagEvent(name="v0.6.0", sha="f00ba47", tagged_at=mid)]
    return commits, merges, tags


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GitHub Daily Digest (scaffold)")
    parser.add_argument(
        "--date", type=str, help="Kyiv date YYYY-MM-DD (default: today in Kyiv)"
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the digest message (reserved; prints hint in scaffold)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use offline mock data (default in scaffold)",
    )
    args = parser.parse_args(argv)

    if args.date:
        d = date.fromisoformat(args.date)
    else:
        # "Today" relative to Kyiv time
        # Since we do not import zoneinfo here, we use UTC->date approximation:
        # In Step-6.0.2 we may switch to zoneinfo for exactness in CLI.
        d = datetime.utcnow().date()

    if args.mock or True:
        commits, merges, tags = _mock_events(d)
    else:
        # Placeholder for future Step-6.0.2 (real API)
        raise NotImplementedError("Real API wiring will be added in Step-6.0.2")

    digest = build_digest(d, commits=commits, merges=merges, tags=tags)
    text = render_text_report(digest)
    print(text)

    if args.send:
        # Reserved: integrate Telegram sender or notify pipeline next step.
        # We deliberately avoid importing notify modules here to keep scaffold minimal.
        print(
            "\n[send] NOTE: Sending is not wired in scaffold. Integrate in Step-6.0.2."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
