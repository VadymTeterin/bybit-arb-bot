# scripts/sqlite.maint.ps1
# Purpose: Windows-friendly wrapper for SQLite maintenance CLI
# Notes: No secrets printed. Run from repo root. Uses current venv if active.

param(
    [switch]$Execute = $false,
    [string]$DbPath = "data/signals.db",
    [string]$Strategy = $env:SQLITE_MAINT_VACUUM_STRATEGY
)

if (-not $Strategy -or $Strategy -eq "") {
    $Strategy = "incremental"
}

# Sensible defaults (can be overridden via ENV before invoking this script)
if (-not $env:SQLITE_MAINT_ENABLE) { $env:SQLITE_MAINT_ENABLE = "0" }
if (-not $env:SQLITE_RETENTION_SIGNALS_DAYS) { $env:SQLITE_RETENTION_SIGNALS_DAYS = "14" }
if (-not $env:SQLITE_RETENTION_ALERTS_DAYS)  { $env:SQLITE_RETENTION_ALERTS_DAYS  = "30" }
if (-not $env:SQLITE_RETENTION_QUOTES_DAYS)  { $env:SQLITE_RETENTION_QUOTES_DAYS  = "7"  }
if (-not $env:SQLITE_MAINT_MAX_DURATION_SEC) { $env:SQLITE_MAINT_MAX_DURATION_SEC = "60" }
if (-not $env:SQLITE_MAINT_VACUUM_STRATEGY)  { $env:SQLITE_MAINT_VACUUM_STRATEGY  = $Strategy }

$mode = if ($Execute) { "--execute" } else { "--dry-run" }

Write-Host "SQLite maintenance: $mode, strategy=$($env:SQLITE_MAINT_VACUUM_STRATEGY), db=$DbPath"

# Use python from venv if available
$python = "$PSScriptRoot\..\.\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

& $python -m scripts.sqlite_maint --db "$DbPath" $mode
if ($LASTEXITCODE -ne 0) {
    Write-Error "sqlite_maint ended with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
