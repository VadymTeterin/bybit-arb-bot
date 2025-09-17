# tools/hooks/guard_irm_no_manual.py
import subprocess
import sys

def staged_files():
    try:
        p = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            check=True, capture_output=True, text=True
        )
    except Exception as e:
        sys.stderr.write(f"ERROR: cannot query staged files: {e}\n")
        return []

    files = [ln.strip().replace("\\", "/") for ln in p.stdout.splitlines() if ln.strip()]
    return files

def main():
    files = staged_files()
    irm = "docs/IRM.md"
    yaml = "docs/irm.phase6.yaml"

    if irm in files and yaml not in files:
        sys.stderr.write(
            "ERROR: Manual edits to docs/IRM.md are not allowed.\n"
            "Please modify 'docs/irm.phase6.yaml' and re-generate via:\n"
            "  python tools/irm_phase6_gen.py --write --phase 6.3\n"
            "Then commit both YAML and generated IRM.md.\n"
        )
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
