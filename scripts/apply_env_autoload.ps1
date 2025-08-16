# scripts\apply_env_autoload.ps1
Param(
  [string]$ConfigPath = "src/infra/config.py"
)

Write-Host "==> Applying .env autoload hook into $ConfigPath"

if (!(Test-Path -LiteralPath $ConfigPath)) {
  Write-Error "Config file not found: $ConfigPath"
  exit 1
}

# Backup
Copy-Item -LiteralPath $ConfigPath -Destination "$ConfigPath.bak" -Force

# Read file
$content = Get-Content -LiteralPath $ConfigPath -Raw

# 1) Ensure import present (insert after first block of imports or at top)
if ($content -notmatch "(?m)from\s+\.\s*dotenv_autoload\s+import\s+autoload_env") {
  # Try to find the last import line to insert after
  $importBlock = [regex]::Matches($content, "(?m)^(from\s+[^\r\n]+|import\s+[^\r\n]+)\r?$")
  if ($importBlock.Count -gt 0) {
    $lastImport = $importBlock[$importBlock.Count - 1]
    $idx = $lastImport.Index + $lastImport.Length
    $content = $content.Insert($idx, "`r`nfrom .dotenv_autoload import autoload_env`r`n")
  } else {
    $content = "from .dotenv_autoload import autoload_env`r`n" + $content
  }
}

# 2) Inject autoload_env() at the start of load_settings() body
$pattern = "(?ms)def\s+load_settings\s*\([^\)]*\)\s*:\s*\r?\n"
$m = [regex]::Match($content, $pattern)
if ($m.Success) {
  $insertAt = $m.Index + $m.Length
  if ($content.Substring($insertAt, [Math]::Min(200, $content.Length - $insertAt)) -notmatch "(?m)^\s*autoload_env\s*\(") {
    $content = $content.Insert($insertAt, "    autoload_env()`r`n")
  }
} else {
  Write-Warning "Could not find 'def load_settings(...)' to inject hook. Please add manually inside that function:  autoload_env()"
}

# Write back
Set-Content -LiteralPath $ConfigPath -Value $content -Encoding UTF8

Write-Host "==> Done. Backup at $ConfigPath.bak"
