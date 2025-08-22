# scripts/gh_daily_digest.py
# CLI for GitHub Daily Digest — supports --date, --send, mock/real modes, daily throttle
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Tuple

import httpx

try:
    from zoneinfo import ZoneInfo  # Python 3.11+ on Windows 11 has it
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

# --- Force UTF-8 for Windows consoles ---
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Try to load .env if present (non-invasive)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

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
RUN_DIR = Path("run")
RUN_DIR.mkdir(parents=True, exist_ok=True)


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


# -------- Telegram sending --------


def _throttle_stamp_path(date_kyiv: date) -> Path:
    # one send per Kyiv-day
    return RUN_DIR / f"gh_digest.sent.{date_kyiv.isoformat()}.stamp"


def _should_send_today(date_kyiv: date) -> bool:
    return not _throttle_stamp_path(date_kyiv).exists()


def _mark_sent_today(date_kyiv: date) -> None:
    _throttle_stamp_path(date_kyiv).write_text("sent", encoding="utf-8")


def _send_telegram(text: str) -> None:
    """
    Sends a plain-text message to Telegram via Bot API.
    Requires env vars: TG_BOT_TOKEN, TG_CHAT_ID
    """
    token = (
        os.getenv("TG_BOT_TOKEN")
        or os.getenv("TG_TOKEN")
        or os.getenv("TELEGRAM_BOT_TOKEN")
    )
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "Telegram credentials are missing: set TG_BOT_TOKEN and TG_CHAT_ID in environment/.env"
        )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # We intentionally do NOT set parse_mode to avoid escaping headaches; text is plain.
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}

    with httpx.Client(timeout=10.0) as client:
        r = client.post(url, data=payload)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram sendMessage failed: {data}")


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
        help="Send the digest message to Telegram (one per Kyiv-day; see --force)",
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
    # Throttle control:
    parser.add_argument(
        "--force", action="store_true", help="Bypass daily throttle and send anyway"
    )
    args = parser.parse_args(argv)

    d = date.fromisoformat(args.date) if args.date else _today_kyiv()

    # Decide mode: default to mock unless --no-mock provided.
    use_mock = True
    if args.no_mock:
        use_mock = False
    elif args.mock:
        use_mock = True

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
        if not args.force and not _should_send_today(d):
            print(
                "\n[send] Skipped: daily throttle (already sent for this Kyiv-day). Use --force to override."
            )
            return 0
        try:
            _send_telegram(text)
            _mark_sent_today(d)
            print("\n[send] OK: digest sent to Telegram.")
        except Exception as e:
            # Do not leak secrets; show concise error
            print(f"\n[send] ERROR: {e.__class__.__name__}: {e}")
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
