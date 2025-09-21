
# tests/test_irm_patterns.py
# Purpose: Ensure the generalized regex ^docs/(IRM\.view\.md|irm\.phase[0-9]+\.yaml)$
# covers all phase YAML files and does not include unrelated files.
import re
from pathlib import Path

REGEX = r'^docs/(IRM\.view\.md|irm\.phase[0-9]+\.yaml)$'
pattern = re.compile(REGEX)

def test_matches_all_phase_yaml_examples(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    # Create sample phase files for 0..12 (extendable without changing regex)
    samples = [f"irm.phase{i}.yaml" for i in range(0, 13)]
    for name in samples:
        p = docs / name
        p.write_text("phase: '{}'\n".format(name), encoding="utf-8")
        assert pattern.match(f"docs/{name}")

def test_matches_irm_view_only():
    assert pattern.match("docs/IRM.view.md")
    assert not pattern.match("docs/IRM.md")  # should be handled by another guard

def test_does_not_match_other_docs():
    # Negative cases — must not be picked by the hook
    negatives = [
        "docs/irm.phaseX.yaml",       # non-numeric suffix
        "docs/irm.phase.7.yaml",      # wrong dotted style
        "docs/irm.phase7.yml",        # different extension
        "docs/irm.phase7.yaml.bak",   # backup files
        "docs/ROADMAP.md",
        "README.md",
        "scripts/irm.phase7.yaml",
    ]
    for n in negatives:
        assert not pattern.match(n), f"Unexpected match for: {n}"
