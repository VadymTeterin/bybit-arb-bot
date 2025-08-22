<#
  scripts/gh_digest_run.ps1
  Purpose: Run GitHub Daily Digest for "yesterday in Kyiv" and optionally send to Telegram.
  Notes:
    - Requires .venv (Python 3.11+) and valid .env with GH_TOKEN, TG_BOT_TOKEN, TG_CHAT_ID.
    - This script is safe for Windows Task Scheduler usage.
#>

param(
  [switch]$Send = $true,          # default: send to Telegram
  [switch]$NoMock = $true,        # default: use real GitHub API
  [string]$Owner = $env:GITHUB_OWNER,
  [string]$Repo  = $env:GITHUB_REPO
)

# --- Resolve repo root (script directory) ---
$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot  = Resolve-Path (Join-Path $ScriptDir "..")

# --- Ensure working directory is repo root ---
Set-Location $RepoRoot

# --- Compute "yesterday in Kyiv" safely ---
$kyivTz = [System.TimeZoneInfo]::FindSystemTimeZoneById("FLE Standard Time")  # Windows id for Europe/Kyiv
$nowKyiv = [System.TimeZoneInfo]::ConvertTime([DateTime]::UtcNow, $kyivTz)
$yesterdayKyiv = $nowKyiv.Date.AddDays(-1)
$DateArg = $yesterdayKyiv.ToString("yyyy-MM-dd")

# --- Prepare Python executable ---
$venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $pythonExe = $venvPy
} else {
    $pythonExe = "python"
}

# --- Ensure logs dir exists ---
$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

# --- Build command ar
