# LabOps Agent — Quick Endpoint Test Script
# Run from project root: .\test_endpoints.ps1

$BASE = "http://localhost:8000"

function Test-Endpoint($name, $url) {
    Write-Host "`n▶ Testing $name..." -ForegroundColor Cyan
    try {
        $resp = Invoke-RestMethod -Uri $url -Method GET -TimeoutSec 10
        Write-Host "  ✅ PASS" -ForegroundColor Green
        $resp | ConvertTo-Json -Depth 3 | Write-Host
    } catch {
        Write-Host "  ❌ FAIL: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n========== LabOps Agent Endpoint Tests ==========" -ForegroundColor Yellow

Test-Endpoint "Health Check"         "$BASE/health"
Test-Endpoint "Alert Trigger (TSH)"  "$BASE/alert/trigger?reagent_name=TSH"
Test-Endpoint "Prophet Forecast"     "$BASE/predict/TSH?current_stock=680"

Write-Host "`n========== Done ==========" -ForegroundColor Yellow
