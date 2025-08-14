from __future__ import annotations
import sys
import re
import subprocess
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
    assert r".\.venv\Scripts\python.exe" in content, "launcher should run venv python"
    assert r"scripts\export_signals.py" in content, "launcher should call export_signals.py"
    assert r">> logs\export.log 2>&1" in content.replace("  ", " "), "launcher should redirect output to logs/export.log"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
def test_launcher_cmd_executes_in_its_own_dir(tmp_path: Path):
    # Оригінальний файл лаунчера
    src_cmd = PROJECT_ROOT / "launcher_export.cmd"
    assert src_cmd.exists(), "launcher_export.cmd not found at project root"

    original = src_cmd.read_text(encoding="utf-8", errors="ignore")

    # Підмінимо лише рядок з python.exe  решту логіки лишаємо як є.
    pattern = re.compile(r'^\s*\.\\\.venv\\Scripts\\python\.exe.*$', flags=re.MULTILINE)

    # НАДІЙНА підміна: чистий cmd.exe створює ran.txt і щось пише в export.log
    replacement = r'cmd.exe /c "mkdir logs && echo ok>logs\ran.txt" >> logs\export.log 2>&1'

    # Використовуємо lambda, щоб re не трактував backslash-и як посилання на групи
    modified = pattern.sub(lambda m: replacement, original)

    # Запис тимчасового лаунчера
    tmp_cmd = tmp_path / "launcher_export.cmd"
    tmp_cmd.write_text(modified, encoding="utf-8")

    # Запуск через cmd.exe
    subprocess.run(
        ["cmd.exe", "/c", str(tmp_cmd)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Перевірки побічних ефектів
    ran_marker = tmp_path / "logs" / "ran.txt"
    log_file = tmp_path / "logs" / "export.log"

    assert ran_marker.exists(), "launcher should create logs\\ran.txt via the Python command"
    assert log_file.exists(), "launcher should create logs\\export.log via stdout/stderr redirection"
    assert ran_marker.read_text(encoding="utf-8").strip() == "ok"
