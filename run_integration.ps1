# Automated audit integration and testing script

$ErrorActionPreference = "Continue"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Automation Orchestrator - Audit Integration & Testing" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

$orchestratorPath = "c:\AI Automation\Automation Orchestrator"

# Step 1: Run integration
Write-Host "[1/2] Integrating audit logging into modules..." -ForegroundColor Yellow
Set-Location $orchestratorPath

$integrationResult = python integrate_audit.py 2>&1
Write-Host $integrationResult

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Integration completed successfully!`n" -ForegroundColor Green
} else {
    Write-Host "`n✗ Integration failed!`n" -ForegroundColor Red
    exit 1
}

# Step 2: Run tests
Write-Host "`n[2/2] Running test suite..." -ForegroundColor Yellow
$testResult = python test_audit_integration.py 2>&1
Write-Host $testResult

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ All tests passed!`n" -ForegroundColor Green
} else {
    Write-Host "`n✗ Some tests failed!`n" -ForegroundColor Red
    exit 1
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✓ AUDIT INTEGRATION COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "`nAudit logging is now active in all modules." -ForegroundColor White
Write-Host "Audit logs will be written to: logs/audit.log" -ForegroundColor White
Write-Host "`nBackup files created with .bak extension" -ForegroundColor Gray
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Configure config/example_config.json with real credentials" -ForegroundColor White
Write-Host "2. Run: python -m automation_orchestrator.main" -ForegroundColor White
Write-Host "3. Monitor audit.log for complete operation trail`n" -ForegroundColor White
