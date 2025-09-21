#!/usr/bin/env python3
"""IRM Phase 7 generator (structured splice).

- Source: docs/irm.phase7.yaml
- Goal: insert Phase 7.0 block into docs/IRM.md inside the section
  "### Подальші фази (укрупнено)", right after bullet "7 — ...".
- Idempotent: removes any existing <!-- IRM:BEGIN 7.0 --> ... <!-- IRM:END 7.0 -->.
- Modes:
    --check : exit 0 if IRM.md already matches, else 1
    --write : update IRM.md in place
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IRM_MD = ROOT / "docs" / "IRM.md"
YAML_PATH = ROOT / "docs" / "irm.phase7.yaml"
PHASE_STR = "7.0"

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("Please install pyyaml: pip install pyyaml") from exc

# ---------------- YAML ----------------
def load_phase_yaml() -> dict[str, Any]:
    raw = YAML_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    # allow {phases: {7.0: {...}}} or a single-phase mapping
    if "phases" in data and isinstance(data["phases"], dict):
        phases = data["phases"]
        if "7.0" in phases:
            node = dict(phases["7.0"])
        else:
            keys = sorted(k for k in phases if str(k).startswith("7."))
            if not keys:
                raise ValueError("No 7.x phase found under phases")
            node = dict(phases[keys[0]])
        node.setdefault("phase", "7.0")
        return node
    node = dict(data)
    node.setdefault("phase", "7.0")
    return node

# -------------- RENDER ---------------
def render_markdown(d: dict[str, Any]) -> str:
    title = "Фаза 7.0 —"
    sections = d.get("sections") or []
    out: list[str] = []
    out.append(f"### {title}")
    out.append("")
    out.append("_Статуси_: **todo** — заплановано, **wip** — в роботі, **done** — завершено")
    out.append("")
    for sec in sections:
        sid = str(sec.get("id", "")).strip()
        name = str(sec.get("name", "")).strip()
        status = str(sec.get("status", "todo")).strip()
        checkbox = "x" if status == "done" else " "
        out.append(f"- [{checkbox}] **{sid} — {name}**  `status: {status}`")
        for t in (sec.get("tasks") or []):
            out.append(f"  - [ ] {t}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"

def wrap_sentinels(body: str) -> str:
    return f"<!-- IRM:BEGIN {PHASE_STR} -->\n{body}\n<!-- IRM:END {PHASE_STR} -->\n"

# -------------- SPLICING -------------
RE_BLOCK = re.compile(r"<!--\s*IRM:BEGIN\s*7\.0\s*-->.*?<!--\s*IRM:END\s*7\.0\s*-->\s*", re.S)
RE_HDR_FUTURE = re.compile(r"(?mi)^\s*###\s*Подальші фази.*$")
RE_NEXT_HDR = re.compile(r"(?m)^\s*###\s+")
RE_BULLET7 = re.compile(r"(?mi)^\s*-\s*\[[^\]]*\]\s*7\s*[\-—–]\s.*$")

def splice(text: str, block: str) -> str:
    text = RE_BLOCK.sub("", text)
    hdr = RE_HDR_FUTURE.search(text)
    if not hdr:
        return text.rstrip() + "\n\n" + block
    start = hdr.end()
    nxt = RE_NEXT_HDR.search(text, pos=start)
    end = nxt.start() if nxt else len(text)
    pre, mid, post = text[:start], text[start:end], text[end:]
    m7 = RE_BULLET7.search(mid)
    if m7:
        eol = mid.find("\n", m7.end())
        if eol == -1:
            eol = len(mid)
        mid_new = mid[: eol + 1].rstrip() + "\n\n" + block + "\n" + mid[eol + 1 :].lstrip()
    else:
        mid_new = mid.rstrip() + "\n\n" + block + "\n"
    return (pre + mid_new + post).rstrip() + "\n"

# --------------- MAIN ----------------
def build_expected() -> str:
    base = IRM_MD.read_text(encoding="utf-8")
    d = load_phase_yaml()
    body = render_markdown(d)
    block = wrap_sentinels(body)
    return splice(base, block)

def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Phase 7 IRM into 'Подальші фази' section")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    current = IRM_MD.read_text(encoding="utf-8")
    expected = build_expected()

    if args.check and not args.write:
        if current == expected:
            print("IRM.md is in sync for Phase 7.")
            return 0
        print("IRM.md is NOT in sync for Phase 7. Run with --write.")
        diff = difflib.unified_diff(current.splitlines(), expected.splitlines(),
                                    fromfile="IRM.md", tofile="IRM.md(expected)", lineterm="")
        for ln in diff:
            sys.stdout.write(ln + "\n")
        return 1

    if args.write:
        IRM_MD.write_text(expected, encoding="utf-8")
        print(f"Updated {IRM_MD}")
        return 0

    # default safe behavior
    if current == expected:
        print("IRM.md is in sync for Phase 7.")
        return 0
    print("IRM.md is NOT in sync for Phase 7. Run with --write.")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
