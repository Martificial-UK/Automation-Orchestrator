# Automation Orchestrator - Laptop Installation Quick Start

## Pre-Installation Checklist

### What You Need
1. **Python 3.8+** installed
   - Check: `python --version` or `python3 --version`
   - Download: https://www.python.org/downloads/
2. **Git** (optional, for cloning)
   - Or download ZIP from GitHub
3. **10 minutes** for installation

### Get the Code

**Option 1: Git Clone**
```bash
git clone https://github.com/Martificial-UK/Automation-Orchestrator.git
cd Automation-Orchestrator
```

**Option 2: Download ZIP**
1. Go to https://github.com/Martificial-UK/Automation-Orchestrator
2. Click "Code" → "Download ZIP"
3. Extract to desired location
4. Open terminal in extracted folder

## Installation

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File installer\install.ps1
```

Wait 2-3 minutes for dependencies to install and services to start.

### Linux/Mac
```bash
bash installer/install.sh
```

## Verify Installation

You should see:
```
========================================
Automation Orchestrator Started!
========================================
API Server: http://localhost:8000
API Docs: http://localhost:8000/api/docs

Default credentials:
  Username: admin
  Password: admin123

Services are running in the background.
To stop: python installer\stop_services.py
========================================
```

### Quick Test

1. **Open Browser**: http://localhost:8000/api/docs
2. **Click "Authorize"**
   - Username: `admin`
   - Password: `admin123`
3. **Try an API**: Expand `/api/license/status` → Click "Try it out" → "Execute"

Should see:
```json
{
  "status": "trial",
  "trial_days_remaining": 7,
  "purchase_url": "https://example.com/buy"
}
```

### Run Full E2E Test
```powershell
powershell -ExecutionPolicy Bypass -File scripts\e2e_smoke_simple.ps1
```

Expected output:
```
========================================
E2E Smoke Test - Automation Orchestrator
========================================

+ License status: trial
+ Trial days remaining: 7
+ Logged in successfully
+ Lead created: <uuid>
+ Workflow triggered: <uuid>
... (more tests)
All checks passed!
```

## What's Running

Check service status:
```powershell
# Windows
Get-Content run\services.json

# Linux/Mac
cat run/services.json
```

View logs:
```powershell
# API server log
Get-Content logs\api.log

# Worker log
Get-Content logs\worker.log

# Launcher log
Get-Content logs\launcher.log
```

## Stop Services
```bash
python installer\stop_services.py
```

## Restart Services
```bash
python installer\launch_services.py
```

## Common Issues

### Python not found
- Install Python 3.8+ from python.org
- Make sure "Add Python to PATH" was checked during install
- Restart terminal after installation

### Port 8000 already in use
```bash
python installer\stop_services.py
```
Wait 5 seconds, then start again.

### Dependencies fail to install
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Then install requirements
pip install -r requirements.txt
```

### Services won't start
1. Check logs: `logs/api.log`
2. Verify Python version: `python --version`
3. Check port is free: `netstat -ano | findstr :8000` (Windows) or `lsof -i :8000` (Mac/Linux)

## Next Steps

1. **Explore API Docs**: http://localhost:8000/api/docs
2. **Check Metrics**: http://localhost:8000/metrics
3. **Read Full Guide**: Open `INSTALL.md` for production setup
4. **Review Features**: See `README.md` for capabilities

## Trial Information

- **Duration**: 7 days from first start
- **Features**: Full access during trial
- **After Trial**: Demo mode (read-only)
- **Upgrade**: Contact for license key

Check trial status anytime:
```bash
curl http://localhost:8000/api/license/status
```

## Clean Uninstall

```bash
# Stop services
python installer\stop_services.py

# Remove virtual environment
rm -rf .venv  # Linux/Mac
Remove-Item -Recurse -Force .venv  # Windows

# Remove runtime files
rm -rf run/ logs/ config/license_state.json
```

## Support

- **Documentation**: `INSTALL.md`, `README.md`
- **Test Reports**: `STRESS_TEST_VALIDATION_REPORT.md`
- **Logs**: `logs/` directory

---

**Ready to go!** Your Automation Orchestrator is live at http://localhost:8000
