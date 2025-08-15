# tests/test_alerts_preview.py
import subprocess
import sys


def test_alerts_preview_runs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.main",
            "alerts:preview",
            "--symbol",
            "BTCUSDT",
            "--spot",
            "50000",
            "--mark",
            "50500",
            "--threshold",
            "0.5",
            "--vol",
            "3000000",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "BTCUSDT" in (result.stdout or "") or "Top" in (result.stdout or "")
