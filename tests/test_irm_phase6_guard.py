import importlib.util
import sys
from pathlib import Path


def load_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("irm_phase6_gen", script_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # for dataclasses on Py3.12
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def test_heal_duplicate_blocks(tmp_path: Path):
    repo = tmp_path
    (repo / "docs").mkdir(parents=True)
    (repo / "tools").mkdir(parents=True)

    # Minimal YAML to render a block
    (repo / "docs" / "irm.phase6.yaml").write_text(
        """\
phase: "6.2"
title: "SSOT-lite (автоматизація IRM)"
updated_utc: "2025-08-24T00:00:00Z"
sections:
  - id: "6.2.0"
    name: "Каркас"
    status: "done"
    tasks: ["ok"]
""",
        encoding="utf-8",
    )

    # Copy generator-under-test
    src = Path(__file__).parent.parent / "tools" / "irm_phase6_gen.py"
    dst = repo / "tools" / "irm_phase6_gen.py"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    mod = load_module(dst)
    mod.ROOT = repo
    mod.YAML_PATH = repo / "docs" / "irm.phase6.yaml"
    mod.IRM_MD = repo / "docs" / "IRM.md"

    # IRM with TWO 6.2 blocks ("noise" imitates historical leftovers)
    initial = """# IRM

## Фаза 6

<!-- IRM:BEGIN 6.2 -->
AAA
<!-- IRM:END 6.2 -->

...noise...

<!-- IRM:BEGIN 6.2 -->
BBB
<!-- IRM:END 6.2 -->
"""
    mod.IRM_MD.write_text(initial, encoding="utf-8")

    new_block = mod.render_markdown(mod.load_yaml())
    healed = mod.splice_content(initial, new_block)

    # After healing + splice: exactly one block remains
    assert healed.count("<!-- IRM:BEGIN 6.2 -->") == 1
    assert healed.count("<!-- IRM:END 6.2 -->") == 1

    # Idempotent on repeated call
    assert mod.splice_content(healed, new_block) == healed
