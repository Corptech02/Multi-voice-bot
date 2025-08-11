#!/usr/bin/env pwsh

Write-Host "Testing COI Backend Connection from Surefire Configuration..." -ForegroundColor Yellow

# Test direct backend connection
Write-Host "`nTesting direct backend connection on port 8001..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/requests/monitoring/status" -Method Get
    Write-Host "✓ Direct backend connection successful!" -ForegroundColor Green
    Write-Host "  - Monitoring Active: $($response.active)" -ForegroundColor Gray
    Write-Host "  - Email Count: $($response.email_count)" -ForegroundColor Gray
    Write-Host "  - New Emails: $($response.scan_results.new_emails)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Direct backend connection failed: $_" -ForegroundColor Red
}

# Test Surefire configuration
Write-Host "`nChecking Surefire configuration..." -ForegroundColor Cyan
$configPath = "./surefire-crm/appsettings.json"
if (Test-Path $configPath) {
    $config = Get-Content $configPath | ConvertFrom-Json
    $coiUrl = $config.COITool.BaseUrl
    Write-Host "  - COI Backend URL in config: $coiUrl" -ForegroundColor Gray
    
    # Test the configured URL
    Write-Host "`nTesting configured URL: $coiUrl/api/v1/requests/monitoring/status" -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri "$coiUrl/api/v1/requests/monitoring/status" -Method Get
        Write-Host "✓ Configured URL connection successful!" -ForegroundColor Green
    } catch {
        Write-Host "✗ Configured URL connection failed: $_" -ForegroundColor Red
    }
}

# Test from Surefire perspective
Write-Host "`nTesting from Surefire's perspective (with Origin header)..." -ForegroundColor Cyan
try {
    $headers = @{
        "Origin" = "http://localhost:5189"
        "Accept" = "application/json"
    }
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/requests/monitoring/status" -Method Get -Headers $headers
    Write-Host "✓ CORS test successful!" -ForegroundColor Green
} catch {
    Write-Host "✗ CORS test failed: $_" -ForegroundColor Red
}

Write-Host "`nTest complete." -ForegroundColor Yellow