<#
.SYNOPSIS
  Safe .env profile switcher: backups to .backups\env\, auto-rotation.

.USAGE
  .\use-profile.safe.ps1 soft
  .\use-profile.safe.ps1 medium "python -m src.main ws:run"
  .\use-profile.safe.ps1 restore
  .\use-profile.safe.ps1 soft "" -Keep 7

.PARAMETERS
  -Keep <int>  How many backups to keep in .backups\env\ (default: 5)
#>

param(
  [Parameter(Mandatory=$true, Position=0)]
  [ValidateSet('hard','medium','soft','restore')]
  [string]$Profile,
  [Parameter(Mandatory=$false, Position=1)]
  [string]$Run = '',
  [Parameter(Mandatory=$false)]
  [int]$Keep = 5
)

$ErrorActionPreference = 'Stop'

function Read-EnvFile([string]$Path) {
  if (-not (Test-Path $Path)) { throw ".env not found at $Path" }
  $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  return $raw -split "(`r`n|`n)"
}

function Write-EnvFile([string[]]$Lines, [string]$Path) {
  $nl = "`r`n"
  [IO.File]::WriteAllText($Path, ($Lines -join $nl), [Text.UTF8Encoding]::new($false))
}

function Ensure-Dir([string]$Dir) {
  if (-not (Test-Path $Dir)) { New-Item -ItemType Directory -Force -Path $Dir | Out-Null }
}

function Backup-Env([string]$EnvPath, [string]$Dir, [int]$Keep) {
  Ensure-Dir $Dir
  $stamp = Get-Date -Format "yyyyMMddHHmmss"
  $bk = Join-Path $Dir ("env.backup.{0}" -f $stamp)
  Copy-Item -LiteralPath $EnvPath -Destination $bk -Force
  # Rotation
  $all = Get-ChildItem -LiteralPath $Dir -File -Filter "env.backup.*" | Sort-Object LastWriteTime -Descending
  if ($all.Count -gt $Keep) {
    $all | Select-Object -Skip $Keep | Remove-Item -Force -ErrorAction SilentlyContinue
  }
  return $bk
}

function Overlay-Keys([string[]]$Lines, [hashtable]$Overlay){
  $found = @{}
  for ($i=0; $i -lt $Lines.Count; $i++) {
    $line = $Lines[$i]
    if ($line -match '^\s*([A-Za-z0-9_]+)\s*=(.*)$') {
      $k = $Matches[1]
      if ($Overlay.ContainsKey($k)) {
        $v = $Overlay[$k]
        $Lines[$i] = "$k=$v"
        $found[$k] = $true
      }
    }
  }
  foreach ($k in $Overlay.Keys) {
    if (-not $found.ContainsKey($k)) {
      $Lines += "$k=$($Overlay[$k])"
    }
  }
  return ,$Lines
}

$root = Get-Location
$envPath = Join-Path $root ".env"
$bkDir = Join-Path $root ".backups\env"

if ($Profile -eq 'restore') {
  if (-not (Test-Path $bkDir)) { throw "No backup directory: $bkDir" }
  $bk = Get-ChildItem -LiteralPath $bkDir -File -Filter "env.backup.*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $bk) { throw "No backups found in $bkDir" }
  Copy-Item -LiteralPath $bk.FullName -Destination $envPath -Force
  Write-Host "Restored from $($bk.Name) → .env" -ForegroundColor Green
  if ($Run) {
    Write-Host "Running: $Run" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -Command $Run
  }
  exit 0
}

# Define overlay per profile
$overlay = switch ($Profile) {
  'hard'   { @{ ALERT_THRESHOLD_PCT='1.0'; MIN_VOL_24H_USD='10000000'; ALERT_COOLDOWN_SEC='300'; RT_LOG_PASSES='0' } }
  'medium' { @{ ALERT_THRESHOLD_PCT='0.5'; MIN_VOL_24H_USD='2000000';  ALERT_COOLDOWN_SEC='180'; RT_LOG_PASSES='1' } }
  'soft'   { @{ ALERT_THRESHOLD_PCT='0.3'; MIN_VOL_24H_USD='1000000';  ALERT_COOLDOWN_SEC='60';  RT_LOG_PASSES='1' } }
}

$lines = Read-EnvFile $envPath
$bk = Backup-Env $envPath $bkDir $Keep
$updated = Overlay-Keys $lines $overlay
Write-EnvFile $updated $envPath

Write-Host "Profile '$Profile' applied. Backup: $($bkDir)\$(Split-Path $bk -Leaf). Keeping last $Keep backups." -ForegroundColor Green

if ($Run) {
  Write-Host "Running: $Run" -ForegroundColor Cyan
  & powershell -NoProfile -ExecutionPolicy Bypass -Command $Run
}
