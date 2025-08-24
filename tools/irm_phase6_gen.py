#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRM Phase 6.2 generator (SSOT-lite)
- Reads docs/irm.phase6.yaml
- Produces a Markdown block for "Фаза 6.2" and injects it into docs/IRM.md
- Two modes:
    --check : exits with code 1 if IRM.md doesn't match generated block
    --write : updates IRM.md in-place
This script is Windows-friendly and does not rely on GNU tools.
"""

from __future__ import annotations

import argparse
import difflib
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


# --- Ensure UTF-8 stdio on Windows runners (cp1252 would fail on Cyrillic) ---
def _ensure_utf8_stdio() -> None:
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if not stream:
            continue
        try:
            # Python 3.7+: reconfigure available on text streams
            stream.reconfigure(encoding="utf-8")
        except Exception:
            # Fallback: wrap the underlying buffer
            try:
                buffer = stream.buffer  # type: ignore[attr-defined]
            except Exception:
                continue
            wrapper = io.TextIOWrapper(buffer, encoding="utf-8", errors="replace")
            setattr(sys, name, wrapper)


_ensure_utf8_stdio()
# ---------------------------------------------------------------------------

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    print("Please install pyyaml: pip install pyyaml", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "docs" / "irm.phase6.yaml"
IRM_MD = ROOT / "docs" / "IRM.md"

BEGIN = "<!-- IRM:BEGIN 6.2 -->"
END = "<!-- IRM:END 6.2 -->"
HEADER_RE = re.compile(r"^###\s+Фаза\s+6\.2\b.*$", re.MULTILINE)


@dataclass
class Section:
    id: str
    name: str
    status: str
    tasks: List[str]


def load_yaml() -> dict:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid YAML structure")
    return data


def render_markdown(data: dict) -> str:
    """Render the Phase 6.2 block as Markdown (without sentinels)."""
    title = data.get("title", "").strip()
    updated = data.get("updated_utc", "").strip()
    sections = [Section(**s) for s in data.get("sections", [])]
    out: List[str] = []
    out.append(f"### Фаза 6.2 — {title}")
    if updated:
        out.append(f"> Оновлено: {updated}")
    out.append("")
    legend = data.get("status_legend", {})
    if legend:
        out.append(
            "_Статуси_: " + ", ".join(f"**{k}** — {v}" for k, v in legend.items())
        )
        out.append("")
    for s in sections:
        out.append(
            f"- [{'x' if s.status == 'done' else ' '}] **{s.id} — {s.name}**  `status: {s.status}`"
        )
        if s.tasks:
            for t in s.tasks:
                out.append(f"  - [ ] {t}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def splice_content(full_md: str, new_block: str) -> str:
    """
    Return full_md with the 6.2 block replaced/inserted inside sentinels.
    If sentinels exist, replace content between them.
    Else, try to locate the '### Фаза 6.2' header and replace that section.
    Else, append at the end.
    """
    begin_idx = full_md.find(BEGIN)
    end_idx = full_md.find(END)
    wrapped = f"{BEGIN}\n{new_block}\n{END}\n"
    if begin_idx != -1 and end_idx != -1 and end_idx > begin_idx:
        # Replace existing sentinel block
        before = full_md[:begin_idx]
        after = full_md[end_idx + len(END) :]
        return before + wrapped + after
    # No sentinels — try header-based replace
    m = HEADER_RE.search(full_md)
    if m:
        start = m.start()
        # find next H3 header or end
        next_h3 = re.search(r"^###\s+", full_md[m.end() :], re.MULTILINE)
        if next_h3:
            stop = m.end() + next_h3.start()
        else:
            stop = len(full_md)
        before = full_md[:start]
        after = full_md[stop:]
        return before + wrapped + after
    # Append to the end
    if not full_md.endswith("\n"):
        full_md += "\n"
    return full_md + "\n" + wrapped


def check_mode() -> int:
    data = load_yaml()
    new_block = render_markdown(data)
    if not IRM_MD.exists():
        print("docs/IRM.md not found.", file=sys.stderr)
        return 2
    full_md = IRM_MD.read_text(encoding="utf-8")
    # Extract current effective block
    effective = splice_content(full_md, new_block)
    if effective == full_md:
        print("IRM up-to-date.")
        return 0
    # Show a unified diff for convenience
    diff = difflib.unified_diff(
        full_md.splitlines(keepends=True),
        effective.splitlines(keepends=True),
        fromfile="IRM.md (current)",
        tofile="IRM.md (expected)",
    )
    sys.stdout.writelines(diff)
    return 1


def write_mode() -> int:
    data = load_yaml()
    new_block = render_markdown(data)
    full_md = IRM_MD.read_text(encoding="utf-8") if IRM_MD.exists() else ""
    updated = splice_content(full_md, new_block)
    if updated != full_md:
        IRM_MD.write_text(updated, encoding="utf-8", newline="\n")
        print("IRM updated.")
        return 0
    print("IRM already up-to-date.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Phase 6.2 IRM from YAML")
    ap.add_argument(
        "--check", action="store_true", help="Check IRM diff; exit 1 if updates needed"
    )
    ap.add_argument("--write", action="store_true", help="Write IRM updates in-place")
    args = ap.parse_args()
    if args.check and args.write:
        print("Choose either --check or --write", file=sys.stderr)
        return 2
    if not args.check and not args.write:
        ap.print_help()
        return 2
    return check_mode() if args.check else write_mode()


if __name__ == "__main__":
    raise SystemExit(main())
