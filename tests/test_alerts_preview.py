import subprocess
import sys

def test_alerts_preview_runs():
    result = subprocess.run(
        [
            sys.executable, "-m", "src.main", "alerts:preview",
            "--symbol", "BTCUSDT",
            "--spot", "50000",
            "--mark", "50500",
            "--vol", "3000000",
            "--threshold", "0.5",
            "--min-vol", "1000000"
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "BTCUSDT" in result.stdout
    assert "basis" in result.stdout
