# scripts/update_project_tree.py
# Генерує текстове дерево проєкту (Windows PowerShell).
# Запуск із кореня:
#   python .\scripts\update_project_tree.py
# Необов'язково:
#   python .\scripts\update_project_tree.py --out .\project-tree.txt

from __future__ import annotations

import argparse
import os
from pathlib import Path

# Каталоги, які пропускаємо
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dev/tmp",
    "logs",
    "exports",
    ".backups",
}

# Глоб-патерни файлів, які пропускаємо
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


def should_skip_dir(rel: Path) -> bool:
    parts = list(rel.parts)
    for i in range(1, len(parts) + 1):
        sub = Path(*parts[:i]).as_posix()
        if sub in SKIP_DIRS:
            return True
    return False


def should_skip_file(rel: Path) -> bool:
    name = rel.name
    for pattern in SKIP_FILE_GLOBS:
        if rel.match(pattern) or Path(name).match(pattern):
            return True
    return False


def build_tree(root: Path) -> list[str]:
    lines: list[str] = []
    lines.append("Folder PATH listing")
    lines.append(f"ROOT: {root.resolve()}")
    # Перший рівень: показуємо файли/теки в корені (відсортовано)
    for item in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        rel = item.relative_to(root)
        if item.is_dir():
            if should_skip_dir(rel):
                continue
            lines.append(f"{rel.as_posix()}/")
            for subpath, dirs, files in os.walk(item):
                sub_rel = Path(subpath).relative_to(root)
                if should_skip_dir(sub_rel):
                    dirs[:] = []  # не спускаємося далі
                    continue
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
            if should_skip_file(rel):
                continue
            lines.append(rel.as_posix())
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Шлях до вихідного файлу (за замовчуванням: dev/tmp/project-tree.txt)",
    )
    args = parser.parse_args()

    root = Path.cwd()
    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = root / out_path
    else:
        out_path = root / "dev" / "tmp" / "project-tree.txt"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = build_tree(root)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] Wrote {out_path} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
