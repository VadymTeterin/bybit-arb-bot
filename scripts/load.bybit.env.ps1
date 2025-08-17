<#
  Завантажує змінні BYBIT_* з .env-файлу (дефолт: config\bybit.secrets.env)
  Сумісно з Windows PowerShell 5.1 (без тернарного оператора).
  Використання:
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    .\scripts\load.bybit.env.ps1
    # або:
    .\scripts\load.bybit.env.ps1 -Path "C:\path\to\file.env"
#>
param(
  [string]$Path = "config\bybit.secrets.env"
)

if (-not (Test-Path -LiteralPath $Path)) {
  Write-Error "Файл '$Path' не знайдено. Створи його за шаблоном у config\bybit.secrets.env"
  exit 1
}

$lines = Get-Content -LiteralPath $Path -Encoding UTF8

foreach ($line in $lines) {
  $t = $line.Trim()
  if ([string]::IsNullOrWhiteSpace($t)) { continue }
  if ($t.StartsWith("#")) { continue }
  if ($t -notmatch "=") { continue }

  $kv = $t.Split("=", 2)
  $key = $kv[0].Trim()
  $val = $kv[1].Trim()

  if ($val.StartsWith('"') -and $val.EndsWith('"')) { $val = $val.Substring(1, $val.Length - 2) }
  if ($val.StartsWith("'") -and $val.EndsWith("'")) { $val = $val.Substring(1, $val.Length - 2) }

  [System.Environment]::SetEnvironmentVariable($key, $val, "Process")

  if ($key -match "SECRET|KEY") {
    Write-Host ("Set {0}=****" -f $key)
  } else {
    Write-Host ("Set {0}={1}" -f $key, $val)
  }
}

Write-Host ""
Write-Host "Перевірка:  gci env:BYBIT_* | ft Name,Value -AutoSize"
Write-Host "Smoke (баланс, без торгів):  python -m scripts.e2e_bybit_testnet"
