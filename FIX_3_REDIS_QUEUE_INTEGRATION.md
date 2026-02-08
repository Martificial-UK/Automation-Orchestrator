# Fix #3: Redis Background Task Queue Integration Guide

## Overview
This document explains how to integrate the Redis background task queue into the Automation Orchestrator API to decouple async CRM operations from request handling.

## Components

### 1. `redis_queue.py` - Redis Queue Implementation
- `RedisQueue` class: Core queue logic
- Task status tracking (PENDING, PROCESSING, COMPLETED, FAILED, RETRY)
- Non-blocking task enqueueing
- Automatic retry handling
- Task metadata and status retrieval

### 2. `task_worker.py` - Background Task Worker
- Standalone process that consumes tasks from Redis queue
- Task handlers for different task types
- Graceful shutdown handling
- Performance metrics tracking

### 3. Integration into API

## Installation

### Step 1: Install Redis
```bash
# Option A: Windows Subsystem for Linux (WSL)
wsl
sudo apt-get update
sudo apt-get install redis-server
redis-server

# Option B: Docker
docker run -d -p 6379:6379 redis:latest

# Option C: Native Windows (using Memurai)
# Download from: https://github.com/microsoftarchive/memurai-db/releases
# Or use Windows Package Manager:
choco install memurai
```

### Step 2: Install Python Dependencies
```bash
pip install redis
```

## Usage

### In API Endpoints (Replacing BackgroundTasks)

**Before (In-Process):**
```python
from fastapi import BackgroundTasks

@app.put("/api/leads/{lead_id}")
async def update_lead(lead_id: str, lead: LeadData, background_tasks: BackgroundTasks):
    # Update cache
    app.state.leads_cache[lead_id] = lead_dict
    
    # Queue background task (in-process, blocks request)
    background_tasks.add_task(crm_connector.update_lead, lead_id, lead_dict)
    
    return response
```

**After (Redis Queue):**
```python
from src.automation_orchestrator.redis_queue import enqueue_background_task

@app.put("/api/leads/{lead_id}")
async def update_lead(lead_id: str, lead: LeadData):
    # Update cache
    app.state.leads_cache[lead_id] = lead_dict
    
    # Queue background task (non-blocking, returns immediately)
    task_id = await enqueue_background_task(
        "crm_update",
        {"lead_id": lead_id, "lead_data": lead_dict}
    )
    
    return response
```

### Running the System

**Terminal 1: Start Gunicorn API Server (Fix #1)**
```bash
cd "c:\AI Automation\Automation Orchestrator"
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.automation_orchestrator.wsgi:app --bind 0.0.0.0:8000
```

**Terminal 2: Start Redis Server**
```bash
# WSL
wsl
redis-server

# Or Docker
docker run -d -p 6379:6379 redis:latest

# Or Memurai (Windows - starts automatically as service)
# Verify: redis-cli ping -> should return PONG
```

**Terminal 3: Start Background Task Worker(s)**
```bash
cd "c:\AI Automation\Automation Orchestrator"
python task_worker.py --queue default --worker-id worker-1
```

**Terminal 4 (Optional): Start Additional Workers for Parallel Processing**
```bash
python task_worker.py --queue default --worker-id worker-2
```

## Architecture Benefits

### Before (In-Process)
```
REQUEST
  ↓
[API Thread] 
  ↓ (CRM operation blocks thread)
RESPONSE (after CRM completes)
```
- Single thread processes request AND CRM operation
- Slow CRM calls block other requests
- High latency, limited concurrency
- Result: Connection resets under load

### After (Redis Queue)
```
REQUEST
  ↓
[API Thread] → Queue Task → RESPONSE (immediate)
                   ↓
            [Worker Process 1] (CRM update)
            [Worker Process 2] (CRM update parallel)
            [Worker Process N] (CRM update parallel)
```
- API thread returns immediately
- CRM operations processed in parallel by workers
- All 4+ Gunicorn workers handle incoming requests
- Result: 100% pass rate, <1s response time

## Expected Improvements

| Metric | Before Fix #3 | After Fix #3 |
|--------|---------------|-------------|
| Request Latency | 35.3s avg | <1s avg |
| CRM Operation Latency | In-process (blocking) | Off-process (non-blocking) |
| Concurrent Requests | ~10 (Uvicorn limited) | 50+ (Gunicorn workers) |
| Connection Resets | 38 per test | ~0 |
| Pass Rate | 86.25% | ~100% |

## Monitoring

### Check Queue Status
```bash
redis-cli
> KEYS "ao:tasks:*"
> LLEN "ao:tasks:default"  # Queue length
> HGETALL "ao:tasks:task:<task_id>"  # Task details
```

### Worker Logs
The task worker outputs:
- Task processing status
- Performance metrics
- Error details
- Processing statistics on shutdown

Example output:
```
2024-01-15 10:30:45,123 - src.automation_orchestrator.task_worker - INFO - [worker-1] Worker started, polling queue 'default'
2024-01-15 10:30:46,234 - src.automation_orchestrator.task_worker - INFO - [worker-1] Processing task <task-id>: crm_update
2024-01-15 10:30:48,456 - src.automation_orchestrator.task_worker - INFO - Task <task-id> completed successfully (2.22s)
```

## Troubleshooting

### Issue: "Redis connection refused"
```
Solution: Ensure Redis server is running
  - WSL: Run `redis-server` in WSL terminal
  - Docker: Run `docker ps` to verify container running
  - Windows: Check Services for "Memurai" or "Redis"
```

### Issue: "Task not processing"
```
Solution: Check task worker is running
  - Verify terminal 3/4 showing "Worker started"
  - Check queue length: redis-cli LLEN "ao:tasks:default"
  - Increase log level for debugging
```

### Issue: "Tasks keep retrying"
```
Solution: Check task handler logs
  - Verify handler registered (check HANDLERS dict in task_worker.py)
  - Check CRM/Email configuration in config.yaml
  - Review error messages in worker log
```

## Configuration

### Redis Configuration (config.yaml)
```yaml
redis:
  host: "localhost"
  port: 6379
  db: 0
```

### Worker Configuration (command line)
```bash
# Process specific queue
python task_worker.py --queue crm_updates --worker-id worker-1

# Adjust poll interval (seconds between queue checks when empty)
python task_worker.py --poll-interval 2 --worker-id worker-1

# Multiple workers for parallel processing
python task_worker.py --queue default --worker-id worker-1 &
python task_worker.py --queue default --worker-id worker-2 &
python task_worker.py --queue default --worker-id worker-3 &
```

## Performance Targets

After all three fixes:

| Target | Details |
|--------|---------|
| **Pass Rate** | 100% success on all endpoints |
| **Response Time** | <1 second average, <10 seconds max |
| **Concurrency** | 50+ concurrent users sustained |
| **Connection Resets** | 0 (eliminated) |
| **CRM Latency** | Off-request path (async queue) |
| **Scalability** | Add workers per CPU core |

## Next Steps

1. **Deploy Fix #1**: Restart API with Gunicorn (4 workers)
2. **Deploy Fix #2**: Run isolated PUT debug server
3. **Deploy Fix #3**: 
   - Install Redis
   - Start Redis server
   - Start task worker(s)
   - Update API to use `enqueue_background_task`
4. **Run Final Test**: Execute locustfile_final.py against full stack
5. **Monitor**: Verify 100% pass rate and <1s response times

## Example Complete Setup

```bash
# Terminal 1: Gunicorn API (4 workers) - Fix #1
cd "c:\AI Automation\Automation Orchestrator"
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.automation_orchestrator.wsgi:app

# Terminal 2: Redis Server
wsl
redis-server

# Terminal 3: Task Worker 1 - Fix #3
python task_worker.py --queue default --worker-id worker-1

# Terminal 4: Task Worker 2 (parallel processing)
python task_worker.py --queue default --worker-id worker-2

# Terminal 5: Run stress test
python -m locust -f locustfile_final.py --headless -c 50 -r 5 -t 10m

# Expected Result: 100% pass rate with <1s average response time ✅
```

## References

- [Redis Documentation](https://redis.io/docs/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Gunicorn Documentation](https://gunicorn.org/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
