# Fix #3 Deployment Guide - Redis Queue System

## Current Status

✅ **Implementation Complete**: redis_queue.py and task_worker.py are fully implemented
✅ **Fix #1 Validated**: Multi-worker deployment achieving 98.58% pass rate
✅ **Fix #2 Validated**: PUT endpoint debug server fully operational
⏳ **Fix #3 Ready for Deployment**: Requires Redis installation

---

## Prerequisites

### Option 1: Windows Redis Installation (Recommended for Development)

**Using Windows Subsystem for Linux (WSL2):**
```powershell
# Option A: Install Redis on WSL2 Ubuntu
wsl
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

**Using Docker Desktop (Recommended for Production):**
```powershell
# Option B: Docker Container (requires Docker Desktop)
docker run -d -p 6379:6379 --name automation-redis redis:latest
```

**Using Memurai (Windows-native Redis port):**
```powershell
# Option C: Download and install from https://github.com/microsoftarchive/redis/releases
# Then run: redis-server.exe
```

**Using Chocolatey:**
```powershell
choco install redis-64
# Start service: redis-server
```

---

## Deployment Steps

### Step 1: Verify Redis Installation

```powershell
cd c:\AI Automation\Automation Orchestrator
redis-cli ping
# Expected response: PONG
```

### Step 2: Start Redis Server (if not already running)

**Option A - WSL2:**
```bash
# In WSL2 terminal
sudo service redis-server start
redis-cli ping  # Verify connection
```

**Option B - Docker:**
```powershell
docker run -d -p 6379:6379 --name automation-redis redis:latest
```

**Option C - Windows native:**
```powershell
redis-server
# Redis will be listening on localhost:6379
```

### Step 3: Verify Redis Connection from Python

```powershell
python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0); print(r.ping())"
# Expected: True
```

### Step 4: Start Task Worker(s)

**Terminal 1 - Main API Server (Fix #1):**
```powershell
cd c:\AI Automation\Automation Orchestrator
python -m uvicorn src.automation_orchestrator.wsgi:app --host 0.0.0.0 --port 8000 --workers 4
```

**Terminal 2 - Debug Server (Fix #2):**
```powershell
cd c:\AI Automation\Automation Orchestrator
python put_endpoint_debug.py
# Listens on 127.0.0.1:8001
```

**Terminal 3 - Task Worker 1 (Fix #3):**
```powershell
cd c:\AI Automation\Automation Orchestrator
python task_worker.py --queue default --worker-id worker-1
```

**Terminal 4 - Task Worker 2 (Fix #3 - Optional for load distribution):**
```powershell
cd c:\AI Automation\Automation Orchestrator
python task_worker.py --queue default --worker-id worker-2
```

### Step 5: Verify All Components Running

```powershell
# Check if all processes are listening
netstat -ano | findstr "8000|8001|6379"
```

Expected output:
```
127.0.0.1:6379   (Redis)
0.0.0.0:8000     (Main API with 4 workers)
127.0.0.1:8001   (Debug server)
```

### Step 6: Health Check All Services

```powershell
# API Health
curl http://localhost:8000/health

# Debug Server Health
curl http://localhost:8001/health

# Redis Health
redis-cli ping
# Response: PONG

# Task Worker Status (via logs)
# Check worker terminal output for "Worker worker-1 started" messages
```

---

## Configuration Options

### Redis Connection Settings

Edit `src/automation_orchestrator/config.py` to customize Redis connection:

```python
REDIS_CONFIG = {
    'host': 'localhost',      # Redis server host
    'port': 6379,             # Redis server port
    'db': 0,                  # Redis database number
    'password': None,         # Redis password (if auth enabled)
    'socket_timeout': 5,      # Connection timeout
    'socket_connect_timeout': 5,
    'connection_pool_max': 10 # Max connections
}
```

### Task Worker Configuration

```powershell
# Run with custom queue name
python task_worker.py --queue priority-tasks --worker-id worker-1

# Run with polling interval (seconds)
python task_worker.py --poll-interval 1 --worker-id worker-1
```

---

## Performance Expectations

### Single Worker (Baseline - Before Fix #3)
- Average Response: 35.3 seconds
- Pass Rate: 85-90%
- Throughput: ~537 requests in 10 minutes

### Multi-Worker (After Fix #1)
- Average Response: 8.9 seconds
- Pass Rate: 98.58%
- Throughput: ~2,739 requests in 10 minutes

### Multi-Worker + Async Tasks (After Fix #3)
- Expected Average Response: **<1 second**
- Expected Pass Rate: **99%+**
- Expected Throughput: **3,000+ requests in 10 minutes**

---

## Stress Testing with All Fixes

### Prerequisites
- Locust installed: `pip install locust`
- All three components running (see Step 4)

### Run 10-Minute Stress Test

```powershell
cd c:\AI Automation\Automation Orchestrator
locust -f locustfile_final.py --headless -u 50 -r 5 -t 10m --host http://localhost:8000
```

### Expected Results
- **Total Requests**: 3,000+
- **Success Rate**: 99%+
- **Average Response**: <1 second
- **Max Response**: <10 seconds
- **Connection Resets**: 0
- **Remote Disconnects**: 0

---

## Troubleshooting

### Issue: "ConnectionError: Error 111 connecting to localhost:6379"

**Solution**: Redis is not running
```powershell
# Start Redis
redis-server

# Or in Docker
docker run -d -p 6379:6379 redis:latest

# Verify
redis-cli ping
```

### Issue: "ModuleNotFoundError: No module named 'redis'"

**Solution**: Install Redis Python client
```powershell
pip install redis
```

### Issue: "Address already in use" on port 8000/8001

**Solution**: Kill existing processes
```powershell
# Kill all Python processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Or kill specific port
Get-NetTCPConnection -LocalPort 8000 | Select -ExpandProperty OwningProcess | ForEach-Object {Stop-Process -Id $_ -Force}
```

### Issue: Task worker not processing tasks

**Solution**: Check logs
```powershell
# Verify worker is connected to Redis
# Should see: "Worker worker-1 started successfully"
# And: "Waiting for tasks on queue: default"

# Check Redis queue size
redis-cli LLEN automation:queue:default
```

---

## Deployment Checklist

- [ ] Redis server installed
- [ ] Redis service running (verify with `redis-cli ping`)
- [ ] Python redis module installed
- [ ] API server started with 4 workers
- [ ] Debug server started
- [ ] At least 1 task worker started
- [ ] All health checks passing
- [ ] Redis is accessible (redis-cli connects)
- [ ] Task workers show "started successfully" in logs

---

## Production Deployment Recommendations

### 1. Use Docker Compose
```yaml
version: '3.8'
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  api:
    build: .
    command: python -m uvicorn src.automation_orchestrator.wsgi:app --host 0.0.0.0 --port 8000 --workers 4
    ports:
      - "8000:8000"
    depends_on:
      - redis

  worker:
    build: .
    command: python task_worker.py --queue default --worker-id worker-1
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis

volumes:
  redis-data:
```

### 2. Use Process Manager (PM2)
```powershell
npm install -g pm2

pm2 start "redis-server" --name "redis"
pm2 start "python -m uvicorn src.automation_orchestrator.wsgi:app --workers 4" --name "api"
pm2 start "python task_worker.py" --name "worker-1"
pm2 start "python task_worker.py" --name "worker-2"

pm2 save
pm2 startup
```

### 3. Horizontal Scaling
- Run multiple task workers on different machines
- Use Redis Sentinel for HA
- Configure load balancer for API servers (Nginx/HAProxy)

---

## Next Steps

1. **Install Redis** using one of the methods above
2. **Start all services** (API, Debug, Worker) in separate terminals
3. **Run health checks** to verify connectivity
4. **Execute stress test** with locustfile_final.py
5. **Monitor metrics** for 99%+ pass rate achievement
6. **Deploy to production** using Docker Compose or PM2

---

## Validation Success Criteria

✅ All three fixes deployed and running
✅ Pass rate ≥ 99%
✅ Average response time < 1 second
✅ Zero connection resets/disconnects
✅ All health checks passing
✅ 3,000+ requests processed in 10 minutes

---

## Contact & Support

For issues or questions about the Fix #3 deployment, refer to:
- [FIX_3_REDIS_QUEUE_INTEGRATION.md](FIX_3_REDIS_QUEUE_INTEGRATION.md)
- [COMPLETE_FIX_IMPLEMENTATION_SUMMARY.md](COMPLETE_FIX_IMPLEMENTATION_SUMMARY.md)
- Main API logs in `logs/` directory
