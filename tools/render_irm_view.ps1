param(
  [switch]$Open
)
$src = Resolve-Path (Join-Path $PSScriptRoot '..\docs\IRM.md') -ErrorAction Stop
$dst = Join-Path $PSScriptRoot '..\docs\IRM.view.md'

# Read, strip sentinels (block & inline), tidy whitespace
$content = Get-Content $src -Raw -Encoding UTF8
$content = [regex]::Replace($content, '<!--\s*IRM:(BEGIN|END)\s*[0-9.]+\s*-->', '')
$content = [regex]::Replace($content, '^[ \t]+$', '', 'Multiline')
$content = [regex]::Replace($content, '(\r?\n){3,}', "`r`n`r`n")

Set-Content -Path $dst -Value $content -Encoding UTF8
Write-Host " Wrote: $dst"
if ($Open) { code $dst }
