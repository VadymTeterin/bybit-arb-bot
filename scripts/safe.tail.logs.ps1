<#
  Безпечний "tail" логів із маскуванням ключів/підписів.
  Використання:
    .\scripts\safe.tail.logs.ps1 -Path app_console.log
#>
param(
  [string]$Path = "app_console.log"
)

if (-not (Test-Path -LiteralPath $Path)) {
  Write-Error "Файл '$Path' не знайдено."
  exit 1
}

function Mask-Line([string]$line) {
  $s = $line
  # JSON-подібні: "Header": "value"
  $s = [Regex]::Replace($s, '(?i)("?(x-bapi-[a-z0-9\-]+|authorization|api-?key|api[_-]?secret|signature)"?\s*[:=]\s*")([^"]+)(")', { param($m) $m.Groups[1].Value + "****" + $m.Groups[4].Value })
  # key=value
  $s = [Regex]::Replace($s, '(?i)\b(api_key|apiSecret|signature|api-secret|api-key)\s*=\s*([^\s&]+)', { param($m) $m.Groups[1].Value + "=****" })
  # Bearer токени
  $s = [Regex]::Replace($s, '(?i)\b(BEARER|Bearer)\s+([A-Za-z0-9\.\-_]+)', { param($m) $m.Groups[1].Value + " ****" })
  return $s
}

Write-Host "Tailing '$Path' (Ctrl+C щоб вийти)..." -ForegroundColor Cyan
Get-Content -LiteralPath $Path -Wait -Tail 10 | ForEach-Object {
  Write-Host (Mask-Line $_)
}
