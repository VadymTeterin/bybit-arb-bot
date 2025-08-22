<#
  scripts/unschedule_gh_digest.ps1
  Purpose: Remove the Windows Task Scheduler job for GH Digest.
#>
param([string]$TaskName = "BybitBot-GH-Digest")

try {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Scheduled task '$TaskName' removed."
  } else {
    Write-Host "Scheduled task '$TaskName' not found."
  }
} catch {
  Write-Error $_
  exit 1
}
