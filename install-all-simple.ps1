# Simple Unified Installer for Automation Orchestrator (Backend + Frontend)
$ErrorActionPreference = "Stop"

Write-Host "=== Automation Orchestrator - Unified Install ===" -ForegroundColor Cyan

# 1. Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found! Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
$pythonVersion = python --version
Write-Host "Python found: $pythonVersion" -ForegroundColor Green

# 2. Install backend dependencies
if (-not (Test-Path "requirements.txt")) {
    Write-Host "requirements.txt not found!" -ForegroundColor Red
    exit 1
}
python -m pip install --upgrade pip
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend dependency install failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Backend dependencies installed" -ForegroundColor Green

# 3. Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js not found! Please install Node.js from https://nodejs.org/" -ForegroundColor Red
    exit 1
}
$nodeVersion = node --version
Write-Host "Node.js found: $nodeVersion" -ForegroundColor Green

# 4. Install frontend dependencies and build
$frontendPath = Join-Path $PSScriptRoot "frontend"
if (-not (Test-Path $frontendPath)) {
    Write-Host "Frontend directory not found at: $frontendPath" -ForegroundColor Red
    exit 1
}
Set-Location $frontendPath
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "npm install failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Frontend dependencies installed" -ForegroundColor Green
Write-Host "Building frontend..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Frontend built successfully" -ForegroundColor Green
Set-Location $PSScriptRoot

# 5. Start backend server
Write-Host "Starting backend server... (open http://localhost:8000)" -ForegroundColor Cyan
python src/automation_orchestrator/main.py --api --host 0.0.0.0 --port 8000

Write-Host "=== Setup Successful! ===" -ForegroundColor Green
