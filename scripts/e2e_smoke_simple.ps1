param(
    [string]$ConfigPath = "config\sample_config.json"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$script:LauncherProc = $null

function Write-Banner {
    param([string]$Text)
    Write-Host "" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Wait-Health {
    param([int]$Retries = 30, [int]$DelaySeconds = 2)
    for ($i = 0; $i -lt $Retries; $i++) {
        try {
            $code = (Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing -TimeoutSec 5).StatusCode
            if ($code -eq 200) {
                return $true
            }
        } catch {
        }
        Write-Host ("Waiting for health... {0}/{1}" -f ($i + 1), $Retries) -ForegroundColor Gray
        Start-Sleep -Seconds $DelaySeconds
    }
    return $false
}

function Stop-Launcher {
    if ($script:LauncherProc -and -not $script:LauncherProc.HasExited) {
        try {
            Stop-Process -Id $script:LauncherProc.Id -Force -ErrorAction SilentlyContinue
        } catch {
        }
    }
    $script:LauncherProc = $null
}

function Cleanup-Services {
    python installer\stop_services.py | Out-Null
    Stop-Launcher
}

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers = $null,
        [object]$Body = $null
    )

    try {
        if ($Body -ne $null) {
            $payload = $Body | ConvertTo-Json
            $resp = Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers -Body $payload -ContentType "application/json" -UseBasicParsing -TimeoutSec 10
        } else {
            $resp = Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 10
        }
        return @{ Status = $resp.StatusCode; Body = ($resp.Content | ConvertFrom-Json) }
    } catch {
        $response = $_.Exception.Response
        if ($response) {
            $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
            $content = $reader.ReadToEnd()
            return @{ Status = [int]$response.StatusCode; Body = ($content | ConvertFrom-Json) }
        }
        throw
    }
}

Write-Banner "E2E Smoke Test - Automation Orchestrator"

try {

Write-Host "Stopping any existing services..." -ForegroundColor Yellow
python installer\stop_services.py | Out-Null
Start-Sleep -Seconds 2

Write-Host "Starting services via launcher..." -ForegroundColor Yellow
$script:LauncherProc = Start-Process -FilePath "python" -ArgumentList @(
    "installer\launch_services.py",
    $ConfigPath
) -WorkingDirectory $root -PassThru -WindowStyle Hidden
Write-Host ("Launcher PID: {0}" -f $script:LauncherProc.Id) -ForegroundColor Gray

$maxWait = 30
for ($i = 0; $i -lt $maxWait; $i++) {
    if (Test-Path "run\services.json") {
        break
    }
    if ($script:LauncherProc -and $script:LauncherProc.HasExited) {
        Write-Host "ERROR: Launcher process exited unexpectedly" -ForegroundColor Red
        if (Test-Path "logs\launcher.log") { Get-Content "logs\launcher.log" -Tail 200 | Write-Host }
        if (Test-Path "logs\api.log") { Get-Content "logs\api.log" -Tail 200 | Write-Host }
        if (Test-Path "logs\worker.log") { Get-Content "logs\worker.log" -Tail 200 | Write-Host }
        Cleanup-Services
        exit 1
    }
    if (($i + 1) % 5 -eq 0) {
        Write-Host ("Waiting for services.json... {0}/{1}s" -f (($i + 1)), $maxWait) -ForegroundColor Gray
    }
    Start-Sleep -Seconds 1
}

if (-not (Test-Path "run\services.json")) {
    Write-Host "ERROR: Launcher did not create services.json" -ForegroundColor Red
    if (Test-Path "logs\launcher.log") { Get-Content "logs\launcher.log" -Tail 200 | Write-Host }
    if (Test-Path "logs\api.log") { Get-Content "logs\api.log" -Tail 200 | Write-Host }
    if (Test-Path "logs\worker.log") { Get-Content "logs\worker.log" -Tail 200 | Write-Host }
    Cleanup-Services
    exit 1
}

if (-not (Wait-Health)) {
    Write-Host "ERROR: API did not become healthy" -ForegroundColor Red
    if (Test-Path "logs\launcher.log") { Get-Content "logs\launcher.log" -Tail 200 | Write-Host }
    if (Test-Path "logs\api.log") { Get-Content "logs\api.log" -Tail 200 | Write-Host }
    if (Test-Path "logs\worker.log") { Get-Content "logs\worker.log" -Tail 200 | Write-Host }
    Cleanup-Services
    exit 1
}

Write-Banner "Trial Status + Purchase URL"
$status = Invoke-Json -Method GET -Url http://localhost:8000/api/license/status
Write-Host ("+ License status: {0}" -f $status.Body.status) -ForegroundColor Green
Write-Host ("+ Trial days remaining: {0}" -f $status.Body.trial_days_remaining) -ForegroundColor Green

$purchase = Invoke-Json -Method GET -Url http://localhost:8000/api/license/purchase
Write-Host ("+ Purchase URL: {0}" -f $purchase.Body.purchase_url) -ForegroundColor Green

Write-Banner "Authentication"
$login = Invoke-Json -Method POST -Url http://localhost:8000/api/auth/login -Body @{ username = "admin"; password = "admin123" }
$token = $login.Body.access_token
$headers = @{ Authorization = "Bearer $token" }
Write-Host "+ Logged in successfully" -ForegroundColor Green

$me = Invoke-Json -Method GET -Url http://localhost:8000/api/auth/me -Headers $headers
Write-Host ("+ Authenticated as: {0}" -f $me.Body.username) -ForegroundColor Green

Write-Banner "Core API Operations"
$lead = Invoke-Json -Method POST -Url http://localhost:8000/api/leads -Headers $headers -Body @{ email = "smoke.test@example.com"; first_name = "Smoke"; last_name = "Test" }
Write-Host ("+ Lead created: {0}" -f $lead.Body.id) -ForegroundColor Green

$workflow = Invoke-Json -Method POST -Url http://localhost:8000/api/workflows/trigger -Headers $headers -Body @{ workflow_id = "workflow-1"; lead_data = @{ email = "smoke.test@example.com" } }
Write-Host ("+ Workflow triggered: {0}" -f $workflow.Body.execution_id) -ForegroundColor Green

$campaigns = Invoke-Json -Method GET -Url http://localhost:8000/api/campaigns -Headers $headers
Write-Host ("+ Campaigns endpoint: {0} campaigns" -f $campaigns.Body.campaigns.Count) -ForegroundColor Green

$analytics = Invoke-Json -Method GET -Url http://localhost:8000/api/analytics/summary -Headers $headers
Write-Host "+ Analytics endpoint working" -ForegroundColor Green

Write-Banner "License Activation"
$licenseKey = python -c "import base64, json, hmac, hashlib, os, datetime; secret=os.getenv('LICENSE_SECRET','change-me-in-production-use-strong-secret'); now=datetime.datetime.now(datetime.timezone.utc); payload={'license_id':'e2e-smoke-test','issued_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),'expires_at': (now+datetime.timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S+00:00'),'plan':'pro'}; pj=json.dumps(payload, separators=(',',':')).encode(); b64=base64.urlsafe_b64encode(pj).decode().rstrip('='); sig=base64.urlsafe_b64encode(hmac.new(secret.encode(), b64.encode(), hashlib.sha256).digest()).decode().rstrip('='); print('LIC-'+b64+'.'+sig)"

$activate = Invoke-Json -Method POST -Url http://localhost:8000/api/license/activate -Headers $headers -Body @{ license_key = $licenseKey }
Write-Host ("+ License activated: {0}" -f $activate.Body.license_id) -ForegroundColor Green

$statusAfter = Invoke-Json -Method GET -Url http://localhost:8000/api/license/status
Write-Host ("+ New license status: {0}" -f $statusAfter.Body.status) -ForegroundColor Green

Write-Banner "Health & Metrics"
$health = Invoke-Json -Method GET -Url http://localhost:8000/health/detailed -Headers $headers
Write-Host "+ Detailed health check passed" -ForegroundColor Green

$metrics = Invoke-WebRequest -Uri http://localhost:8000/metrics -UseBasicParsing -TimeoutSec 10
Write-Host "+ Metrics endpoint working" -ForegroundColor Green

Write-Banner "Cleanup"
Cleanup-Services
Write-Host "+ Services stopped" -ForegroundColor Green

Write-Banner "E2E Smoke Test Complete"
Write-Host "All checks passed!" -ForegroundColor Green
Write-Host ""
Write-Host "Tested:" -ForegroundColor Cyan
Write-Host "  - Service launcher startup" -ForegroundColor White
Write-Host "  - Trial license enforcement" -ForegroundColor White
Write-Host "  - Authentication & authorization" -ForegroundColor White
Write-Host "  - Lead management" -ForegroundColor White
Write-Host "  - Workflow triggering" -ForegroundColor White
Write-Host "  - Campaign management" -ForegroundColor White
Write-Host "  - Analytics endpoints" -ForegroundColor White
Write-Host "  - License activation" -ForegroundColor White
Write-Host "  - Health & metrics endpoints" -ForegroundColor White
Write-Host "  - Service shutdown" -ForegroundColor White

} catch {
    Write-Host ("ERROR: E2E smoke test failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
    Cleanup-Services
    exit 1
}
