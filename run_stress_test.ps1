# Stress Test Runner Script for Automation Orchestrator
# Run: .\run_stress_test.ps1

param(
    [string]$Host = "http://localhost:8000",
    [int]$Users = 50,
    [int]$SpawnRate = 10,
    [string]$RunTime = "10m",
    [switch]$WebUI = $false,
    [switch]$Headless = $false
)

$ErrorActionPreference = "Stop"

function Write-Banner {
    param([string]$Text)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Check-Prerequisites {
    Write-Banner "🔍 Checking Prerequisites"
    
    # Check if locust is installed
    $locustCheck = locust --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Locust not installed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Install with: pip install locust" -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "✓ Locust installed: $locustCheck" -ForegroundColor Green
    }
    
    # Check if API is running
    Write-Host "Checking API connectivity..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "$Host/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "✓ API is running and responding" -ForegroundColor Green
    } catch {
        Write-Host "❌ Cannot reach API at $Host" -ForegroundColor Red
        Write-Host ""
        Write-Host "Make sure the API is running with: docker-compose up -d" -ForegroundColor Yellow
        exit 1
    }
}

function Get-SystemMetrics {
    Write-Host ""
    Write-Host "📊 System Information Before Test:" -ForegroundColor Cyan
    Write-Host "  Host: $Host"
    Write-Host "  Simulated Users: $Users"
    Write-Host "  Spawn Rate: $SpawnRate users/sec"
    Write-Host "  Duration: $RunTime"
    Write-Host ""
}

function Run-StressTest {
    Write-Banner "🚀 Starting Stress Test"
    
    $cmd = "locust -f locustfile.py --host=$Host --users=$Users --spawn-rate=$SpawnRate --run-time=$RunTime"
    
    if ($Headless) {
        $cmd += " --headless"
        Write-Host "Running in HEADLESS mode..." -ForegroundColor Yellow
    } elseif ($WebUI) {
        Write-Host "Launching Web UI at http://localhost:8089" -ForegroundColor Yellow
        Write-Host "You can monitor the test in real-time in your browser" -ForegroundColor Yellow
        Write-Host ""
    } else {
        $cmd += " --headless"
        Write-Host "Running in HEADLESS mode (default)" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Command: $cmd" -ForegroundColor Cyan
    Write-Host ""
    
    Invoke-Expression $cmd
}

function Show-APIMetrics {
    Write-Banner "📈 API Metrics During Test"
    
    Write-Host "Checking Prometheus metrics endpoint..." -ForegroundColor Yellow
    
    try {
        $metrics = Invoke-WebRequest -Uri "$Host/metrics" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "✓ Metrics available at $Host/metrics" -ForegroundColor Green
        Write-Host ""
        Write-Host "View metrics with: curl $Host/metrics | grep http_requests" -ForegroundColor Cyan
    } catch {
        Write-Host "⚠ Metrics endpoint not available" -ForegroundColor Yellow
    }
}

function Show-DashboardInfo {
    Write-Banner "📊 Monitoring Dashboard"
    
    Write-Host "🔗 Access these dashboards during/after test:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. Grafana (Metrics Visualization)"
    Write-Host "     URL: http://localhost:3000"
    Write-Host "     Login: admin / admin"
    Write-Host ""
    Write-Host "  2. API Health"
    Write-Host "     Basic: http://localhost:8000/health"
    Write-Host "     Detailed: http://localhost:8000/health/detailed"
    Write-Host ""
    Write-Host "  3. Prometheus (Raw Metrics)"
    Write-Host "     URL: http://localhost:9090"
    Write-Host ""
    Write-Host "  4. Docker System Metrics"
    Write-Host "     Use: docker stats"
    Write-Host ""
}

function Show-PostTestInstructions {
    Write-Banner "✅ Test Complete"
    
    Write-Host "Review results:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Check Grafana dashboard for visualizations"
    Write-Host "2. Review response times and error rates"
    Write-Host "3. Check if auto-scaling triggered (Kubernetes only)"
    Write-Host "4. Monitor database and Redis performance"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  - Review memory usage patterns"
    Write-Host "  - Check database connection pool utilization"
    Write-Host "  - Verify error logs in Grafana Loki"
    Write-Host "  - Document baseline metrics for comparison"
    Write-Host ""
}

# ==================== MAIN EXECUTION ====================

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║   Automation Orchestrator - Local Stress Test Runner    ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Magenta

Check-Prerequisites
Get-SystemMetrics
Show-APIMetrics
Show-DashboardInfo

# Confirm before starting
Write-Host ""
Write-Host "Ready to start stress test?" -ForegroundColor Yellow
Write-Host "Press Enter to continue or Ctrl+C to cancel..."
Read-Host

Run-StressTest
Show-PostTestInstructions
