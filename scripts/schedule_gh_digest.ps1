<#
  scripts/schedule_gh_digest.ps1
  Purpose: Register a Windows Task Scheduler job to run gh_digest_run.ps1 daily at 07:10 Kyiv time.
  Usage (PowerShell, run as user who has rights to register tasks):
    .\scripts\schedule_gh_digest.ps1
#>

param(
  [string]$TaskName = "BybitBot-GH-Digest",
  [string]$Time     = "07:10"  # local machine time; ensure your Windows clock/timezone is set to Kyiv
)

$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot  = Resolve-Path (Join-Path $ScriptDir "..")
$Runner    = Join-Path $RepoRoot "scripts\gh_digest_run.ps1"

if (-not (Test-Path $Runner)) {
  Write-Error "Runner not found: $Runner"
  exit 1
}

# Build action: powershell -NoProfile -ExecutionPolicy Bypass -File "<repo>\scripts\gh_digest_run.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`""

# Daily trigger at $Time (machine local time)
$trigger = New-ScheduledTaskTrigger -Daily -At ([DateTime]::ParseExact($Time, "HH:mm", $null))

# Optionally: start even on AC/battery; set conditions as needed
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

# Register or update
try {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  }
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings | Out-Null
  Write-Host "Scheduled task '$TaskName' registered at $Time daily."
  Write-Host "To run now: Start-ScheduledTask -TaskName $TaskName"
} catch {
  Write-Error $_
  exit 1
}
