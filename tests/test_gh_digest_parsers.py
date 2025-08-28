# tests/test_gh_digest_parsers.py
# Offline tests for GH digest scaffolding (no network)
from __future__ import annotations

from datetime import date, timedelta

from src.reports.gh_digest import (
    CommitEvent,
    MergeEvent,
    TagEvent,
    build_digest,
    kyiv_day_bounds,
    render_text_report,
)


def test_kyiv_day_bounds_basic():
    d = date(2025, 8, 22)
    start_utc, end_utc = kyiv_day_bounds(d)
    # Sanity: window is 24h in UTC
    assert (end_utc - start_utc) == timedelta(days=1)
    # Must be timezone-aware UTC datetimes
    assert start_utc.tzinfo is not None and start_utc.tzinfo.utcoffset(start_utc) == timedelta(0)
    assert end_utc.tzinfo is not None and end_utc.tzinfo.utcoffset(end_utc) == timedelta(0)


def test_digest_aggregation_and_rendering():
    d = date(2025, 8, 22)
    start_utc, end_utc = kyiv_day_bounds(d)
    mid = start_utc + (end_utc - start_utc) / 2

    commits = [
        CommitEvent(
            sha="aaa1111",
            message="Initial commit",
            author="alice",
            branch="main",
            committed_at=mid,
        ),
        CommitEvent(
            sha="bbb2222",
            message="Merge pull request #5 from feature/x",
            author="bob",
            branch="main",
            committed_at=mid,
        ),
    ]
    merges = [
        MergeEvent(
            number=5,
            title="feature: x ready",
            merged_by="alice",
            merged_at=mid,
            base_branch="main",
        ),
    ]
    tags = [
        TagEvent(name="v1.0.0", sha="ccc3333", tagged_at=mid),
    ]

    digest = build_digest(d, commits=commits, merges=merges, tags=tags)
    assert digest.stats["commits"] == 2
    assert digest.stats["merges"] == 1
    assert digest.stats["tags"] == 1

    text = render_text_report(digest)
    assert "GitHub Daily Digest" in text
    assert "commits=2" in text
    assert "#5 feature: x ready" in text
    assert "v1.0.0 (ccc3333" in text  # short sha check
