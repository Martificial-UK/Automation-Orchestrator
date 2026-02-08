param(
    [string]$ConfigPath = "config\app_config.json"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Automation Orchestrator Installer" -ForegroundColor Cyan

if (!(Test-Path $ConfigPath)) {
    Copy-Item "config\sample_config.json" $ConfigPath
}

if (!(Test-Path ".venv")) {
    python -m venv .venv
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"

$wheelsDir = Join-Path $root "vendor\wheels"
$hasWheels = $false
if (Test-Path $wheelsDir) {
    $wheelFiles = Get-ChildItem -Path $wheelsDir -Filter "*.whl" -ErrorAction SilentlyContinue
    $hasWheels = ($wheelFiles.Count -gt 0)
}

if ($hasWheels) {
    Write-Host "Installing from offline wheels..." -ForegroundColor Green
    & $venvPython -m pip install --no-index --find-links vendor\wheels -r requirements.txt
} else {
    Write-Host "Installing from PyPI (requires internet)..." -ForegroundColor Yellow
    & $venvPython -m pip install -r requirements.txt
}

$env:AO_CONFIG = $ConfigPath
& $venvPython installer\launch_services.py $ConfigPath
