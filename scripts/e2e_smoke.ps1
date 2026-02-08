param(
    [string]$ConfigPath = "config\sample_config.json",
    [int]$Port = 8000,
    [switch]$ForceStopPort
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$baseUrl = "http://localhost:$Port"
$script:ApiProc = $null

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
            $code = (Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing -TimeoutSec 5).StatusCode
            if ($code -eq 200) {
                return $true
            }
        } catch {
        }
        Start-Sleep -Seconds $DelaySeconds
    }
    return $false
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

function Write-JsonFile {
    param(
        [string]$Path,
        [object]$Object
    )

    $json = $Object | ConvertTo-Json -Depth 10
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json, $utf8NoBom)
}

function Ensure-Port-Free {
    param([int]$Port)
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        $pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
        if (-not $ForceStopPort) {
            throw "Port $Port is already in use by PID(s): $($pids -join ', '). Re-run with -ForceStopPort to stop them."
        }
        foreach ($procId in $pids) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Start-Api {
    param([string]$ConfigPathOverride = $null)

    $useConfig = $ConfigPath
    if ($ConfigPathOverride) {
        $useConfig = $ConfigPathOverride
    }

    $runDir = Join-Path $root "run"
    if (-not (Test-Path $runDir)) {
        New-Item -ItemType Directory -Path $runDir | Out-Null
    }

    $servicesFile = Join-Path $runDir "services.json"
    if (Test-Path $servicesFile) {
        Remove-Item -Path $servicesFile -Force -ErrorAction SilentlyContinue
    }

    $prevConfig = $env:AO_CONFIG
    $env:AO_CONFIG = $useConfig

    Write-Host "Starting services via launcher..." -ForegroundColor Yellow
    $script:ApiProc = Start-Process -FilePath "python" -ArgumentList @(
        "installer\launch_services.py",
        $useConfig
    ) -WorkingDirectory $root -PassThru -WindowStyle Hidden

    $env:AO_CONFIG = $prevConfig

    # Wait for services.json to be created
    $maxWait = 30
    for ($i = 0; $i -lt $maxWait; $i++) {
        if (Test-Path $servicesFile) {
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not (Test-Path $servicesFile)) {
        Stop-Api
        throw "Launcher did not create services.json"
    }

    if (-not (Wait-Health)) {
        Stop-Api
        throw "API did not become healthy"
    }

    return $script:ApiProc
}

function Stop-Api {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    python installer\stop_services.py | Out-Null
    
    # Wait for port to be freed
    $maxWait = 10
    for ($i = 0; $i -lt $maxWait; $i++) {
        $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if (-not $listeners) {
            break
        }
        Start-Sleep -Seconds 1
    }
    
    # Force kill any remaining processes on the port
    Ensure-Port-Free -Port $Port
    
    if ($script:ApiProc -and -not $script:ApiProc.HasExited) {
        Stop-Process -Id $script:ApiProc.Id -Force -ErrorAction SilentlyContinue
    }
    $script:ApiProc = $null
    
    Start-Sleep -Seconds 2
}

Write-Banner "E2E Smoke Test - Automation Orchestrator"

$runDir = Join-Path $root "run"
if (-not (Test-Path $runDir)) {
    New-Item -ItemType Directory -Path $runDir | Out-Null
}
$trialConfigPath = Join-Path $runDir "trial_config.json"
$trialStatePath = Join-Path $runDir "trial_license_state.json"

$trialState = @{ trial_start_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss+00:00") }
Write-JsonFile -Path $trialStatePath -Object $trialState

$trialConfig = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
$trialConfig.license.trial_days = 7
$trialConfig.license.state_path = $trialStatePath
Write-JsonFile -Path $trialConfigPath -Object $trialConfig

Ensure-Port-Free -Port $Port
Stop-Api
Start-Api -ConfigPathOverride $trialConfigPath | Out-Null

Write-Banner "Trial Status + Purchase URL"
$status = Invoke-Json -Method GET -Url "$baseUrl/api/license/status"
if ($status.Body.status -ne "trial") {
    Stop-Api
    throw "Expected license status trial, got $($status.Body.status)"
}
Write-Host ("License status: {0}, trial days remaining: {1}" -f $status.Body.status, $status.Body.trial_days_remaining)
$purchase = Invoke-Json -Method GET -Url "$baseUrl/api/license/purchase"
Write-Host ("Purchase URL: {0}" -f $purchase.Body.purchase_url)

Write-Banner "Login + Core API"
$login = Invoke-Json -Method POST -Url "$baseUrl/api/auth/login" -Body @{ username = "admin"; password = "admin123" }
$token = $login.Body.access_token
$headers = @{ Authorization = "Bearer $token" }

$me = Invoke-Json -Method GET -Url "$baseUrl/api/auth/me" -Headers $headers
Write-Host ("Logged in as: {0}" -f $me.Body.username)

$lead = Invoke-Json -Method POST -Url "$baseUrl/api/leads" -Headers $headers -Body @{ email = "trial.smoke@example.com"; first_name = "Trial"; last_name = "Smoke" }
Write-Host ("Lead created: {0}" -f $lead.Body.id)

$workflow = Invoke-Json -Method POST -Url "$baseUrl/api/workflows/trigger" -Headers $headers -Body @{ workflow_id = "workflow-1"; lead_data = @{ email = "trial.smoke@example.com" } }
Write-Host ("Workflow triggered: {0}" -f $workflow.Body.execution_id)

Write-Banner "Force Demo Mode"
$demoConfigPath = Join-Path $runDir "demo_config.json"
$demoStatePath = Join-Path $runDir "demo_license_state.json"

$demoState = @{ trial_start_at = (Get-Date).ToUniversalTime().AddDays(-8).ToString("yyyy-MM-ddTHH:mm:ss+00:00") }
Write-JsonFile -Path $demoStatePath -Object $demoState

$demoConfig = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
$demoConfig.license.trial_days = 0
$demoConfig.license.state_path = $demoStatePath
Write-JsonFile -Path $demoConfigPath -Object $demoConfig

Stop-Api
Ensure-Port-Free -Port $Port
Start-Sleep -Seconds 3
Start-Api -ConfigPathOverride $demoConfigPath | Out-Null

$demoStatus = Invoke-Json -Method GET -Url "$baseUrl/api/license/status"
if ($demoStatus.Body.status -ne "demo") {
    Stop-Api
    throw "Expected license status demo after trial expiry, got $($demoStatus.Body.status)"
}

$login = Invoke-Json -Method POST -Url "$baseUrl/api/auth/login" -Body @{ username = "admin"; password = "admin123" }
$token = $login.Body.access_token
$headers = @{ Authorization = "Bearer $token" }

$demoWrite = Invoke-Json -Method POST -Url "$baseUrl/api/leads" -Headers $headers -Body @{ email = "demo.blocked@example.com"; first_name = "Demo"; last_name = "Blocked" }
if ($demoWrite.Status -ne 402) {
    Stop-Api
    throw "Expected demo write to be blocked with 402, got $($demoWrite.Status)"
}
Write-Host "Demo mode blocking confirmed (402)" -ForegroundColor Green

Write-Banner "Activate License"
$licenseKey = python -c "import base64, json, hmac, hashlib, os, datetime; secret=os.getenv('LICENSE_SECRET','change-me-in-production-use-strong-secret'); now=datetime.datetime.now(datetime.timezone.utc); payload={'license_id':'trial-upgrade','issued_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),'expires_at': (now+datetime.timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S+00:00'),'plan':'pro'}; pj=json.dumps(payload, separators=(',',':')).encode(); b64=base64.urlsafe_b64encode(pj).decode().rstrip('='); sig=base64.urlsafe_b64encode(hmac.new(secret.encode(), b64.encode(), hashlib.sha256).digest()).decode().rstrip('='); print('LIC-'+b64+'.'+sig)"

$activate = Invoke-Json -Method POST -Url "$baseUrl/api/license/activate" -Headers $headers -Body @{ license_key = $licenseKey }
Write-Host ("License activated: {0}" -f $activate.Body.license_id)

$lead2 = Invoke-Json -Method POST -Url "$baseUrl/api/leads" -Headers $headers -Body @{ email = "licensed.ok@example.com"; first_name = "Licensed"; last_name = "Ok" }
Write-Host ("Licensed lead created: {0}" -f $lead2.Body.id)

Stop-Api

Write-Banner "E2E Smoke Test Complete"
Write-Host "All checks passed." -ForegroundColor Green
