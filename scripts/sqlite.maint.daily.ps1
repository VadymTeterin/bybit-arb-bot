# scripts/sqlite.maint.daily.ps1
# Purpose: Run SQLite maintenance in two phases: retention-only then compact-only.
# Changes in this patch:
#  - Set-Location to the repo root (so relative paths resolve)
#  - Build absolute DB path from env var or default
#  - Use direct script path (no `-m`) to avoid ModuleNotFoundError
#  - Force UTF-8 for Python I/O to avoid UnicodeEncodeError
#  - Log to logs/sqlite_maint.log

param()

$ErrorActionPreference = 'Stop'

# Resolve repo root and key paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path $ScriptDir -Parent
Set-Location -Path $RepoRoot

$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$CliScript = Join-Path $RepoRoot "scripts\sqlite_maint.py"
$LogDir    = Join-Path $RepoRoot "logs"
$LogFile   = Join-Path $LogDir  "sqlite_maint.log"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Write-Log([string]$msg) {
    $ts = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    $line = "[{0}] {1}" -f $ts, $msg
    $line | Tee-Object -FilePath $LogFile -Append
}

# Defaults
if (-not $env:SQLITE_DB_PATH) { $env:SQLITE_DB_PATH = "data\signals.db" }

# Build absolute DB path even if env var is relative
$DBPath = $env:SQLITE_DB_PATH
if (-not [System.IO.Path]::IsPathRooted($DBPath)) {
    $DBPath = Join-Path $RepoRoot $DBPath
}

if (-not $env:SQLITE_MAINT_ENABLE) { $env:SQLITE_MAINT_ENABLE = "1" } # Allow execute in scheduled runs

# Force UTF-8 for Python I/O and PowerShell console/file sink
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}

Write-Log ("SQLiteMaint START db={0} strategy=incremental" -f $DBPath)

# Phase 1: Retention-only
$cmd1 = @(
    "`"$PythonExe`"",
    "`"$CliScript`"",
    "--db", "`"$DBPath`"",
    "--execute",
    "--retention-only"
) -join ' '

Write-Log ("RUN: & {0}" -f $cmd1)
$LASTEXITCODE = 0
& $PythonExe $CliScript --db $DBPath --execute --retention-only 2>&1 | Tee-Object -FilePath $LogFile -Append
$ret1 = $LASTEXITCODE
if ($ret1 -ne 0) {
    Write-Log ("ERROR: retention-only failed with code {0}" -f $ret1)
    exit $ret1
}

# Phase 2: Compact-only
$cmd2 = @(
    "`"$PythonExe`"",
    "`"$CliScript`"",
    "--db", "`"$DBPath`"",
    "--execute",
    "--compact-only"
) -join ' '

Write-Log ("RUN: & {0}" -f $cmd2)
$LASTEXITCODE = 0
& $PythonExe $CliScript --db $DBPath --execute --compact-only 2>&1 | Tee-Object -FilePath $LogFile -Append
$ret2 = $LASTEXITCODE
if ($ret2 -ne 0) {
    Write-Log ("ERROR: compact-only failed with code {0}" -f $ret2)
    exit $ret2
}

Write-Log "SQLiteMaint DONE"
exit 0
