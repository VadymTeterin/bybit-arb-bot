@echo off
REM bybit-arb-bot: launcher_export.cmd
REM Purpose: run project CLI with forwarded args on Windows.
setlocal EnableExtensions EnableDelayedExpansion

REM Change dir to the script's folder (handles different drive letters)
cd /d %~dp0

REM Ensure logs directory exists (required by tests)
if not exist logs mkdir logs

REM Prefer virtualenv Python if present
set "PY_EXE=python"
if exist ".venv\Scripts\python.exe" (
  set "PY_EXE=.venv\Scripts\python.exe"
)

REM Export script path (explicit string required by tests)
set "EXPORT_SCRIPT=scripts\export_signals.py"

REM If export script exists and no args provided, run it by default with log redirection
if exist "%EXPORT_SCRIPT%" (
  if "%~1"=="" (
    %PY_EXE% "%EXPORT_SCRIPT%" >> logs\export.log 2>&1
    set "EXITCODE=%ERRORLEVEL%"
    endlocal & exit /b %EXITCODE%
  )
)

REM Otherwise, forward all arguments to the CLI entrypoint
%PY_EXE% -m src.main %*
set "EXITCODE=%ERRORLEVEL%"

endlocal & exit /b %EXITCODE%
