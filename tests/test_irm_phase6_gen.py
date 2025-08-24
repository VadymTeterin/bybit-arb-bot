# -*- coding: utf-8 -*-
# Basic smoke tests for IRM Phase 6 generator
import importlib.util
import sys
from pathlib import Path


def load_module(script_path: Path):
    # Create a spec and module object
    spec = importlib.util.spec_from_file_location("irm_phase6_gen", script_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)

    # IMPORTANT for Python 3.12 + dataclasses:
    # Register the module in sys.modules before exec_module, so that
    # dataclasses can resolve string annotations against the module.
    sys.modules[spec.name] = mod

    spec.loader.exec_module(mod)  # type: ignore
    return mod


def test_render_and_splice(tmp_path: Path):
    # Arrange: create a fake repo structure
    repo = tmp_path
    (repo / "docs").mkdir(parents=True)
    (repo / "tools").mkdir(parents=True)

    # Write minimal YAML
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

    # Copy generator (from repo)
    src = Path(__file__).parent.parent / "tools" / "irm_phase6_gen.py"
    dst = repo / "tools" / "irm_phase6_gen.py"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    # Load module from tmp location
    mod = load_module(dst)

    # Patch ROOT and paths to the temp repo
    mod.ROOT = repo
    mod.YAML_PATH = repo / "docs" / "irm.phase6.yaml"
    mod.IRM_MD = repo / "docs" / "IRM.md"

    # Prepare initial IRM.md
    initial = "# IRM\n\n## Фаза 6\n\n### Фаза 6.1 — ...\n\nContent...\n"
    mod.IRM_MD.write_text(initial, encoding="utf-8")

    # Generate block and splice
    block = mod.render_markdown(mod.load_yaml())
    updated = mod.splice_content(initial, block)

    # Assertions
    assert "<!-- IRM:BEGIN 6.2 -->" in updated
    assert "<!-- IRM:END 6.2 -->" in updated
    assert "Фаза 6.2 — SSOT-lite" in updated
