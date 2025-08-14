# fix_utcnow.ps1
# Масово оновлює .py-файли:
#  - datetime.utcnow() -> datetime.now(timezone.utc)
#  - додає ", timezone" в рядки імпорту "from datetime import ...", якщо його ще нема

$ErrorActionPreference = "Stop"

# Які директорії переглядаємо
$roots = @("src", "tests", "scripts", "dev")

# Збираємо список файлів
$files = foreach ($root in $roots) {
  if (Test-Path $root) { Get-ChildItem $root -Recurse -Filter *.py }
}

$changed = @()
foreach ($f in $files) {
  $text = Get-Content $f.FullName -Raw

  $original = $text

  # 1) utcnow() -> now(timezone.utc)
  $text = $text -replace 'datetime\s*\.\s*utcnow\s*\(\s*\)', 'datetime.now(timezone.utc)'

  # 2) у рядку імпорту "from datetime import ...":
  #    якщо є "from datetime import" але немає "timezone" — додати ", timezone"
  #    працює і коли імпорт кількарядковий (зворотні слеші чи дужки не чіпаємо — лише прості випадки)
  $text = $text -replace '(?m)^(from\s+datetime\s+import\s+)(?!.*\btimezone\b)([^\r\n#]+)', '$1$2, timezone'

  if ($text -ne $original) {
    Set-Content -Path $f.FullName -Value $text -NoNewline
    $changed += $f.FullName
    Write-Host "[updated] $($f.FullName)"
  }
}

if ($changed.Count -eq 0) {
  Write-Host "No files needed changes."
} else {
  Write-Host "`nUpdated files:"
  $changed | ForEach-Object { Write-Host " - $_" }
}
