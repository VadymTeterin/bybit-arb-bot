[CmdletBinding()]
param()

function Get-EnvSafe { param([string]$Name)
  $v = [Environment]::GetEnvironmentVariable($Name)
  if ($null -eq $v) { '' } else { $v }
}
function Mask { param([string]$v, [int]$Head=4, [int]$Tail=2)
  if ([string]::IsNullOrEmpty($v)) { return '<empty>' }
  if ($v.Length -le ($Head + $Tail)) { return ('*' * $v.Length) }
  return $v.Substring(0,$Head) + ('*' * ($v.Length - ($Head + $Tail))) + $v.Substring($v.Length-$Tail)
}
function ToDisplay { param([string]$s)
  if ([string]::IsNullOrEmpty($s)) { '<empty>' } else { $s }
}

# ---- Bybit core ----
$IS_TESTNET = Get-EnvSafe 'BYBIT_IS_TESTNET'
$PUB_URL    = Get-EnvSafe 'BYBIT_PUBLIC_URL'
$PRV_URL    = Get-EnvSafe 'BYBIT_PRIVATE_URL'
$API_KEY    = Get-EnvSafe 'BYBIT_API_KEY'
$API_SECRET = Get-EnvSafe 'BYBIT_API_SECRET'

Write-Host "BYBIT_IS_TESTNET : $IS_TESTNET"
if ($PUB_URL) { Write-Host "BYBIT_PUBLIC_URL : $PUB_URL" }
if ($PRV_URL) { Write-Host "BYBIT_PRIVATE_URL: $PRV_URL" }

if ($PUB_URL -and $PUB_URL -notmatch 'bybit\.com') { Write-Warning 'BYBIT_PUBLIC_URL looks non-standard.' }
if ($PRV_URL -and $PRV_URL -notmatch 'bybit\.com') { Write-Warning 'BYBIT_PRIVATE_URL looks non-standard.' }

Write-Host ("BYBIT_API_KEY    : {0}" -f (Mask $API_KEY))
Write-Host ("BYBIT_API_SECRET : {0}" -f (Mask $API_SECRET))

# ---- Telegram (supports TELEGRAM__* and TG_* ) ----
$TG_TOKEN = Get-EnvSafe 'TELEGRAM__BOT_TOKEN'
if (-not $TG_TOKEN) { $TG_TOKEN = Get-EnvSafe 'TG_BOT_TOKEN' }

$TG_CHAT  = Get-EnvSafe 'TELEGRAM__ALERT_CHAT_ID'
if (-not $TG_CHAT) { $TG_CHAT = Get-EnvSafe 'TG_CHAT_ID' }

Write-Host ("TELEGRAM__BOT_TOKEN     : {0}" -f (Mask $TG_TOKEN))
Write-Host ("TELEGRAM__ALERT_CHAT_ID : {0}" -f (ToDisplay $TG_CHAT))

# ---- SQLite paths (optional) ----
$ALERTS_DB  = Get-EnvSafe 'ALERTS__DB_PATH'
$RUNTIME_DB = Get-EnvSafe 'RUNTIME__DB_PATH'
if ($ALERTS_DB)  { Write-Host "ALERTS__DB_PATH  : $ALERTS_DB" }
if ($RUNTIME_DB) { Write-Host "RUNTIME__DB_PATH : $RUNTIME_DB" }
