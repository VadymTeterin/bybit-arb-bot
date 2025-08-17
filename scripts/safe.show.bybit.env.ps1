<#
  Безпечний вивід змінних BYBIT_* з маскуванням ключів.
  Використання:
    .\scripts\safe.show.bybit.env.ps1
    # Показати повністю (НЕ радиться на скрині/стрімі):
    # .\scripts\safe.show.bybit.env.ps1 -All
#>
param(
  [switch]$All
)

function Get-EnvSafe([string]$name) {
  $v = [System.Environment]::GetEnvironmentVariable($name, "Process")
  if ([string]::IsNullOrEmpty($v)) {
    # спробуємо зчитати з User/Machine на всякий випадок
    $v = [System.Environment]::GetEnvironmentVariable($name, "User")
    if ([string]::IsNullOrEmpty($v)) {
      $v = [System.Environment]::GetEnvironmentVariable($name, "Machine")
    }
  }
  return $v
}

function Mask([string]$s) {
  if ([string]::IsNullOrEmpty($s)) { return "" }
  if ($s.Length -le 8) { return "****" }
  return $s.Substring(0,4) + "…" + $s.Substring($s.Length-4,4)
}

$vars = @(
  "BYBIT_PUBLIC_URL",
  "BYBIT_PRIVATE_URL",
  "BYBIT_DEFAULT_CATEGORY",
  "BYBIT_API_KEY",
  "BYBIT_API_SECRET"
)

foreach ($k in $vars) {
  $v = Get-EnvSafe $k
  if ($k -match "KEY|SECRET" -and -not $All) {
    "{0} = {1}" -f $k, (Mask $v)
  } else {
    "{0} = {1}" -f $k, $v
  }
}

# Додаткові підказки
if ((Get-EnvSafe "BYBIT_PUBLIC_URL") -notmatch "bybit\.com") {
  Write-Warning "BYBIT_PUBLIC_URL виглядає нетипово."
}
if ((Get-EnvSafe "BYBIT_PRIVATE_URL") -notmatch "bybit\.com") {
  Write-Warning "BYBIT_PRIVATE_URL виглядає нетипово."
}
