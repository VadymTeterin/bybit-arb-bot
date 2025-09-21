
# scripts/run_irm_check.ps1
# Runs IRM pattern validation and IRM.view sync check locally (Windows PowerShell).
# Usage: .\scripts\run_irm_check.ps1

Write-Host "==> Validating IRM hook pattern on existing YAMLs..." -ForegroundColor Cyan
python tools\tests\validate_irm_patterns.py
if ($LASTEXITCODE -ne 0) {
  Write-Error "IRM pattern validation failed. See messages above."
  exit 1
}

Write-Host "==> Running IRM.view sync check (render_irm_view.py --check)..." -ForegroundColor Cyan
python tools\render_irm_view.py --check
if ($LASTEXITCODE -ne 0) {
  Write-Warning "IRM.view is out of sync. Use: python tools\render_irm_view.py --write"
  exit 2
}

Write-Host "All IRM checks passed." -ForegroundColor Green
exit 0
