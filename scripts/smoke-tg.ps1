param(
  [string]$EnvFile = ".env",
  [string]$Text = "bybit-arb-bot: smoke test ✅"
)

$ErrorActionPreference = "Stop"

function Get-DotenvValue([string]$path, [string]$key) {
  (Get-Content -Raw $path) -split "`r?`n" |
    Where-Object { $_ -match "^\s*$key\s*=\s*(.+)$" } |
    ForEach-Object { $matches[1].Trim(' ''"') } |
    Select-Object -First 1
}

# 1) дістаємо токен/чат із .env
$token  = Get-DotenvValue $EnvFile 'TELEGRAM__BOT_TOKEN'
$chatId = Get-DotenvValue $EnvFile 'TELEGRAM__ALERT_CHAT_ID'

if (-not $token)  { throw "TELEGRAM__BOT_TOKEN not found in $EnvFile" }
if (-not $chatId) { throw "TELEGRAM__ALERT_CHAT_ID not found in $EnvFile" }

# 2) швидка перевірка токена (getMe)
$me = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getMe"
if (-not $me.ok) { throw "Telegram getMe failed: $($me | ConvertTo-Json -Depth 5)" }
"Token OK for bot: $($me.result.username)"

# 3) експортуємо змінні в поточну PS-сесію (щоб їх бачив Python-процес)
$env:TELEGRAM__BOT_TOKEN     = $token
$env:TELEGRAM__ALERT_CHAT_ID = $chatId
$env:ENABLE_ALERTS           = '1'

# 4) показуємо, що додаток їх бачить
python -m src.main env

# 5) надсилаємо тест зі застосунку
python -m src.main tg:send --text $Text
