#!/usr/bin/env python3
"""
IRM Phase 6 generator (SSOT-lite) with guard healing
- Single source of truth: docs/irm.phase6.yaml
- Renders a block for requested Phase (e.g., 6.2, 6.3) and injects it into docs/IRM.md
- Modes:
    --check : exit 1 if IRM.md needs update
    --write : update IRM.md in-place
- Windows-friendly (forces UTF-8 on stdio)
"""

from __future__ import annotations

import argparse
import difflib
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# -------- paths / constants --------
ROOT = Path(__file__).resolve().parents[1]
IRM_MD = ROOT / "docs" / "IRM.md"
YAML_PATH = ROOT / "docs" / "irm.phase6.yaml"
DEFAULT_PHASE = "6.2"


def _ensure_utf8_stdio() -> None:
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if not stream:
            continue
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            try:
                buffer = stream.buffer  # type: ignore[attr-defined]
            except Exception:
                continue
            wrapper = io.TextIOWrapper(buffer, encoding="utf-8", errors="replace")
            setattr(sys, name, wrapper)


_ensure_utf8_stdio()

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    print("Please install pyyaml: pip install pyyaml", file=sys.stderr)
    raise


@dataclass
class Section:
    id: str
    name: str
    status: str
    tasks: list[str]


# -------- yaml loading (single-source) --------
def load_yaml(phase: str | None = None) -> dict:
    """
    Single-source mode: docs/irm.phase6.yaml

    Supported layouts:
      1) New (preferred):
         phases:
           "6.2": { title, updated_utc, status_legend, sections: [...] }
           "6.3": { ... }
      2) Legacy single-phase (root keys):
         { phase: "6.2", title, updated_utc, status_legend, sections: [...] }
    """
    if not YAML_PATH.exists():
        raise FileNotFoundError(str(YAML_PATH))

    data_all = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    if not isinstance(data_all, dict):
        raise ValueError("Invalid YAML structure (root object)")

    # Multi-phase layout
    if "phases" in data_all and isinstance(data_all["phases"], dict):
        phases = data_all["phases"]
        chosen = phase or DEFAULT_PHASE
        if chosen not in phases:
            raise KeyError(f"Phase '{chosen}' not found; available: {list(phases.keys())}")
        out = dict(phases[chosen])  # shallow copy
        out.setdefault("phase", str(chosen))
        return out

    # Legacy single-phase layout
    out = dict(data_all)  # shallow copy
    out.setdefault("phase", str(phase or out.get("phase") or DEFAULT_PHASE))
    return out


# -------- rendering / splicing --------
def render_markdown(data: dict) -> str:
    """Render Phase block as Markdown (without sentinels)."""
    phase = str(data.get("phase") or DEFAULT_PHASE)
    title = str(data.get("title", "")).strip()
    updated = str(data.get("updated_utc", "")).strip()
    sections = [Section(**s) for s in data.get("sections", [])]

    out: list[str] = []
    out.append(f"### Фаза {phase} — {title}")
    if updated:
        out.append(f"> Оновлено: {updated}")
    out.append("")
    legend = data.get("status_legend", {})
    if legend:
        out.append("_Статуси_: " + ", ".join(f"**{k}** — {v}" for k, v in legend.items()))
        out.append("")
    for s in sections:
        out.append(f"- [{'x' if s.status == 'done' else ' '}] **{s.id} — {s.name}**  `status: {s.status}`")
        if s.tasks:
            for t in s.tasks:
                out.append(f"  - [ ] {t}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _sentinels(phase: str) -> tuple[str, str, re.Pattern[str], re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    begin = f"<!-- IRM:BEGIN {phase} -->"
    end = f"<!-- IRM:END {phase} -->"
    begin_line_re = re.compile(rf"(?m)^\s*<!-- IRM:BEGIN {re.escape(phase)} -->\s*$")
    end_line_re = re.compile(rf"(?m)^\s*<!-- IRM:END {re.escape(phase)} -->\s*$")
    block_re = re.compile(
        rf"(?ms)^\s*<!-- IRM:BEGIN {re.escape(phase)} -->\s*$.*?^\s*<!-- IRM:END {re.escape(phase)} -->\s*$"
    )
    header_re = re.compile(rf"^###\s+Фаза\s+{re.escape(phase)}\b.*$", re.MULTILINE)
    return begin, end, begin_line_re, end_line_re, block_re, header_re


def _wrap_block(begin: str, end: str, new_block: str) -> str:
    return f"{begin}\n{new_block}\n{end}\n"


def _heal_duplicates(full_md: str, phase: str, new_block: str) -> str:
    """
    If multiple <phase> sentinel blocks exist, collapse the range from
    FIRST BEGIN to LAST END into one fresh block.
    """
    _, _, BEGIN_LINE_RE, END_LINE_RE, _, _ = _sentinels(phase)
    begins = list(BEGIN_LINE_RE.finditer(full_md))
    ends = list(END_LINE_RE.finditer(full_md))
    if len(begins) >= 1 and len(ends) >= 1 and (
        len(begins) > 1 or len(ends) > 1 or begins[0].start() > ends[-1].start()
    ):
        start = begins[0].start()
        stop = ends[-1].end()
        begin, end, *_ = _sentinels(phase)
        return full_md[:start] + _wrap_block(begin, end, new_block) + full_md[stop:]
    return full_md


def _extract_phase_from_block(new_block: str) -> str | None:
    """Parse phase like '6.2' from the block header line: '### Фаза 6.2 — ...'"""
    m = re.search(r"^###\s+Фаза\s+(\d+\.\d+)\b", new_block, re.MULTILINE)
    return m.group(1) if m else None


# --- NEW: prune a manual 6.3 checklist mistakenly left inside the previous (e.g., 6.2) block ---
def _prev_phase(phase: str) -> str | None:
    m = re.match(r"^(\d+)\.(\d+)$", phase)
    if not m:
        return None
    major, minor = int(m.group(1)), int(m.group(2))
    if minor <= 0:
        return None
    return f"{major}.{minor-1}"


def _prune_manual_summary_in_prev_block(full_md: str, phase: str) -> str:
    """
    Inside the previous phase block (e.g., 6.2), remove a manual checklist
    that announces next phase (e.g., '- [x] **6.3 — ...**' + its 5 known lines).
    This avoids a visible duplicate when we generate the real 6.3 section.
    """
    prev = _prev_phase(phase)
    if not prev:
        return full_md

    begin, end, _, _, BLOCK_RE, _ = _sentinels(prev)
    m = BLOCK_RE.search(full_md)
    if not m:
        return full_md

    block = full_md[m.start() : m.end()]

    # Header bullet for "6.3 — ..." (checked or unchecked)
    hdr_re = re.compile(rf"(?m)^\s*-\s\[[ xX]\]\s\*\*{re.escape(phase)}\b.*$")
    # The five follow-up lines we know from WA
    follow_res = [
        re.compile(r"(?m)^\s*-\s\[[ xX]\]\salerts_repo:"),
        re.compile(r"(?m)^\s*-\s\[[ xX]\]\salerts_hook:"),
        re.compile(r"(?m)^\s*-\s\[[ xX]\]\salerts\.py:"),
        re.compile(r"(?m)^\s*-\s\[[ xX]\]\stests:"),
        re.compile(r"(?m)^\s*-\s\[[ xX]\]\sdocs:"),
    ]

    lines = block.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        if hdr_re.match(lines[i]):
            # skip header
            i += 1
            # skip only known follow-up lines (do not touch other 6.2 tasks)
            while i < len(lines) and any(rx.match(lines[i]) for rx in follow_res):
                i += 1
            continue
        out.append(lines[i])
        i += 1

    pruned = "".join(out)
    return full_md[: m.start()] + pruned + full_md[m.end() :]


def splice_content(full_md: str, new_block: str, phase: str | None = None) -> str:
    """
    Replace/insert the <phase> block robustly.
    Back-compat: phase is optional; if not provided, infer from new_block header.
    """
    phase_txt = phase or _extract_phase_from_block(new_block) or DEFAULT_PHASE

    # prune stray manual summary of the target phase inside the previous block
    full_md = _prune_manual_summary_in_prev_block(full_md, phase_txt)

    begin, end, _, _, BLOCK_RE, HEADER_RE = _sentinels(phase_txt)
    wrapped = _wrap_block(begin, end, new_block)

    healed = _heal_duplicates(full_md, phase_txt, new_block)
    if healed is not full_md:
        full_md = healed

    if BLOCK_RE.search(full_md):
        return BLOCK_RE.sub(wrapped, full_md, count=1)

    m = HEADER_RE.search(full_md)
    if m:
        start = m.start()
        next_h3 = re.search(r"^###\s+", full_md[m.end():], re.MULTILINE)
        stop = m.end() + next_h3.start() if next_h3 else len(full_md)
        before = full_md[:start]
        after = full_md[stop:]
        return before + wrapped + after

    if not full_md.endswith("\n"):
        full_md += "\n"
    return full_md + "\n" + wrapped


# -------- CLI helpers (keep phase optional for back-compat) --------
def check_mode(phase: str | None) -> int:
    data = load_yaml(phase)
    new_block = render_markdown(data)
    phase_txt = str(data.get("phase") or DEFAULT_PHASE)

    if not IRM_MD.exists():
        print("docs/IRM.md not found.", file=sys.stderr)
        return 2
    full_md = IRM_MD.read_text(encoding="utf-8")
    effective = splice_content(full_md, new_block, phase_txt)
    if effective == full_md:
        print(f"IRM {phase_txt} up-to-date.")
        return 0
    diff = difflib.unified_diff(
        full_md.splitlines(keepends=True),
        effective.splitlines(keepends=True),
        fromfile="IRM.md (current)",
        tofile=f"IRM.md (expected {phase_txt})",
    )
    sys.stdout.writelines(diff)
    return 1


def write_mode(phase: str | None) -> int:
    data = load_yaml(phase)
    new_block = render_markdown(data)
    phase_txt = str(data.get("phase") or DEFAULT_PHASE)

    full_md = IRM_MD.read_text(encoding="utf-8") if IRM_MD.exists() else ""
    updated = splice_content(full_md, new_block, phase_txt)
    if updated != full_md:
        IRM_MD.write_text(updated, encoding="utf-8", newline="\n")
        print(f"IRM {phase_txt} updated.")
        return 0
    print(f"IRM {phase_txt} already up-to-date.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Phase 6 IRM from a single YAML (with guard healing)")
    ap.add_argument("--check", action="store_true", help="Check IRM diff; exit 1 if updates needed")
    ap.add_argument("--write", action="store_true", help="Write IRM updates in-place")
    ap.add_argument("--phase", default=None, help="Phase section to sync (e.g., 6.2, 6.3). Optional.")
    args = ap.parse_args()
    if args.check and args.write:
        print("Choose either --check or --write", file=sys.stderr)
        return 2
    if not args.check and not args.write:
        ap.print_help()
        return 2
    return check_mode(args.phase) if args.check else write_mode(args.phase)


if __name__ == "__main__":
    raise SystemExit(main())
