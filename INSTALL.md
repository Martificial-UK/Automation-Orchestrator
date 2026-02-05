# Automation Orchestrator - Installation Guide

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Windows or Linux

### One-Click Installation

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File installer\install.ps1
```

**Linux/Mac:**
```bash
bash installer/install.sh
```

The installer will:
1. Create a Python virtual environment (`.venv`)
2. Install all dependencies
3. Start all services (API server + background worker)
4. Display the server URL

### Services

After installation, the following services will be running:
- **API Server**: http://localhost:8000
- **Background Worker**: Processing tasks from the queue
- **Redis** (if available): Task queue backend

### Default Credentials
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Change these credentials in production!**

## Trial & Licensing

### 7-Day Trial
Your installation starts with a **7-day trial** with full access to all features.

Check your trial status:
```bash
curl http://localhost:8000/api/license/status
```

### Purchase a License
Visit the purchase URL provided in the trial status response to upgrade.

Activate your license:
```bash
curl -X POST http://localhost:8000/api/license/activate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"license_key": "YOUR_LICENSE_KEY"}'
```

### Demo Mode
After the trial expires, the system enters **demo mode** with:
- ✅ Read-only access to all endpoints
- ✅ View analytics, leads, campaigns
- ❌ No write operations (create/update/delete)
- ✅ Activate a license to restore full access

## Managing Services

### Stop Services
```powershell
# Windows
python installer\stop_services.py

# Linux/Mac
python3 installer/stop_services.py
```

### Start Services
```powershell
# Windows
python installer\launch_services.py

# Linux/Mac
python3 installer/launch_services.py
```

### Check Service Status
```powershell
# Windows
Get-Content run\services.json | ConvertFrom-Json

# Linux/Mac
cat run/services.json
```

## Configuration

### Custom Configuration
Edit `config/sample_config.json` or create your own:

```json
{
  "log_level": "INFO",
  "auth": {
    "enabled": true
  },
  "rate_limit": {
    "enabled": true,
    "window_seconds": 60,
    "max_requests": 120
  },
  "license": {
    "enabled": true,
    "trial_days": 7,
    "purchase_url": "https://example.com/buy"
  }
}
```

Use a custom config:
```bash
python installer\launch_services.py path\to\config.json
```

### Environment Variables
- `AO_CONFIG`: Path to configuration file
- `JWT_SECRET`: Secret key for JWT tokens (change in production!)
- `LICENSE_SECRET`: Secret key for license validation (change in production!)

## API Documentation

Once services are running, visit:
- **Interactive API Docs**: http://localhost:8000/api/docs
- **Metrics**: http://localhost:8000/metrics
- **Health Check**: http://localhost:8000/health

## Offline Installation

### Bundle Dependencies
On a machine with internet access:
```bash
pip download -r requirements.txt -d vendor/wheels
```

Copy the entire project folder to the offline machine and run the installer.

### Bundle Redis (Optional)
Download Redis binaries and place in `vendor/redis/`:
- Windows: `redis-server.exe`
- Linux: `redis-server`

The installer will detect and use the bundled Redis.

## Testing

### Run E2E Smoke Test
```powershell
powershell -ExecutionPolicy Bypass -File scripts\e2e_smoke_simple.ps1
```

This validates:
- Service startup
- Authentication
- API operations
- License management
- Health checks

## Troubleshooting

### Services won't start
1. Check Python version: `python --version` (must be 3.8+)
2. Check logs: `logs/api.log`, `logs/worker.log`
3. Verify port 8000 is free
4. Check services.json was created: `run/services.json`

### Port already in use
Stop existing services:
```powershell
python installer\stop_services.py
```

### License issues
Check license state:
```powershell
# Windows
Get-Content config\license_state.json

# Linux/Mac
cat config/license_state.json
```

Delete license state to reset trial:
```bash
rm config/license_state.json
```

### Dependencies missing
Reinstall from the project root:
```bash
pip install -r requirements.txt
```

## Production Deployment

### Security Checklist
- [ ] Change default admin password
- [ ] Set strong `JWT_SECRET` environment variable
- [ ] Set strong `LICENSE_SECRET` environment variable
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Enable rate limiting
- [ ] Review and restrict API access

### Systemd Service (Linux)
Create `/etc/systemd/system/automation-orchestrator.service`:
```ini
[Unit]
Description=Automation Orchestrator
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Automation Orchestrator
ExecStart=/path/to/Automation Orchestrator/.venv/bin/python installer/launch_services.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable automation-orchestrator
sudo systemctl start automation-orchestrator
```

### Windows Service
Use NSSM (Non-Sucking Service Manager):
```powershell
nssm install AutomationOrchestrator "C:\Path\To\Python\python.exe" "C:\Path\To\installer\launch_services.py"
nssm start AutomationOrchestrator
```

## Support

For issues, questions, or feature requests, check:
- `README.md` for project overview
- `STRESS_TEST_VALIDATION_REPORT.md` for performance metrics
- Log files in `logs/` directory
