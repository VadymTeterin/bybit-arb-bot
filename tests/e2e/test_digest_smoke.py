import json
import subprocess
import sys


def test_digest_smoke_script_runs(tmp_path):
    out_md = tmp_path / "digest.md"
    out_json = tmp_path / "digest.json"

    result = subprocess.run(
        [
            sys.executable,
            "tools/digest_smoke.py",
            "--out",
            str(out_md),
            "--json",
            str(out_json),
            "--limit",
            "3",
        ],
        text=True,
    )
    assert result.returncode == 0
    assert out_md.exists(), "Markdown digest file was not created."

    text = out_md.read_text(encoding="utf-8")
    assert "E2E Smoke" in text
    assert "Recent commits" in text

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "repo" in data and "commits" in data
    assert isinstance(data["commits"], list)
