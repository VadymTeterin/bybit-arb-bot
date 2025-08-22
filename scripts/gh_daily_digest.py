# scripts/gh_daily_digest.py
# CLI for GitHub Daily Digest — supports --date, --send, mock/real modes (backward-compatible)
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timezone
from typing import List, Tuple

try:
    from zoneinfo import ZoneInfo  # Python 3.11+ on Windows 11 has it
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from src.github.client import GitHubClient
from src.reports.gh_digest import (
    CommitEvent,
    MergeEvent,
    TagEvent,
    build_digest,
    kyiv_day_bounds,
    parse_commit,
    parse_merge_pr,
    parse_tag,
    render_text_report,
)

KYIV_TZ = ZoneInfo("Europe/Kyiv") if ZoneInfo else None  # for "today" resolution


def _today_kyiv() -> date:
    if KYIV_TZ:
        now_kyiv = datetime.now(KYIV_TZ)
        return now_kyiv.date()
    return datetime.utcnow().date()


def _mock_events(d: date) -> Tuple[List[CommitEvent], List[MergeEvent], List[TagEvent]]:
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


def _iso(dt: datetime) -> str:
    # GitHub expects ISO8601 with Z
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _collect_real_events(
    d: date, owner: str, repo: str, client: GitHubClient
) -> Tuple[List[CommitEvent], List[MergeEvent], List[TagEvent]]:
    start_utc, end_utc = kyiv_day_bounds(d)
    since_iso, until_iso = _iso(start_utc), _iso(end_utc)

    # COMMITS
    commits_raw = list(
        client.list_commits(owner, repo, since_iso=since_iso, until_iso=until_iso)
    )
    commits: List[CommitEvent] = [
        parse_commit(item, default_branch="main") for item in commits_raw
    ]

    # MERGES (PRs)
    pulls_raw = list(client.list_pulls_merged(owner, repo))
    merges: List[MergeEvent] = []
    for pr in pulls_raw:
        merged_at_iso = pr.get("merged_at")
        if not merged_at_iso:
            continue
        me = parse_merge_pr(pr, base_fallback="main")
        if start_utc <= me.merged_at < end_utc:
            merges.append(me)

    # TAGS (require commit date lookup)
    tags_raw = list(client.list_tags(owner, repo))
    tags: List[TagEvent] = []
    for t in tags_raw:
        te = parse_tag(t)
        sha = te.sha
        if not sha:
            continue
        commit_obj = client.get_commit(owner, repo, sha)
        ci = (commit_obj.get("commit") or {}).get("author") or {}
        c_iso = ci.get("date")
        if not c_iso:
            continue
        te.tagged_at = datetime.fromisoformat(c_iso.replace("Z", "+00:00"))
        if start_utc <= te.tagged_at < end_utc:
            tags.append(te)

    return commits, merges, tags


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GitHub Daily Digest")
    parser.add_argument(
        "--date", type=str, help="Kyiv date YYYY-MM-DD (default: today in Kyiv)"
    )
    parser.add_argument(
        "--owner",
        type=str,
        default=os.getenv("GITHUB_OWNER") or "VadymTeterin",
        help="GitHub owner/org (default from env)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=os.getenv("GITHUB_REPO") or "bybit-arb-bot",
        help="GitHub repo name (default from env)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the digest message (reserved; prints hint)",
    )
    # Backward-compatible flags:
    parser.add_argument(
        "--mock", action="store_true", help="Use offline mock data (default)"
    )
    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Use real GitHub API instead of offline mock data",
    )
    args = parser.parse_args(argv)

    d = date.fromisoformat(args.date) if args.date else _today_kyiv()

    # Decide mode: default to mock unless --no-mock provided.
    use_mock = True
    if args.no_mock:
        use_mock = False
    elif args.mock:
        use_mock = True  # explicit mock wins only if --no-mock not set

    if use_mock:
        commits, merges, tags = _mock_events(d)
    else:
        client = GitHubClient()
        commits, merges, tags = _collect_real_events(d, args.owner, args.repo, client)
        client.close()

    digest = build_digest(d, commits=commits, merges=merges, tags=tags)
    text = render_text_report(digest)
    print(text)

    if args.send:
        print(
            "\n[send] NOTE: Sending is not wired in Step-6.0.2. We will integrate Telegram in Step-6.0.3."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
