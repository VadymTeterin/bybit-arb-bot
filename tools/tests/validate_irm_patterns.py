# tools/tests/validate_irm_patterns.py
import re
import sys
from pathlib import Path

REGEX = r'^docs/(IRM\.view\.md|irm\.phase[0-9]+\.yaml)$'
pattern = re.compile(REGEX)

def main(repo_root: Path) -> int:
    docs = repo_root / "docs"
    if not docs.exists():
        print("::warning:: docs/ directory not found  skipping pattern validation.")
        return 0
    phase_files = sorted(docs.glob("irm.phase*.yaml"))
    rc = 0
    for f in phase_files:
        rel = f.relative_to(repo_root).as_posix()
        if not pattern.match(rel):
            print(f"::error:: File does not match IRM hook pattern: {rel}")
            rc = 1
    print(f"Checked {len(phase_files)} IRM YAML files with pattern {REGEX}")
    return rc

if __name__ == '__main__':
    sys.exit(main(Path(__file__).resolve().parents[2]))
