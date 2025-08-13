# tests/test_alerts_preview.py
import subprocess
import sys
import re


def test_alerts_preview_runs():
    result = subprocess.run(
        [
            sys.executable, "-m", "src.main", "alerts:preview",
            "--symbol", "BTCUSDT",
            "--spot", "50000",
            "--mark", "50500",
            "--min-vol", "1000000",
            "--threshold", "0.5",
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "BTCUSDT" in result.stdout
    # має містити basis у відсотках
    assert re.search(r"basis=\+?[\d\.]+%", result.stdout) or "Top 1 basis" in result.stdout
