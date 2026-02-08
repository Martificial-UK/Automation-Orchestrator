# 🚀 Stress Testing - Complete Setup & Launch Guide

## Quick Start (< 5 minutes)

### Step 1: Start API Services

**Windows (PowerShell):**
```powershell
cd c:\AI Automation\Automation Orchestrator

# Install Docker Desktop if not installed:
# Download: https://www.docker.com/products/docker-desktop
# Then restart PowerShell

# Start services
docker compose up -d

# Wait 15 seconds for services to fully initialize
Start-Sleep -Seconds 15

# Verify API is running
curl http://localhost:8000/health
```

**macOS/Linux:**
```bash
cd ~/path/to/automation-orchestrator

docker-compose up -d

sleep 15

curl http://localhost:8000/health
```

### Step 2: Run Stress Test

In a **new terminal window**:

**Windows (PowerShell):**
```powershell
cd c:\AI Automation\Automation Orchestrator

# Light test (10 users, 2 minutes)
locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 5 --run-time 2m --headless

# Or use the helper script
.\run_stress_test.ps1
```

**macOS/Linux:**
```bash
cd ~/path/to/automation-orchestrator

# Light test
locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 5 --run-time 2m --headless

# Or use the helper script
bash run_stress_test.sh
```

---

## Real-time Monitoring Dashboard

While the stress test is running, **open these in your browser**:

1. **Locust Web UI** (if not using --headless):
   ```
   http://localhost:8089
   ```
   Shows: Real-time requests, response times, errors

2. **Grafana Dashboards**:
   ```
   http://localhost:3000
   Login: admin / admin
   ```
   Shows: Performance metrics, resource usage

3. **API Health**:
   ```
   http://localhost:8000/health
   http://localhost:8000/health/detailed
   ```
   Shows: API status, dependency health

4. **Prometheus Metrics**:
   ```
   http://localhost:9090
   ```
   Shows: Raw metrics data

---

## Test Scenarios

Choose based on your needs:

### 🟢 **Light Load (Baseline - Start Here)**
```bash
locust -f locustfile.py --host http://localhost:8000 \
  --users 10 --spawn-rate 5 --run-time 2m --headless

# Expected: Response time < 100ms, 0% errors
# Best for: Initial validation
```

### 🟡 **Medium Load (Normal)**
```bash
locust -f locustfile.py --host http://localhost:8000 \
  --users 50 --spawn-rate 10 --run-time 10m --headless

# Expected: Response time < 200ms, < 0.1% errors
# Best for: Performance baseline, load capacity
```

### 🔴 **Heavy Load (Stress)**
```bash
locust -f locustfile.py --host http://localhost:8000 \
  --users 200 --spawn-rate 20 --run-time 15m --headless

# Expected: Response time < 500ms, < 1% errors
# Best for: Finding bottlenecks
```

### 🟣 **Peak Load (Breaking Point)**
```bash
locust -f locustfile.py --host http://localhost:8000 \
  --users 500 --spawn-rate 50 --run-time 5m --headless

# Expected: Identify where system fails
# Best for: Capacity planning, auto-scaling testing
```

### 💜 **Spike Test (Sudden Surge)**
```bash
locust -f locustfile.py --host http://localhost:8000 \
  --users 500 --spawn-rate 100 --run-time 3m --headless

# Expected: Test recovery from sudden traffic spike
# Best for: Testing auto-scaling and resilience
```

### 🕐 **Soak Test (Long Duration)**
```bash
locust -f locustfile.py --host http://localhost:8000 \
  --users 30 --spawn-rate 10 --run-time 1h --headless

# Expected: Stable performance over extended run
# Best for: Finding memory leaks, connection issues
```

---

## With Web UI (Recommended for First Time)

Interactive monitoring in browser:

```bash
# Windows
locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 10

# macOS/Linux
locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 10
```

Then:
1. Open browser to: **http://localhost:8089**
2. Enter: 10 for initial users
3. Click **"Start swarming"**
4. Watch in real-time as users and requests increase
5. Monitor metrics as they update

---

## Understanding Results

### Response Times
```
Metric          value       meaning
──────────────────────────────────
Mean (Avg)      50-100ms    Normal, healthy
P95             100-200ms   Good, acceptable
P99             200-500ms   Getting slow
Max             > 1s        Occasional issues
```

### Error Rates
```
Rate            Status      Action
─────────────────────────────────
0%              ✅ Good     All requests succeeded
< 0.1%          ✅ Fine     Expected network variance
0.1-1%          ⚠️  Watch   Minor issues
> 1%            ❌ Bad      Investigate errors
```

### Resource Usage
```
CPU             < 70%       ✅ Healthy
CPU             70-85%      ⚠️  Getting busy
CPU             > 85%       🔴 Critical

Memory          < 65%       ✅ Healthy
Memory          65-80%      ⚠️  Watch it
Memory          > 80%       🔴 Critical

DB Connections  < 80% pool  ✅ Healthy
DB Connections  > 90% pool  🔴 Connection pool exhausted
```

---

## Sample Output Explained

```
[2024-02-05 10:15:30]  Starting test...
[2024-02-05 10:15:31]  ✓ API health check passed
[2024-02-05 10:15:32]  [SLOW] GET /api/workflows          2500ms   200
[2024-02-05 10:15:33]  [ERROR] POST /api/leads            5000ms   ConnectionError
[2024-02-05 10:16:00]
20:00  Spawned 1 user
22:52  Spawned 1 user
00:15  Spawned 1 user

======================== RESULTS ========================

Endpoint                         Reqs     Avg(ms)  P95(ms)  Max(ms)  Failed
────────────────────────────────────────────────────────────────────────
/api/workflows                  1,250     120      250      2,500    0
POST /api/leads                   450      180      400      5,000    5
GET /health                       500       5       10       50       0
GET /api/campaigns                320      210      500      3,000    0

Total Requests:   2,520
Total Failures:   5 (0.2%)
Avg Response:     150ms
P95 Response:     350ms
P99 Response:     800ms
```

---

## Troubleshooting

### ❌ "API not responding"
```bash
# Check if services are running
docker compose ps

# Check API logs
docker compose logs api

# Restart services
docker compose restart api

# Wait 10 seconds and test again
curl http://localhost:8000/health
```

### ❌ "locust command not found"
```bash
# Reinstall Locust
pip install --upgrade locust

# Verify
locust --version
```

### ❌ "Connection refused on port 8000"
```bash
# Make sure API is running
docker compose ps

# Check if port is in use
# Windows: netstat -ano | findstr :8000
# macOS/Linux: lsof -i :8000

# Start API if not running
docker compose up -d api
```

### ❌ "High error rate during test"
```bash
# Check API logs in real-time
docker compose logs -f api

# Check database is running
docker compose logs -f db

# Check credentials in locustfile.py
# Default: username=admin, password=admin

# Verify database is initialized
curl http://localhost:8000/health/detailed
```

### ❌ "Memory keeps growing"
```bash
# Run a soak test to identify leak:
locust -f locustfile.py --host http://localhost:8000 \
  --users 20 --spawn-rate 5 --run-time 30m --headless

# Monitor memory with Docker
docker stats automation-orchestrator-api

# Look for steady increase = memory leak
```

---

## Saving Results

### Export Grafana Dashboard
1. Go to http://localhost:3000
2. Select dashboard
3. Click **"Share"** → **"PDF"** or **"Image"**
4. Save for comparison

### Export Locust Results
1. Run test in **Web UI**: http://localhost:8089
2. Test completes
3. Click **"Download report as HTML"**
4. Save for documentation

### Manual Results Capture
```bash
# During test in another terminal:

# Get current metrics
curl http://localhost:8000/metrics > metrics.txt

# Get health status
curl http://localhost:8000/health/detailed > health.json

# Check Docker stats
docker stats --no-stream > docker_stats.txt
```

---

## Complete Test Workflow

```
┌─────────────────────────────────────┐
│ 1. Start Docker Services            │
│    docker compose up -d              │
│    Wait 15 seconds                   │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 2. Verify API Healthy               │
│    curl http://localhost:8000/health │
│    Should see JSON response          │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 3. Open Monitoring Dashboards       │
│    - Grafana: localhost:3000         │
│    - Prometheus: localhost:9090      │
│    (optional but recommended)        │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 4. Start Stress Test                │
│    locust -f locustfile.py ...       │
│    (in separate terminal)            │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 5. Monitor in Real-Time             │
│    Watch requests/responses          │
│    Check error messages              │
│    Monitor resource usage            │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 6. Let Test Complete                │
│    Wait for duration to finish       │
│    View final summary                │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 7. Review & Document Results        │
│    Save Grafana screenshots          │
│    Export HTML report                │
│    Compare with baseline             │
└─────────────────────────────────────┘
```

---

## Files Created

- **locustfile.py** - Main stress test scenarios (350+ lines)
- **run_stress_test.ps1** - Windows automation script
- **run_stress_test.sh** - macOS/Linux automation script
- **STRESS_TESTING_GUIDE.md** - This guide (you are here!)

---

## Quick Reference Commands

```bash
# Baseline test (recommended to start)
locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 5 --run-time 2m --headless

# Normal load
locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 10 --run-time 10m --headless

# Heavy load
locust -f locustfile.py --host http://localhost:8000 --users 200 --spawn-rate 20 --run-time 15m --headless

# With web UI (interactive)
locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 10

# Soak test (1 hour sustainability)
locust -f locustfile.py --host http://localhost:8000 --users 30 --spawn-rate 10 --run-time 1h --headless

# Spike test
locust -f locustfile.py --host http://localhost:8000 --users 500 --spawn-rate 100 --run-time 3m --headless

# Check API status
curl http://localhost:8000/health

# Check detailed health
curl http://localhost:8000/health/detailed

# View metrics
curl http://localhost:8000/metrics | grep http_
```

---

## Next Steps

1. ✅ Ensure Docker is installed and running
2. ✅ Start services: `docker compose up -d`
3. ✅ Verify API: `curl http://localhost:8000/health`
4. ✅ Run baseline test: `locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 5 --run-time 2m --headless`
5. ✅ Progress to heavier tests as comfortable
6. ✅ Document baseline metrics
7. ✅ Share results with team

---

## Support

- **Issues with Docker?** See DOCKER_QUICK_START.md
- **Issues with API?** See PRODUCTION_DEPLOYMENT_GUIDE.md
- **Questions about monitoring?** See MONITORING_ALERTING_GUIDE.md
- **Locust documentation**: https://docs.locust.io/

---

**You're all set! Ready to stress test! 🚀**

Start with: `locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 5 --run-time 2m --headless`
