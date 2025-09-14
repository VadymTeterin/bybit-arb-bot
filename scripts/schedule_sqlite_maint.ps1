# scripts/schedule_sqlite_maint.ps1
# Purpose: Register a daily Windows Scheduled Task to run SQLite maintenance.

[CmdletBinding()]
param(
    [string]$TaskName = "BybitBot_SQLiteMaint_Daily",
    [string]$RunTime  = "03:15",
    [ValidateSet('Interactive','Password','S4U','Group','ServiceAccount','InteractiveOrPassword','None')]
    [string]$LogonType = "Interactive",
    [switch]$AsSystem  # requires admin
)

$ErrorActionPreference = 'Stop'

function Test-IsAdmin {
    try {
        $winIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal   = New-Object Security.Principal.WindowsPrincipal($winIdentity)
        return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
    } catch { return $false }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner    = Resolve-Path (Join-Path $ScriptDir "sqlite.maint.daily.ps1")

$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
          -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`""
$Trigger = New-ScheduledTaskTrigger -Daily -At ([DateTime]::Parse($RunTime))

$IsAdmin = Test-IsAdmin

if ($AsSystem.IsPresent) {
    if (-not $IsAdmin) {
        Write-Error "Creating a SYSTEM task requires an elevated (Administrator) PowerShell."
        exit 1
    }
    $Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
} else {
    $user = "$env:USERDOMAIN\$env:USERNAME"
    # If not admin, fall back to Limited run level (no elevation)
    $runLevel = if ($IsAdmin) { "Highest" } else { "Limited" }
    $Principal = New-ScheduledTaskPrincipal -UserId $user -LogonType $LogonType -RunLevel $runLevel
}

try {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal | Out-Null

    $who = if ($AsSystem) { "LocalSystem" } else { "$env:USERDOMAIN\$env:USERNAME ($LogonType, RunLevel=$($Principal.RunLevel))" }
    Write-Host "Scheduled task '$TaskName' registered to run daily at $RunTime."
    Write-Host "Action: powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Runner`""
    Write-Host "Principal: $who"
    if (-not $IsAdmin -and -not $AsSystem) {
        Write-Host "Note: Task registered without elevation (Limited). If you need 'Highest', re-run in an elevated PowerShell."
    }
} catch {
    Write-Error "Failed to register scheduled task: $($_.Exception.Message)"
    exit 1
}
