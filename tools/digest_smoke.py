#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a pseudo "Daily Digest" artifact from the current repo state.
This is used for E2E smoke testing in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo


@dataclass
class CommitItem:
    sha: str
    date: str
    author: str
    subject: str


def run(cmd: List[str]) -> str:
    """Run a shell command and return stdout (stripped)."""
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout.strip()


def recent_commits(limit: int) -> List[CommitItem]:
    """
    Collect recent commits using git. ISO date for easy parsing.
    """
    fmt = "%h|%ad|%an|%s"
    out = run(
        ["git", "log", f"-n{limit}", f"--pretty=format:{fmt}", "--date=iso-strict"]
    )
    items: List[CommitItem] = []
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) != 4:
            # Skip malformed lines gracefully
            continue
        sha, date, author, subject = parts
        items.append(CommitItem(sha=sha, date=date, author=author, subject=subject))
    return items


def build_markdown(repo: str, branch: str, sha: str, commits: List[CommitItem]) -> str:
    """Render markdown digest."""
    now = datetime.now(ZoneInfo("Europe/Kyiv"))
    header = (
        f"# GitHub Daily Digest — E2E Smoke\n\n"
        f"- Generated: **{now.strftime('%Y-%m-%d %H:%M:%S %Z')}**\n"
        f"- Repo: **{repo}**\n"
        f"- Branch: **{branch}**\n"
        f"- Commit: **{sha[:7]}**\n\n"
        f"## Recent commits (last {len(commits)})\n"
        f"| SHA | Date | Author | Subject |\n"
        f"|-----|------|--------|---------|\n"
    )
    rows = []
    for c in commits:
        safe_subject = c.subject.replace("|", "\\|")
        rows.append(f"| {c.sha} | {c.date} | {c.author} | {safe_subject} |")
    notes = (
        "\n\n## Notes\n"
        "- This is a **pseudo-digest** generated in CI for smoke testing.\n"
        "- Artifacts: this `.md` and a companion `.json` with metadata.\n"
    )
    return header + "\n".join(rows) + notes


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pseudo daily digest.")
    parser.add_argument("--out", required=True, help="Path to output markdown file.")
    parser.add_argument(
        "--json", default="", help="Optional path to output JSON metadata."
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Number of recent commits to include."
    )
    args = parser.parse_args()

    out_md = Path(args.out)
    out_json = Path(args.json) if args.json else None
    out_md.parent.mkdir(parents=True, exist_ok=True)
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)

    repo = os.getenv("GITHUB_REPOSITORY", "local/repo")
    branch = os.getenv(
        "GITHUB_REF_NAME", run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    )
    sha = os.getenv("GITHUB_SHA", run(["git", "rev-parse", "HEAD"]))

    commits = recent_commits(limit=args.limit)
    md = build_markdown(repo=repo, branch=branch, sha=sha, commits=commits)
    out_md.write_text(md, encoding="utf-8")

    if out_json:
        payload = {
            "generated_at": datetime.now(ZoneInfo("Europe/Kyiv")).isoformat(),
            "repo": repo,
            "branch": branch,
            "sha": sha,
            "limit": args.limit,
            "commits": [asdict(c) for c in commits],
        }
        out_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"[digest_smoke] Wrote: {out_md}")
    if out_json:
        print(f"[digest_smoke] Wrote: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
