from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
def test_launcher_cmd_structure():
    cmd_path = PROJECT_ROOT / "launcher_export.cmd"
    assert cmd_path.exists(), "launcher_export.cmd not found at project root"

    content = cmd_path.read_text(encoding="utf-8", errors="ignore")

    # Очікуємо ключові конструкції для універсальності та стабільності
    assert "cd /d %~dp0" in content, "launcher must 'cd' to its own directory"
    assert "if not exist logs mkdir logs" in content.lower().replace("  ", " "), "launcher should ensure logs dir"
    assert "python.exe" in content.lower(), "launcher should run some python executable"
    assert r"scripts\export_signals.py" in content, "launcher should call export_signals.py"
    assert r">> logs\export.log 2>&1" in content.replace(
        "  ", " "
    ), "launcher should redirect output to logs/export.log"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
def test_launcher_cmd_executes_in_its_own_dir(tmp_path: Path):
    # Створюємо МІНІМАЛЬНИЙ тимчасовий cmd, який емулює ключову поведінку:
    # 1) cd /d %~dp0   перехід у каталог самого .cmd
    # 2) створення logs
    # 3) запис ran.txt та export.log
    tmp_cmd = tmp_path / "launcher_export.cmd"
    tmp_cmd.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "cd /d %~dp0\r\n"
        "mkdir logs >nul 2>&1\r\n"
        "echo ok > logs\\ran.txt\r\n"
        "echo launched >> logs\\export.log 2>&1\r\n"
        "endlocal\r\n",
        encoding="utf-8",
        newline="\r\n",
    )

    # Запуск через cmd.exe
    subprocess.run(
        ["cmd.exe", "/c", str(tmp_cmd)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Перевірки побічних ефектів у каталозі тимчасового .cmd
    ran_marker = tmp_path / "logs" / "ran.txt"
    log_file = tmp_path / "logs" / "export.log"

    assert ran_marker.exists(), "launcher (cd /d %~dp0) should create logs\\ran.txt in its own directory"
    assert log_file.exists(), "launcher should create logs\\export.log via stdout/stderr redirection"
    assert ran_marker.read_text(encoding="utf-8").strip() == "ok"
