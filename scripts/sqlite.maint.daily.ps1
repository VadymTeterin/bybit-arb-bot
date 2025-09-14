# scripts/sqlite.maint.daily.ps1
# Purpose: Daily maintenance runner: retention then incremental compact, with logging.
param(
    [string]$DbPath = "data\signals.db",
    [string]$Strategy = "incremental",
    [int]$MaxDurationSec = 60
)

# Resolve repo root & logs dir
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Resolve-Path (Join-Path $ScriptDir "..")
$LogsDir   = Join-Path $RepoRoot "logs"
if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null }
$LogFile   = Join-Path $LogsDir "sqlite_maint.log"

# Pick python (venv if exists)
$python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

# Sensible ENV defaults
if (-not $env:SQLITE_MAINT_ENABLE)           { $env:SQLITE_MAINT_ENABLE = "1" }
if (-not $env:SQLITE_DB_PATH)                { $env:SQLITE_DB_PATH = $DbPath }
if (-not $env:SQLITE_MAINT_VACUUM_STRATEGY)  { $env:SQLITE_MAINT_VACUUM_STRATEGY = $Strategy }
if (-not $env:SQLITE_MAINT_MAX_DURATION_SEC) { $env:SQLITE_MAINT_MAX_DURATION_SEC = "$MaxDurationSec" }

function Write-Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format s), $msg
    $line | Tee-Object -FilePath $LogFile -Append
}

Write-Log "SQLiteMaint START db=$($env:SQLITE_DB_PATH) strategy=$($env:SQLITE_MAINT_VACUUM_STRATEGY)"

# Phase 1: retention-only
$cmd1 = "& `"$python`" -m scripts.sqlite_maint --db `"$($env:SQLITE_DB_PATH)`" --execute --retention-only"
Write-Log "RUN: $cmd1"
$ret1 = & $python -m scripts.sqlite_maint --db $env:SQLITE_DB_PATH --execute --retention-only 2>&1
$ret1 | Tee-Object -FilePath $LogFile -Append | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: retention-only failed with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Phase 2: compact-only (incremental)
$cmd2 = "& `"$python`" -m scripts.sqlite_maint --db `"$($env:SQLITE_DB_PATH)`" --execute --compact-only"
Write-Log "RUN: $cmd2"
$ret2 = & $python -m scripts.sqlite_maint --db $env:SQLITE_DB_PATH --execute --compact-only 2>&1
$ret2 | Tee-Object -FilePath $LogFile -Append | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: compact-only failed with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Log "SQLiteMaint DONE"
