[CmdletBinding()]
param(
  # Можна передати інший шлях до .env за потреби
  [string]$EnvFile
)

$ErrorActionPreference = 'Stop'

# ---- helpers ----
function Mask {
  param([string]$v, [int]$Head=4, [int]$Tail=2)
  if ([string]::IsNullOrEmpty($v)) { return '<empty>' }
  if ($v.Length -le ($Head + $Tail)) { return ('*' * $v.Length) }
  return $v.Substring(0,$Head) + ('*' * ($v.Length - ($Head + $Tail))) + $v.Substring($v.Length-$Tail)
}
function ToDisplay {
  param([string]$s)
  if ([string]::IsNullOrEmpty($s)) { return '<empty>' } else { return $s }
}
function Show {
  param([string]$label, [string]$value)
  if ([string]::IsNullOrEmpty($value)) {
    Write-Host ("{0,-26}: <empty>" -f $label)
  } else {
    Write-Host ("{0,-26}: {1}" -f $label, $value)
  }
}

# ---- resolve default EnvFile from script location ----
if (-not $EnvFile -or $EnvFile.Trim() -eq '') {
  # $PSCommandPath працює в PS 5.1 при запуску файлу (не в REPL)
  $scriptDir = Split-Path -Path $PSCommandPath -Parent
  $repoRoot  = Split-Path -Path $scriptDir -Parent
  $EnvFile   = Join-Path $repoRoot '.env'
}

# ---- read .env ----
if (-not (Test-Path -LiteralPath $EnvFile)) {
  throw ".env not found at: $EnvFile"
}
$envText = Get-Content -Raw -Encoding UTF8 -LiteralPath $EnvFile

# ---- parse .env -> hashtable ----
$kv = @{}
foreach ($line in ($envText -split "`n")) {
  $l = $line.Trim()
  if (-not $l) { continue }
  if ($l.StartsWith('#')) { continue }
  if ($l -notmatch '^\s*([A-Za-z_][A-Za-z0-9_+]*)\s*=\s*(.*)\s*$') { continue }
  $k = $matches[1]
  $v = $matches[2]
  if ($v.Length -ge 2) {
    if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
      $v = $v.Substring(1, $v.Length - 2)
    }
  }
  $kv[$k] = $v
}

# ---- keys to lift into Process scope ----
$keys = @(
  'BYBIT_PUBLIC_URL','BYBIT_PRIVATE_URL','BYBIT_DEFAULT_CATEGORY',
  'BYBIT_API_KEY','BYBIT_API_SECRET',
  'BYBIT_USE_SERVER_TIME','BYBIT_RECV_WINDOW_MS',
  'TELEGRAM__BOT_TOKEN','TELEGRAM__ALERT_CHAT_ID'
)

# clear process-scope remnants first
foreach ($k in $keys) { Remove-Item -Path "Env:$k" -ErrorAction SilentlyContinue }

# set values from .env (if present)
foreach ($k in $keys) {
  if ($kv.ContainsKey($k)) {
    [Environment]::SetEnvironmentVariable($k, $kv[$k], 'Process')
  }
}

# testnet defaults if requested
if ($kv.ContainsKey('BYBIT_IS_TESTNET') -and $kv['BYBIT_IS_TESTNET'] -eq '1') {
  if (-not $env:BYBIT_PUBLIC_URL)  { [Environment]::SetEnvironmentVariable('BYBIT_PUBLIC_URL','https://api-testnet.bybit.com','Process') }
  if (-not $env:BYBIT_PRIVATE_URL) { [Environment]::SetEnvironmentVariable('BYBIT_PRIVATE_URL','https://api-testnet.bybit.com','Process') }
}

# ---- diag ----
Write-Host "Loaded .env from: $EnvFile"
Show "BYBIT_PUBLIC_URL"          $env:BYBIT_PUBLIC_URL
Show "BYBIT_PRIVATE_URL"         $env:BYBIT_PRIVATE_URL
Write-Host ("{0,-26}: {1}" -f "BYBIT_DEFAULT_CATEGORY", (ToDisplay $env:BYBIT_DEFAULT_CATEGORY))
Write-Host ("{0,-26}: {1}" -f "BYBIT_API_KEY",          (Mask $env:BYBIT_API_KEY))
Write-Host ("{0,-26}: {1}" -f "BYBIT_API_SECRET",       (Mask $env:BYBIT_API_SECRET))
Write-Host ("{0,-26}: {1}" -f "BYBIT_USE_SERVER_TIME",  (ToDisplay $env:BYBIT_USE_SERVER_TIME))
Write-Host ("{0,-26}: {1}" -f "BYBIT_RECV_WINDOW_MS",   (ToDisplay $env:BYBIT_RECV_WINDOW_MS))
Write-Host ("{0,-26}: {1}" -f "TELEGRAM__BOT_TOKEN",    (Mask $env:TELEGRAM__BOT_TOKEN))
Write-Host ("{0,-26}: {1}" -f "TELEGRAM__ALERT_CHAT_ID",(ToDisplay $env:TELEGRAM__ALERT_CHAT_ID))
