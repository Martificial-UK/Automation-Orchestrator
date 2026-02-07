#!/usr/bin/env pwsh
#
# Quick Setup Script - Automation Orchestrator Dashboard
# This script installs frontend dependencies and provides setup instructions
#

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Automation Orchestrator - Dashboard Setup           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if Node.js is installed
Write-Host "[1/4] Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "  ✓ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Node.js not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Node.js from: https://nodejs.org/" -ForegroundColor Red
    Write-Host "Recommended: Node.js 18 LTS or higher" -ForegroundColor Yellow
    exit 1
}

# Navigate to frontend directory
$frontendPath = Join-Path $PSScriptRoot "frontend"
if (-not (Test-Path $frontendPath)) {
    Write-Host "  ✗ Frontend directory not found at: $frontendPath" -ForegroundColor Red
    exit 1
}

Set-Location $frontendPath
Write-Host "  ✓ Changed to frontend directory" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "[2/4] Installing frontend dependencies..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes..." -ForegroundColor Gray
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ npm install failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Dependencies installed successfully" -ForegroundColor Green
Write-Host ""

# Build frontend for production
Write-Host "[3/4] Building frontend for production..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Frontend built successfully" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "[4/4] Setup Complete!" -ForegroundColor Yellow
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              🎉 Setup Successful! 🎉                  ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "📦 What was installed:" -ForegroundColor Cyan
Write-Host "   • React 18 + TypeScript" -ForegroundColor White
Write-Host "   • Tailwind CSS (styling)" -ForegroundColor White
Write-Host "   • React Router (navigation)" -ForegroundColor White
Write-Host "   • Recharts (analytics)" -ForegroundColor White
Write-Host "   • Axios (API client)" -ForegroundColor White
Write-Host ""

Write-Host "🚀 Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Start the Backend API Server:" -ForegroundColor Yellow
Set-Location ..
$backendCmd = "cd `"$(Get-Location)`" ; python -m uvicorn src.automation_orchestrator.wsgi:app --host 0.0.0.0 --port 8000 --workers 4"
Write-Host "   $backendCmd" -ForegroundColor White
Write-Host ""

Write-Host "2. Open your browser:" -ForegroundColor Yellow
Write-Host "   http://localhost:8000" -ForegroundColor White
Write-Host ""

Write-Host "3. Login with default credentials:" -ForegroundColor Yellow
Write-Host "   Username: admin" -ForegroundColor White
Write-Host "   Password: admin123" -ForegroundColor White
Write-Host ""

Write-Host "📚 For Development Mode:" -ForegroundColor Cyan
Write-Host "   If you want to edit the frontend with hot-reload:" -ForegroundColor Gray
Write-Host ""
Write-Host "   Terminal 1 (Backend):" -ForegroundColor Yellow
Write-Host "   $backendCmd" -ForegroundColor White
Write-Host ""
Write-Host "   Terminal 2 (Frontend):" -ForegroundColor Yellow
Write-Host "   cd frontend ; npm run dev" -ForegroundColor White
Write-Host "   (Then visit http://localhost:3000)" -ForegroundColor Gray
Write-Host ""

Write-Host "💡 Documentation:" -ForegroundColor Cyan
Write-Host "   • Frontend Guide: .\frontend\README.md" -ForegroundColor White
Write-Host "   • Integration Guide: .\FRONTEND_INTEGRATION.md" -ForegroundColor White
Write-Host ""

Write-Host "Press any key to start the backend server now, or Ctrl+C to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host ""
Write-Host "Starting backend server..." -ForegroundColor Green
Invoke-Expression $backendCmd
