# Clears Bybit-related environment variables for a clean session

$vars = @(
  "BYBIT_PUBLIC_URL",
  "BYBIT_PRIVATE_URL",
  "BYBIT_API_KEY",
  "BYBIT_API_SECRET",
  "BYBIT_DEFAULT_CATEGORY",
  "BYBIT_E2E",
  "BYBIT_PLACE_ORDER",
  "BYBIT_ORDER_SYMBOL",
  "BYBIT_ORDER_MARKET",
  "BYBIT_ORDER_SIDE",
  "BYBIT_ORDER_TYPE",
  "BYBIT_ORDER_QTY",
  "BYBIT_ORDER_PRICE"
)

foreach ($v in $vars) {
  Remove-Item "Env:$v" -ErrorAction SilentlyContinue
}

Write-Host "BYBIT env vars cleared."
