#!/usr/bin/env python3
"""
update_project_tree.py
---------------------------------
Generate a clean text tree of the repository into `project-tree.txt`.
Windows-friendly. Skips virtualenvs, caches, backups, and heavy/output dirs.

Usage (run from repo root):
  python scripts/update_project_tree.py
"""
from __future__ import annotations

import os
from pathlib import Path

# Directories to skip entirely
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".backups",
    "dev/tmp",
    "exports",
    "logs",
}

# Files to skip (globs)
SKIP_FILE_GLOBS = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    "*.bak",
    "*.tmp",
    "*.sqlite",
    "*.db",
}

OUT_FILE = "project-tree.txt"


def should_skip_dir(rel: Path) -> bool:
    # Skip if starts with any skip dir at any level
    parts = list(rel.parts)
    for i in range(1, len(parts) + 1):
        sub = Path(*parts[:i]).as_posix()
        if sub in SKIP_DIRS:
            return True
    return False


def should_skip_file(rel: Path) -> bool:
    name = rel.name
    for pattern in SKIP_FILE_GLOBS:
        if rel.match(pattern):
            return True
        if Path(name).match(pattern):
            return True
    return False


def build_tree(root: Path) -> list[str]:
    lines: list[str] = []
    lines.append(f"Folder PATH listing\nROOT: {root.resolve()}")
    # First level: show dotted files in root (like .env) and key files
    for item in sorted(root.iterdir(), key=lambda p: (p.is_dir() is False, p.name.lower())):
        rel = item.relative_to(root)
        if item.is_dir():
            if should_skip_dir(rel):
                continue
            lines.append(f"{rel.as_posix()}/")
            for subpath, dirs, files in os.walk(item):
                sub_rel = Path(subpath).relative_to(root)
                if should_skip_dir(sub_rel):
                    dirs[:] = []  # don't descend
                    continue
                # sort directories/files for stable output
                dirs.sort(key=lambda n: n.lower())
                files.sort(key=lambda n: n.lower())
                level = len(sub_rel.parts)
                prefix = "  " * level
                for d in dirs:
                    d_rel = sub_rel / d
                    if should_skip_dir(d_rel):
                        continue
                    lines.append(f"{prefix}{d_rel.as_posix()}/")
                for f in files:
                    f_rel = sub_rel / f
                    if should_skip_file(f_rel):
                        continue
                    lines.append(f"{prefix}{f_rel.as_posix()}")
        else:
            # file in root
            if should_skip_file(rel):
                continue
            lines.append(rel.as_posix())
    return lines


def main() -> None:
    here = Path.cwd()
    out = here / OUT_FILE
    lines = build_tree(here)
    text = "\n".join(lines) + "\n"
    out.write_text(text, encoding="utf-8")
    print(f"[OK] Wrote {out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
