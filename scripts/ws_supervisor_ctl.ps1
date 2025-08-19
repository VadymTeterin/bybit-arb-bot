<#
WS Supervisor Control Script (PowerShell 5.1 compatible)
Usage:
  .\scripts\ws_supervisor_ctl.ps1 start [-NoConsole]  # за замовч. console-режим (python.exe) з редиректом логів
  .\scripts\ws_supervisor_ctl.ps1 stop
  .\scripts\ws_supervisor_ctl.ps1 status
  .\scripts\ws_supervisor_ctl.ps1 restart [-NoConsole]
  .\scripts\ws_supervisor_ctl.ps1 tail [-TailLines N]
#>

param(
  [Parameter(Position=0)]
  [ValidateSet("start","stop","status","restart","tail")]
  [string]$Action = "status",
  [int]$TailLines = 100,
  [switch]$NoConsole
)

$ErrorActionPreference = "Stop"

# Репо-рут і шляхи
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$RunDir   = Join-Path $RepoRoot "run"
$LogsDir  = Join-Path $RepoRoot "logs"
$PidFile  = Join-Path $RunDir  "supervisor.pid"

$Pythonw  = Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"
$Python   = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Module   = "scripts.ws_bot_supervisor"

function Get-SupervisorProcess {
  # 1) За PID-файлом
  if (Test-Path $PidFile) {
    try {
      $pid = Get-Content $PidFile -ErrorAction SilentlyContinue
      if ($pid) {
        $p = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($p) { return $p }
      }
    } catch {}
  }
  # 2) Пошук за командним рядком (fallback)
  try {
    $list = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
      Where-Object { $_.CommandLine -match [Regex]::Escape($Module) -and $_.CommandLine -match [Regex]::Escape($RepoRoot) }
    if ($list) {
      $procId = ($list | Sort-Object -Property CreationDate -Descending | Select-Object -First 1).ProcessId
      return (Get-Process -Id $procId -ErrorAction SilentlyContinue)
    }
  } catch {}
  return $null
}

switch ($Action) {
  "start" {
    New-Item -ItemType Directory -Path $RunDir  -Force | Out-Null
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

    $existing = Get-SupervisorProcess
    if ($existing) { Write-Host "Already running (PID=$($existing.Id)). Logs: $LogsDir"; break }

    # За замовчуванням console-режим; -NoConsole перемикає на windowless
    $useConsole = $true
    if ($NoConsole.IsPresent) { $useConsole = $false }

    if ($useConsole) {
      if (-not (Test-Path $Python)) { throw "Not found: $Python" }
      $stdout = Join-Path $LogsDir "supervisor.stdout.log"
      $stderr = Join-Path $LogsDir "supervisor.stderr.log"
      $proc = Start-Process $Python `
        -ArgumentList "-m $Module" `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru
    } else {
      $exe = $Pythonw
      if (-not (Test-Path $exe)) { $exe = $Python }
      if (-not (Test-Path $exe)) { throw "Not found: $exe" }
      $proc = Start-Process $exe `
        -ArgumentList "-m $Module" `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -PassThru
    }

    $proc.Id | Out-File $PidFile -Encoding ascii -Force
    Start-Sleep -Milliseconds 800
    $alive = $null -ne (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)
    if ($alive) {
      Write-Host "Started (PID=$($proc.Id)). Logs: $LogsDir"
    } else {
      Write-Host "Process exited immediately (PID=$($proc.Id))."
      if ($useConsole) {
        $stderrFile = Join-Path $LogsDir 'supervisor.stderr.log'
        Write-Host "Check errors: $stderrFile"
        try { Get-Content $stderrFile -Tail 80 } catch {}
      } else {
        Write-Host "Retry in console mode:"
        Write-Host ".\scripts\ws_supervisor_ctl.ps1 start"
      }
    }
  }

  "stop" {
    $p = Get-SupervisorProcess
    if (-not $p) { Write-Host "Not running."; break }
    Stop-Process -Id $p.Id -Force
    if (Test-Path $PidFile) { Remove-Item $PidFile -Force }
    Write-Host "Stopped (PID=$($p.Id))."
  }

  "status" {
    $p = Get-SupervisorProcess
    if ($p) {
      Write-Host "Running (PID=$($p.Id))."
    } else {
      Write-Host "Not running."
    }
    if (Test-Path $LogsDir) {
      $last = Get-ChildItem $LogsDir -Filter "*.log" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
      if ($last) {
        Write-Host "Last log: $($last.FullName)"
        try { Get-Content $last.FullName -Tail 40 } catch {}
      } else {
        Write-Host "No log files yet."
      }
    } else {
      Write-Host "Logs dir missing: $LogsDir"
    }
  }

  "restart" {
    & $PSCommandPath stop
    Start-Sleep -Milliseconds 500
    if ($NoConsole.IsPresent) {
      & $PSCommandPath start -NoConsole
    } else {
      & $PSCommandPath start
    }
  }

  "tail" {
    if (-not (Test-Path $LogsDir)) { Write-Host "Logs dir missing: $LogsDir"; break }
    $last = Get-ChildItem $LogsDir -Filter "*.log" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $last) { Write-Host "No log files to tail."; break }
    Write-Host "Tailing $($last.FullName)  Ctrl+C to stop"
    Get-Content $last.FullName -Tail $TailLines -Wait
  }
}
