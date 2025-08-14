@echo off
setlocal

REM Change to the script's directory
cd /d %~dp0

REM Ensure logs folder exists
if not exist logs mkdir logs

REM Run export_signals.py using venv Python
.\.venv\Scripts\python.exe scripts\export_signals.py --last-hours 24 --keep 14 >> logs\export.log 2>&1

endlocal
