# Basic smoke tests for IRM Phase 6 generator
import importlib.util
import re
import sys
from pathlib import Path


def load_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("irm_phase6_gen", script_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Needed for Python 3.12 + dataclasses resolving string annotations
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def test_render_and_splice(tmp_path: Path):
    # Arrange
    repo = tmp_path
    (repo / "docs").mkdir(parents=True)
    (repo / "tools").mkdir(parents=True)

    (repo / "docs" / "irm.phase6.yaml").write_text(
        """\
phase: "6.2"
title: "SSOT-lite (автоматизація IRM)"
updated_utc: "2025-08-24T00:00:00Z"
sections:
  - id: "6.2.0"
    name: "Каркас"
    status: "todo"
    tasks: ["A", "B"]
""",
        encoding="utf-8",
    )
    src = Path(__file__).parent.parent / "tools" / "irm_phase6_gen.py"
    dst = repo / "tools" / "irm_phase6_gen.py"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    mod = load_module(dst)
    mod.ROOT = repo
    mod.YAML_PATH = repo / "docs" / "irm.phase6.yaml"
    mod.IRM_MD = repo / "docs" / "IRM.md"

    initial = "# IRM\n\n## Фаза 6\n\n### Фаза 6.1 — ...\n\nContent...\n"
    mod.IRM_MD.write_text(initial, encoding="utf-8")

    block = mod.render_markdown(mod.load_yaml())
    updated = mod.splice_content(initial, block)

    assert re.findall(r"(?m)^\s*<!-- IRM:BEGIN 6\.2 -->\s*$", updated)
    assert re.findall(r"(?m)^\s*<!-- IRM:END 6\.2 -->\s*$", updated)
    assert "Фаза 6.2 — SSOT-lite" in updated


def test_splice_with_inline_sentinel_mentions(tmp_path: Path):
    # Arrange
    repo = tmp_path
    (repo / "docs").mkdir(parents=True)
    (repo / "tools").mkdir(parents=True)

    # YAML contains a task that mentions BEGIN/END sentinel literally
    (repo / "docs" / "irm.phase6.yaml").write_text(
        """\
phase: "6.2"
title: "SSOT-lite (автоматизація IRM)"
updated_utc: "2025-08-24T00:00:00Z"
sections:
  - id: "6.2.1"
    name: "Інтеграція з docs/IRM.md (сентинели)"
    status: "todo"
    tasks:
      - "Додати/перевірити блок <!-- IRM:BEGIN 6.2 --> … <!-- IRM:END 6.2 -->"
""",
        encoding="utf-8",
    )

    src = Path(__file__).parent.parent / "tools" / "irm_phase6_gen.py"
    dst = repo / "tools" / "irm_phase6_gen.py"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    mod = load_module(dst)
    mod.ROOT = repo
    mod.YAML_PATH = repo / "docs" / "irm.phase6.yaml"
    mod.IRM_MD = repo / "docs" / "IRM.md"

    # Initial IRM already has a 6.2 sentinel block placeholder
    initial = """# IRM

## Фаза 6

<!-- IRM:BEGIN 6.2 -->
### Фаза 6.2 — Placeholder
<!-- IRM:END 6.2 -->
"""
    mod.IRM_MD.write_text(initial, encoding="utf-8")

    block = mod.render_markdown(mod.load_yaml())
    once = mod.splice_content(initial, block)
    twice = mod.splice_content(once, block)  # idempotency

    # Exactly one BEGIN line and one END line — even if sentinel strings appear inline in tasks
    assert len(re.findall(r"(?m)^\s*<!-- IRM:BEGIN 6\.2 -->\s*$", once)) == 1
    assert len(re.findall(r"(?m)^\s*<!-- IRM:END 6\.2 -->\s*$", once)) == 1
    assert twice == once
