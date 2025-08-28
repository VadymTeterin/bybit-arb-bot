# src/reports/gh_digest.py
# (c) Bybit Arb Bot — GitHub Daily Digest report & aggregation
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

try:
    # Python 3.9+: zoneinfo
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


# ---------- Time helpers (Kyiv "business day" window) ----------

KYIV_TZ_NAME = "Europe/Kyiv"


def kyiv_day_bounds(d: date) -> tuple[datetime, datetime]:
    """
    For a given calendar date in Kyiv, return (start_utc, end_utc)
    where start is 00:00:00 and end is 23:59:59.999... of that Kyiv day,
    both converted to UTC. Handles DST via zoneinfo.
    """
    if ZoneInfo is None:
        # Fallback: assume +02/+03 won't be exact; keep simple +03
        offset = timedelta(hours=3)
        start_utc = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) - offset
        end_utc = start_utc + timedelta(days=1)
        return start_utc, end_utc

    kyiv = ZoneInfo(KYIV_TZ_NAME)
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=kyiv)
    end_local = start_local + timedelta(days=1)
    # Convert to UTC
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    return start_utc, end_utc


# ---------- Event models (lightweight) ----------


@dataclass
class CommitEvent:
    sha: str
    message: str
    author: str
    branch: str
    committed_at: datetime  # UTC


@dataclass
class MergeEvent:
    number: int
    title: str
    merged_by: str
    merged_at: datetime  # UTC
    base_branch: str


@dataclass
class TagEvent:
    name: str
    sha: str
    tagged_at: datetime  # UTC (commit date)


@dataclass
class Digest:
    date_kyiv: date
    window_utc: tuple[datetime, datetime]
    commits: list[CommitEvent]
    merges: list[MergeEvent]
    tags: list[TagEvent]

    @property
    def stats(self) -> dict[str, int]:
        return {
            "commits": len(self.commits),
            "merges": len(self.merges),
            "tags": len(self.tags),
        }


# ---------- Parsing helpers from raw GitHub payloads (dicts) ----------


def parse_commit(item: dict[str, Any], default_branch: str = "main") -> CommitEvent:
    commit = item.get("commit", {})
    author = (commit.get("author") or {}).get("name") or "unknown"
    message = commit.get("message") or ""
    sha = item.get("sha") or ""
    # Branch information may not be present in commit list response; default.
    branch = item.get("branch") or default_branch

    # Dates: prefer item["commit"]["author"]["date"] (ISO8601)
    committed_iso = (commit.get("author") or {}).get("date") or (commit.get("committer") or {}).get("date")
    committed_at = (
        datetime.fromisoformat(committed_iso.replace("Z", "+00:00")) if committed_iso else datetime.now(timezone.utc)
    )
    return CommitEvent(
        sha=sha,
        message=message,
        author=author,
        branch=branch,
        committed_at=committed_at,
    )


def parse_merge_pr(item: dict[str, Any], base_fallback: str = "main") -> MergeEvent:
    number = item.get("number") or 0
    title = item.get("title") or ""
    merged_by = ((item.get("merged_by") or {}) or {}).get("login") or "bot"
    merged_at_iso = item.get("merged_at")
    merged_at = (
        datetime.fromisoformat(merged_at_iso.replace("Z", "+00:00")) if merged_at_iso else datetime.now(timezone.utc)
    )
    base_branch = ((item.get("base") or {}) or {}).get("ref") or base_fallback
    return MergeEvent(
        number=number,
        title=title,
        merged_by=merged_by,
        merged_at=merged_at,
        base_branch=base_branch,
    )


def parse_tag(item: dict[str, Any]) -> TagEvent:
    name = item.get("name") or ""
    sha = (item.get("commit") or {}).get("sha") or ""
    # No tag date in tags API; caller should enrich with commit date if needed.
    tagged_at = datetime.now(timezone.utc)
    return TagEvent(name=name, sha=sha, tagged_at=tagged_at)


# ---------- Aggregation ----------


def in_window(ts: datetime, window_utc: tuple[datetime, datetime]) -> bool:
    start, end = window_utc
    return (ts >= start) and (ts < end)


def build_digest(
    date_kyiv: date,
    *,
    commits: Iterable[CommitEvent],
    merges: Iterable[MergeEvent],
    tags: Iterable[TagEvent],
) -> Digest:
    window = kyiv_day_bounds(date_kyiv)
    c = [x for x in commits if in_window(x.committed_at, window)]
    m = [x for x in merges if in_window(x.merged_at, window)]
    t = [x for x in tags if in_window(x.tagged_at, window)]
    return Digest(date_kyiv=date_kyiv, window_utc=window, commits=c, merges=m, tags=t)


# ---------- Rendering ----------


def render_text_report(d: Digest) -> str:
    start, end = d.window_utc
    lines: list[str] = []
    lines.append("🗞️ GitHub Daily Digest")
    lines.append(f"Date (Kyiv): {d.date_kyiv.isoformat()}")
    lines.append(f"UTC window: {start.isoformat()} → {end.isoformat()}")
    s = d.stats
    lines.append(f"Stats: commits={s['commits']} | merges={s['merges']} | tags={s['tags']}")
    if d.merges:
        lines.append("\nMerged PRs:")
        for pr in d.merges:
            lines.append(f"  • #{pr.number} {pr.title} (by {pr.merged_by}, base {pr.base_branch})")
    if d.tags:
        lines.append("\nTags:")
        for tag in d.tags:
            lines.append(f"  • {tag.name} ({tag.sha[:7]})")
    if d.commits:
        lines.append("\nCommits:")
        for c in d.commits[:10]:
            msg = c.message.splitlines()[0]
            lines.append(f"  • {c.sha[:7]} [{c.branch}] {msg} (by {c.author})")
        if len(d.commits) > 10:
            lines.append(f"  … and {len(d.commits) - 10} more commits")
    return "\n".join(lines)
