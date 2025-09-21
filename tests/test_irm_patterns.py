# tests/test_irm_patterns.py
# Purpose: Ensure the generalized regex ^docs/(IRM\.view\.md|irm\.phase[0-9]+\.yaml)$
# covers all phase YAML files and does not include unrelated files.
import re

REGEX = r'^docs/(IRM\.view\.md|irm\.phase[0-9]+\.yaml)$'
pattern = re.compile(REGEX)


def test_matches_all_phase_yaml_examples(tmp_path):
    """
    Create a docs/ dir with sample irm.phase{N}.yaml files for N=0..12 and
    ensure the pattern matches them all. This guards future phases without
    needing to edit the hook.
    """
    docs = tmp_path / "docs"
    docs.mkdir()
    # sample set can be extended easily without changing the regex
    samples = [f"irm.phase{i}.yaml" for i in range(0, 13)]
    for name in samples:
        p = docs / name
        p.write_text(f"phase: '{name}'\n", encoding="utf-8")
        assert pattern.match(f"docs/{name}"), f"Should match: docs/{name}"


def test_matches_irm_view_only():
    assert pattern.match("docs/IRM.view.md"), "Should match IRM.view.md"
    # IRM.md is governed by a separate guard; it must NOT be matched here
    assert not pattern.match("docs/IRM.md"), "Must NOT match IRM.md"


def test_does_not_match_other_docs():
    """
    Negative cases — must not be picked by the hook.
    """
    negatives = [
        "docs/irm.phaseX.yaml",       # non-numeric suffix
        "docs/irm.phase.7.yaml",      # wrong dotted style
        "docs/irm.phase7.yml",        # different extension
        "docs/irm.phase7.yaml.bak",   # backup file
        "docs/ROADMAP.md",
        "README.md",
        "scripts/irm.phase7.yaml",
    ]
    for n in negatives:
        assert not pattern.match(n), f"Unexpected match for: {n}"
