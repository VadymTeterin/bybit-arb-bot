param(
  [Parameter(Mandatory = $true)][string]$ApiKey,
  [Parameter(Mandatory = $true)][string]$ApiSecret,
  [ValidateSet("spot","linear")][string]$Category = "spot",
  [switch]$Mainnet
)

# URLs
if ($Mainnet) {
  $env:BYBIT_PUBLIC_URL  = "https://api.bybit.com"
  $env:BYBIT_PRIVATE_URL = "https://api.bybit.com"
} else {
  $env:BYBIT_PUBLIC_URL  = "https://api-testnet.bybit.com"
  $env:BYBIT_PRIVATE_URL = "https://api-testnet.bybit.com"
}

# Keys & category
$env:BYBIT_API_KEY          = $ApiKey
$env:BYBIT_API_SECRET       = $ApiSecret
$env:BYBIT_DEFAULT_CATEGORY = $Category

# Safe echo (не світимо ключ)
$last4 = if ($ApiKey.Length -ge 4) { $ApiKey.Substring($ApiKey.Length - 4) } else { $ApiKey }

Write-Host "BYBIT env set:`n"
Write-Host ("  PUBLIC_URL        = {0}" -f $env:BYBIT_PUBLIC_URL)
Write-Host ("  PRIVATE_URL       = {0}" -f $env:BYBIT_PRIVATE_URL)
Write-Host ("  DEFAULT_CATEGORY  = {0}" -f $env:BYBIT_DEFAULT_CATEGORY)
Write-Host ("  API_KEY           = ****{0}" -f $last4)

Write-Host "`nRun smoke:"
Write-Host "  python -m scripts.e2e_bybit_testnet"

Write-Host "`n(Perps example):"
Write-Host "  .\scripts\env.bybit.testnet.ps1 -ApiKey <key> -ApiSecret <secret> -Category linear"

# Tip for current-session execution policy if needed
if ($env:PSExecutionPolicyPreference -eq $null) {
  Write-Host "`nNote: if scripts execution is blocked in this session, run:"
  Write-Host "  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force"
}
