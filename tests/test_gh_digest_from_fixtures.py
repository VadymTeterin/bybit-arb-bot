# tests/test_gh_digest_from_fixtures.py
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from src.reports.gh_digest import (
    build_digest,
    kyiv_day_bounds,
    parse_commit,
    parse_merge_pr,
    parse_tag,
)

FIXT = Path("tests/fixtures/gh")


def test_build_digest_from_fixture_payloads():
    d = date(2025, 8, 22)
    start_utc, end_utc = kyiv_day_bounds(d)

    commits_raw = json.loads((FIXT / "commits.sample.json").read_text(encoding="utf-8"))
    pulls_raw = json.loads((FIXT / "pulls.sample.json").read_text(encoding="utf-8"))
    tags_raw = json.loads((FIXT / "tags.sample.json").read_text(encoding="utf-8"))

    commits = [parse_commit(c) for c in commits_raw]

    merges = []
    for p in pulls_raw:
        if p.get("merged_at"):
            merges.append(parse_merge_pr(p))

    # For tags we need commit date; emulate commit lookup by setting tagged_at inside window
    tags = []
    for t in tags_raw:
        te = parse_tag(t)
        te.tagged_at = start_utc + timedelta(hours=12)  # middle of the kyiv window
        tags.append(te)

    digest = build_digest(d, commits=commits, merges=merges, tags=tags)
    assert digest.stats["commits"] == 2
    assert digest.stats["merges"] == 1
    assert digest.stats["tags"] == 1
