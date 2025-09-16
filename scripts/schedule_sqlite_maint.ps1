# scripts/schedule_sqlite_maint.ps1
# Purpose: Register (or re-register) a daily Windows Task to run sqlite.maint.daily.ps1
# Fixes:
#   - Remove invalid '/D' for DAILY schedule
#   - Remove invalid '/RI' for DAILY schedule
#   - Use full path to powershell.exe in /TR

param(
    [string]$TaskName = "BybitBot_SQLiteMaint_Daily",
    [string]$Time     = "03:15"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path $ScriptDir -Parent
$Runner    = Join-Path $RepoRoot "scripts\sqlite.maint.daily.ps1"
$PSExe     = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path $Runner)) {
    throw "Runner script not found: $Runner"
}

# Remove existing task if present
try {
    schtasks /Query /TN $TaskName | Out-Null
    schtasks /Delete /TN $TaskName /F | Out-Null
} catch { }

# Quote the command for /TR
$Args = "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`""
$TR   = "`"$PSExe`" $Args"

# Create the task (current user), DAILY at specified time
schtasks /Create /TN $TaskName /TR $TR /SC DAILY /ST $Time /RL LIMITED /F | Out-Null

Write-Output "Registered task '$TaskName' at $Time"
Write-Output "Action: $TR"
