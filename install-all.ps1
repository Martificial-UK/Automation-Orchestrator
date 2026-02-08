#!/usr/bin/env pwsh
# Unified Installer for Automation Orchestrator (Backend + Frontend)

$ErrorActionPreference = "Stop"

Write-Host "" -ForegroundColor Cyan
Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Automation Orchestrator - Unified Install           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow
Write-Host "Checking for Python..." -ForegroundColor Yellow
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCheck) {
    Write-Host "  ✗ Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
$pythonVersion = python --version
Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green

# 2. Install backend dependencies
Write-Host "[2/5] Installing backend dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "requirements.txt")) {
    Write-Host "  ✗ requirements.txt not found!" -ForegroundColor Red
    exit 1
}
python -m pip install --upgrade pip
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Backend dependency install failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Backend dependencies installed" -ForegroundColor Green

# 3. Check Node.js
Write-Host "[3/5] Checking Node.js installation..." -ForegroundColor Yellow
Write-Host "Checking for Node.js..." -ForegroundColor Yellow
$nodeCheck = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $nodeCheck) {
    Write-Host "  ✗ Node.js not found!" -ForegroundColor Red
    Write-Host "Please install Node.js from: https://nodejs.org/" -ForegroundColor Red
    exit 1
}
$nodeVersion = node --version
Write-Host "  ✓ Node.js found: $nodeVersion" -ForegroundColor Green

# 4. Install frontend dependencies and build
$frontendPath = Join-Path $PSScriptRoot "frontend"
if (-not (Test-Path $frontendPath)) {
    Write-Host "  ✗ Frontend directory not found at: $frontendPath" -ForegroundColor Red
    exit 1
}
Set-Location $frontendPath
Write-Host "[4/5] Installing frontend dependencies..." -ForegroundColor Yellow
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ npm install failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Frontend dependencies installed" -ForegroundColor Green
Write-Host "[4/5] Building frontend..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Frontend build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Frontend built successfully" -ForegroundColor Green
Set-Location $PSScriptRoot

# 5. Start backend server
Write-Host "[5/5] Starting backend server..." -ForegroundColor Yellow
Write-Host "  (You can open http://localhost:8000 in your browser)" -ForegroundColor Cyan
python -m uvicorn src.automation_orchestrator.wsgi:app --host 0.0.0.0 --port 8000 --workers 4

Write-Host "" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "=              Setup Successful! 🎉                   =" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host ""