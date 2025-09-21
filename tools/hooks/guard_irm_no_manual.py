#!/usr/bin/env python3
import re, sys, subprocess

# Treat staged file list as source of truth
def staged_files():
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        text=True, encoding="utf-8", errors="replace"
    )
    return [p.strip().replace("\\", "/") for p in out.splitlines() if p.strip()]

def main() -> int:
    files = staged_files()
    changed_irm = "docs/IRM.md" in files
    # allow any docs/irm.phaseN.yaml (N is digits), .yaml or .yml
    yaml_pat = re.compile(r"^docs/irm\.phase[0-9]+\.ya?ml$")
    changed_yaml = any(yaml_pat.fullmatch(p) for p in files)

    if changed_irm and not changed_yaml:
        msg = (
            "ERROR: Manual edits to docs/IRM.md are not allowed.\n"
            "Commit must include matching docs/irm.phaseX.yaml and a re-generation step.\n"
            "Examples:\n"
            "  python tools/irm_phase7_gen.py --write   # for Phase 7\n"
            "  python tools/irm_phase6_gen.py --write --phase 6.3  # for Phase 6\n"
            "Then commit BOTH YAML and the generated IRM.md."
        )
        print(msg, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
