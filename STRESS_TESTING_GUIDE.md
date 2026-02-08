# Local Stress Testing Guide for Automation Orchestrator

## Quick Start (< 5 minutes)

### 1. Prerequisites
```bash
# Install Locust (if not already installed)
pip install locust

# Verify installation
locust --version
```

### 2. Start API Services
```bash
cd c:\AI Automation\Automation Orchestrator

# Start all services (API, DB, Redis, Prometheus, Grafana)
docker-compose up -d

# Wait 10 seconds for services to start
# Verify API is running
curl http://localhost:8000/health
```

### 3. Run Stress Test
```bash
# Windows PowerShell
.\run_stress_test.ps1

# macOS/Linux
bash run_stress_test.sh

# Or run directly with custom parameters
locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 10 --run-time 10m --headless
```

## Test Scenarios

### 🟢 Light Load (Baseline)
```bash
# 10 concurrent users, 2 minute duration
locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 5 --run-time 2m --headless

# Expected: Response time < 100ms, Error rate 0%
```

### 🟡 Medium Load (Normal)
```bash
# 50 concurrent users, 10 minute duration
locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 10 --run-time 10m --headless

# Expected: Response time < 200ms, Error rate < 0.1%
```

### 🔴 Heavy Load (Stress)
```bash
# 200 concurrent users, 15 minute duration
locust -f locustfile.py --host http://localhost:8000 --users 200 --spawn-rate 20 --run-time 15m --headless

# Expected: Response time < 500ms, Error rate < 1%
```

### 🟣 Peak Load (Breaking Point)
```bash
# 500 concurrent users, 5 minute duration
locust -f locustfile.py --host http://localhost:8000 --users 500 --spawn-rate 50 --run-time 5m --headless

# Goal: Find system breaking point
```

### 💜 Spike Test (Sudden Traffic Increase)
```bash
# Sudden increase from 10 to 200 users
# This tests auto-scaling and error recovery
locust -f locustfile.py --host http://localhost:8000 --users 200 --spawn-rate 100 --run-time 5m --headless
```

## Monitoring During Test

### Option 1: Web UI (Recommended for first time)
```bash
# Run with web UI enabled on http://localhost:8089
locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 10

# Open browser: http://localhost:8089
# Monitor in real-time
```

### Option 2: Grafana Dashboard
While test is running:
1. Open: http://localhost:3000
2. Login: admin / admin
3. Select "API Overview" dashboard
4. Monitor:
   - Requests/sec
   - Response times (p50, p95, p99)
   - Error rate
   - Memory usage

### Option 3: Prometheus Metrics
```bash
# While test running, in another terminal:
curl http://localhost:8000/metrics | grep http_

# Key metrics:
# - http_requests_total
# - http_request_duration_seconds_bucket
# - http_requests_in_progress
```

### Option 4: Docker Stats
```bash
# In another terminal, monitor container resources:
docker stats automation-orchestrator-api

# Check:
# - CPU usage (should be < 80%)
# - Memory usage (should be < 85%)
# - Network I/O
```

## Understanding Test Results

### Response Time Analysis
```
Metric          Target    Details
─────────────────────────────────────
Average (Mean)  < 200ms   Normal request time
P50             < 100ms   50% of requests
P95             < 500ms   95% of requests (important!)
P99             < 1000ms  99% of requests
Min             varies    Fastest response
Max             < 5000ms  Slowest response
```

### Error Rate Analysis
```
Rate            Status      Action
────────────────────────────────────
0%              ✅ Perfect  All good
< 0.1%          ✅ Good     Acceptable
0.1-1%          ⚠️  Warning Monitor closely
> 1%            ❌ Bad      Needs investigation
```

### Resource Utilization
```
Resource        Low      Medium    High      Critical
───────────────────────────────────────────────────
CPU             < 30%    30-60%    60-80%   > 80%
Memory          < 40%    40-65%    65-85%   > 85%
Connections     < 40%    40-70%    70-90%   > 90%
Disk I/O        < 30%    30-60%    60-80%   > 80%
```

## Traffic Distribution

The stress test simulates realistic user behavior with this traffic mix:

```
Operation                    % of Traffic   Rationale
─────────────────────────────────────────────────────
GET /health                      5%         Health monitoring
GET /health/detailed             2%         Detailed checks
GET /metrics                     1%         Monitoring scraping
GET /api/auth/me                 3%         Session validation
GET /api/auth/keys               1%         Key listing
GET /api/workflows              10%         Most common operation
GET /api/workflows/:id/status    5%         Status checks
POST /api/workflows              3%         New workflows
PUT /api/workflows/:id           2%         Workflow updates
POST /api/workflows/:id/execute  4%         Workflow execution
GET /api/leads                   8%         Lead retrieval
POST /api/leads                  3%         New leads
GET /api/leads/:id               2%         Lead details
GET /api/campaigns               6%         Campaign listing
GET /api/campaigns/:id/metrics   2%         Campaign metrics
GET /api/nonexistent             1%         Error handling test
GET /docs                        2%         Documentation
GET /openapi.json                1%         Schema requests
```

## Test Results Interpretation

### ✅ Healthy Results
- Response time p95 < 200ms
- Error rate < 0.1%
- CPU consistently < 70%
- Memory stable (no growth)
- Database connections < 80% of pool
- No timeouts or connection errors

### ⚠️ Warning Signs
- Response time p95 > 500ms
- Error rate increasing
- Memory gradually increasing
- CPU stays > 80%
- Database connection pool filling
- Intermittent errors

### ❌ Critical Issues
- Rapid response time degradation
- Error rate > 5%
- Memory not releasing (memory leak)
- CPU maxed out consistently
- Database connection pool exhausted
- API becoming unresponsive

## Advanced Testing

### Custom Load Pattern
Create `custom_locustfile.py` for your specific needs:
```python
from locust import HttpUser, task, between

class CustomUser(HttpUser):
    wait_time = between(1, 2)
    
    @task
    def my_custom_endpoint(self):
        self.client.get("/api/custom-endpoint")

# Run: locust -f custom_locustfile.py --host http://localhost:8000
```

### Distributed Testing (Multiple Machines)
```bash
# Master node
locust -f locustfile.py --master --host http://localhost:8000

# Worker node (run on different machines)
locust -f locustfile.py --worker --master-host=<master-ip> --host http://localhost:8000

# Can combine multiple workers for massive load
```

### Ramp-up Test (Gradual Load Increase)
The built-in spawn-rate implements this:
```bash
# Will gradually increase from 0 to 200 users over 20 seconds
locust -f locustfile.py --users 200 --spawn-rate 10 --run-time 10m
```

### Soak Test (Extended Low Load)
```bash
# Run with sustained 50 users for 1 hour
# Detects memory leaks and performance degradation
locust -f locustfile.py --users 50 --spawn-rate 10 --run-time 1h --headless
```

## Troubleshooting

### Issue: "API not responding"
```bash
# Check if Docker containers are running
docker-compose ps

# Check API logs
docker-compose logs api

# Restart services
docker-compose restart api
```

### Issue: "Locust not found"
```bash
# Install Locust
pip install locust

# Verify
locust --version
```

### Issue: "Connection refused"
```bash
# Make sure you're using correct host:port
# Default: http://localhost:8000

# Test connectivity
curl http://localhost:8000/health

# Check firewall
# Default port 8000 should be open
```

### Issue: "High error rate"
```bash
# Check API logs
docker-compose logs api -f

# Check database connectivity
docker-compose logs db

# Verify credentials in API health check
curl http://localhost:8000/health/detailed
```

### Issue: "Memory keeps growing"
```bash
# Could indicate memory leak
# Restart containers
docker-compose restart

# Use soak test to identify:
# locust -f locustfile.py --users 20 --spawn-rate 5 --run-time 1h

# Monitor memory with Docker stats
docker stats automation-orchestrator-api
```

## Performance Benchmarks

### Baseline Targets (adjust based on your requirements)

| Metric | Target | Achieved |
|--------|--------|----------|
| **Response Time (p95)** | < 200ms | ____ |
| **Error Rate** | < 0.1% | ____ |
| **Throughput** | > 1000 req/s | ____ |
| **CPU Usage** | < 70% | ____ |
| **Memory Usage** | < 80% | ____ |
| **Database Conn Pool** | < 80% utilized | ____ |
| **99th Percentile** | < 1000ms | ____ |
| **Max Response Time** | < 5000ms | ____ |

_Fill in achieved values during your tests for comparison._

## Next Steps After Testing

1. **Document Results**
   - Save Grafana dashboard screenshots
   - Export test results from Locust
   - Record baseline metrics

2. **Analyze Bottlenecks**
   - Identify slow endpoints
   - Check database query performance
   - Review error logs

3. **Optimize**
   - Add caching where appropriate
   - Optimize database queries
   - Increase resource limits if needed
   - Enable auto-scaling

4. **Repeat Testing**
   - Retest after optimizations
   - Compare new results with baseline
   - Document improvements

## Resources

- **Locust Documentation**: https://docs.locust.io/
- **Your API Docs**: http://localhost:8000/docs
- **Grafana Dashboards**: http://localhost:3000
- **Prometheus**: http://localhost:9090

## Example Commands Quick Reference

```bash
# Light load (baseline)
locust -f locustfile.py --host http://localhost:8000 --users 10 --run-time 2m --headless

# Medium load (normal)
locust -f locustfile.py --host http://localhost:8000 --users 50 --run-time 10m --headless

# Heavy load (stress)
locust -f locustfile.py --host http://localhost:8000 --users 200 --run-time 15m --headless

# Web UI monitoring
locust -f locustfile.py --host http://localhost:8000 --users 50 --run-time 10m

# Soak test (find issues)
locust -f locustfile.py --host http://localhost:8000 --users 20 --run-time 1h --headless

# Spike test
locust -f locustfile.py --host http://localhost:8000 --users 500 --spawn-rate 100 --run-time 5m --headless
```

Good luck with testing! 🚀
