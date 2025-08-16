Param(
  [switch]$EnableAlerts = $false,
  [string]$LogLevel = "INFO"
)

$ErrorActionPreference = "Stop"

# === Налаштування (за потреби зміни шлях) ===
$RepoRoot = "C:\Projects\bybit-arb-bot"
$Python   = Join-Path $RepoRoot ".venv\Scripts\python.exe"

# === Перехід у корінь репозиторію ===
Set-Location $RepoRoot

# === Базові змінні (якщо не задані у .env або середовищі) ===
if (-not $env:BYBIT__WS_PUBLIC_URL_LINEAR) { $env:BYBIT__WS_PUBLIC_URL_LINEAR = "wss://stream.bybit.com/v5/public/linear" }
if (-not $env:BYBIT__WS_SUB_TOPICS_LINEAR) { $env:BYBIT__WS_SUB_TOPICS_LINEAR = "tickers.BTCUSDT,tickers.ETHUSDT" }

if (-not $env:BYBIT__WS_PUBLIC_URL_SPOT)   { $env:BYBIT__WS_PUBLIC_URL_SPOT   = "wss://stream.bybit.com/v5/public/spot" }
if (-not $env:BYBIT__WS_SUB_TOPICS_SPOT)   { $env:BYBIT__WS_SUB_TOPICS_SPOT   = "tickers.BTCUSDT,tickers.ETHUSDT" }

$env:ENABLE_ALERTS = if ($EnableAlerts) { "true" } else { "false" }
$env:LOG_LEVEL     = $LogLevel

# === Логи ===
$logs = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$StdOut = Join-Path $logs "ws.out.log"
$StdErr = Join-Path $logs "ws.err.log"

# === Запуск ===
& $Python -m src.main ws:run 1>> $StdOut 2>> $StdErr
