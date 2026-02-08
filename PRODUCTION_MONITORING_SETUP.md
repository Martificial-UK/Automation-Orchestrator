# Production Monitoring Setup Guide

Complete guide to implementing monitoring, logging, and alerting for your Automation Orchestrator production deployment.

---

## Table of Contents

1. [Monitoring Architecture](#monitoring-architecture)
2. [Application Logging](#application-logging)
3. [System Health Monitoring](#system-health-monitoring)
4. [Performance Metrics](#performance-metrics)
5. [Error Tracking & Alerting](#error-tracking--alerting)
6. [Log Aggregation](#log-aggregation)
7. [Dashboards & Visualization](#dashboards--visualization)
8. [Alerting Configuration](#alerting-configuration)
9. [Troubleshooting](#troubleshooting)

---

## Monitoring Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│         Automation Orchestrator Application             │
│  (FastAPI + React Dashboard + Workflow Engine)          │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
 LOGGING                  METRICS
 System events          Performance data
    │                         │
    ├─► Application Logs  ◄──┤
    │   (JSON formatted)      │
    │                         │
    └────────┬────────────────┘
             │
   ┌─────────┴──────────┐
   │                    │
   ▼                    ▼
STORAGE              MONITORING
Log files        Prometheus/StatsD
  .log           Health checks

```

### What to Monitor

**Essential Metrics:**
- Request rate and latency
- Error rates and types
- Resource usage (CPU, memory, disk)
- Database connection pool status
- Queue depth and processing time
- Workflow execution success rates
- API response times

---

## Application Logging

### Log Levels Explained

The system uses standard logging levels:

| Level | Severity | Usage |
|-------|----------|-------|
| **DEBUG** | Low | Development, detailed diagnostics |
| **INFO** | Low | Normal operations, workflow events |
| **WARNING** | Medium | Degraded performance, retries |
| **ERROR** | High | Failed operations, exceptions |
| **CRITICAL** | Critical | System failures, crashes |

### Log Format

All logs are structured JSON for parsing:

```json
{
  "timestamp": "2026-02-05T14:30:45.123Z",
  "level": "INFO",
  "logger": "automation_orchestrator.workflows",
  "message": "Workflow executed successfully",
  "workflow_id": "workflow_123",
  "execution_time_ms": 245,
  "status": "success",
  "request_id": "req_abc123"
}
```

### Log Output Locations

#### Development Mode
```
logs/
├── application.log         # All logs
├── error.log              # ERROR and CRITICAL only
└── debug.log              # DEBUG level details
```

#### Production Mode
```
/var/log/automation-orchestrator/
├── app.log                # Application logs
├── error.log              # Error tracking
├── access.log             # HTTP requests
└── workflow.log           # Workflow-specific events
```

### Configuring Logging

Edit `config/logging_config.json`:

```json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "json": {
      "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
      "format": "%(timestamp)s %(level)s %(logger)s %(message)s"
    },
    "standard": {
      "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "json",
      "level": "INFO"
    },
    "file": {
      "class": "logging.handlers.RotatingFileHandler",
      "filename": "logs/application.log",
      "maxBytes": 10485760,
      "backupCount": 5,
      "formatter": "json",
      "level": "DEBUG"
    },
    "error_file": {
      "class": "logging.handlers.RotatingFileHandler",
      "filename": "logs/error.log",
      "maxBytes": 10485760,
      "backupCount": 3,
      "formatter": "json",
      "level": "ERROR"
    }
  },
  "root": {
    "level": "INFO",
    "handlers": ["console", "file", "error_file"]
  }
}
```

---

## System Health Monitoring

### Health Check Endpoint

The system provides a health check endpoint:

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-05T14:30:45Z",
  "uptime_seconds": 3600,
  "metrics": {
    "requests_total": 1250,
    "success_rate": 0.9858,
    "queue_depth": 12,
    "avg_response_time_ms": 145
  },
  "database": {
    "status": "connected",
    "response_time_ms": 2
  },
  "storage": {
    "status": "healthy",
    "available_gb": 45.2
  }
}
```

### Monitoring Health Check

**Recommended:** Check health endpoint every 60 seconds

```bash
# Simple monitoring script
while true; do
  response=$(curl -s http://localhost:8000/health | jq .status)
  if [ "$response" != '"healthy"' ]; then
    echo "ALERT: System unhealthy at $(date)"
    # Send alert (email, Slack, PagerDuty, etc.)
  fi
  sleep 60
done
```

### Health Status Indicators

**Healthy** ✅
- Status: "healthy"
- Success rate: > 95%
- Response time: < 200ms
- Queue depth: < 100

**Degraded** ⚠️
- Status: "degraded"
- Success rate: 80-95%
- Response time: 200-500ms
- Queue depth: 100-500

**Unhealthy** ❌
- Status: "unhealthy"
- Success rate: < 80%
- Response time: > 500ms or no response
- Queue depth: > 500 or growing

---

## Performance Metrics

### Key Performance Indicators (KPIs)

Track these metrics monthly:

```
Response Time (ms):
  - Target: < 200ms average
  - Monitor: 95th percentile
  - Alert: > 500ms sustained

Success Rate (%):
  - Target: > 98%
  - Alert: < 95%
  - Critical: < 80%

Error Rate (%):
  - Target: < 2%
  - Monitor types: Timeouts, retries, failures

Uptime (%):
  - Target: > 99.5% (99.9% enterprise)
  - Track: Planned + unplanned downtime

Queue Processing:
  - Target: 100% tasks complete within 5 minutes
  - Alert: > 100 pending tasks
  - Critical: Queue not processing
```

### Extracting Metrics

Access metrics endpoint:

```bash
curl http://localhost:8000/api/metrics
```

Output includes:
- Total API calls
- Endpoint-specific statistics
- Error breakdown by type
- Response time percentiles
- Workflow execution stats

### Metric Storage

Store metrics for trending:

```
metrics/
├── 2026-02-05.json       # Daily metrics
├── 2026-02-04.json
└── monthly/
    └── 2026-02.json      # Monthly aggregates
```

---

## Error Tracking & Alerting

### Error Categories

**Track by type:**

1. **User Errors** (4xx HTTP codes)
   - Malformed requests
   - Authentication failures
   - Rate limiting
   - Expected, non-concerning

2. **Server Errors** (5xx HTTP codes)
   - Database failures
   - Timeout errors
   - Crashes
   - **Urgent to fix**

3. **Workflow Errors**
   - Invalid trigger configuration
   - Failed action execution
   - Missing data
   - **Monitor for patterns**

### Error Rate Thresholds

Set alerts for these conditions:

| Error Type | Threshold | Severity |
|---|---|---|
| 5xx errors | > 1% of requests | HIGH |
| Workflow failures | > 5% of executions | MEDIUM |
| Timeout errors | > 10/minute | MEDIUM |
| Authentication failures | > 100/minute | HIGH |
| Database connection failures | Any | CRITICAL |

---

## Log Aggregation

### ELK Stack Setup (Optional but Recommended)

For production with multiple servers:

```yaml
# docker-compose-monitoring.yml
version: '3'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.0.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5000:5000"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.0.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

### Simple Log Aggregation (Single Server)

```python
# scripts/aggregate_logs.py
import json
from datetime import datetime, timedelta
import os

def aggregate_daily_logs(log_dir='logs'):
    """Aggregate logs for daily summary"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    stats = {
        'date': today,
        'total_requests': 0,
        'errors': 0,
        'warnings': 0,
        'success_rate': 0.0,
        'avg_response_time': 0,
        'top_errors': {}
    }
    
    # Process all log files
    for filename in os.listdir(log_dir):
        with open(os.path.join(log_dir, filename), 'r') as f:
            for line in f:
                try:
                    log = json.loads(line)
                    stats['total_requests'] += 1
                    
                    if log.get('level') == 'ERROR':
                        stats['errors'] += 1
                        error_type = log.get('error_type', 'unknown')
                        stats['top_errors'][error_type] = \
                            stats['top_errors'].get(error_type, 0) + 1
                    
                    elif log.get('level') == 'WARNING':
                        stats['warnings'] += 1
                        
                except json.JSONDecodeError:
                    continue
    
    # Save summary
    summary_file = f"logs/daily_summary_{today}.json"
    with open(summary_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    return stats

if __name__ == '__main__':
    summary = aggregate_daily_logs()
    print(f"Daily Summary: {summary['total_requests']} requests, "
          f"{summary['errors']} errors")
```

---

## Dashboards & Visualization

### Basic Monitoring Dashboard

Create a simple HTML dashboard for key metrics:

```html
<!-- monitoring-dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Monitoring Dashboard</title>
    <style>
        body { font-family: Arial; background: #f5f5f5; }
        .metric { 
            background: white; 
            padding: 20px; 
            margin: 10px; 
            border-radius: 5px;
            display: inline-block;
            min-width: 200px;
        }
        .healthy { border-left: 5px solid green; }
        .degraded { border-left: 5px solid orange; }
        .unhealthy { border-left: 5px solid red; }
        .value { font-size: 32px; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Production Monitoring</h1>
    <div id="metrics"></div>
    
    <script>
        async function updateMetrics() {
            const response = await fetch('/health');
            const data = await response.json();
            
            document.getElementById('metrics').innerHTML = `
                <div class="metric ${data.status === 'healthy' ? 'healthy' : 'unhealthy'}">
                    <div>Status</div>
                    <div class="value">${data.status}</div>
                </div>
                <div class="metric">
                    <div>Uptime</div>
                    <div class="value">${(data.uptime_seconds / 3600).toFixed(1)}h</div>
                </div>
                <div class="metric">
                    <div>Success Rate</div>
                    <div class="value">${(data.metrics.success_rate * 100).toFixed(1)}%</div>
                </div>
                <div class="metric">
                    <div>Queue Depth</div>
                    <div class="value">${data.metrics.queue_depth}</div>
                </div>
            `;
        }
        
        updateMetrics();
        setInterval(updateMetrics, 30000); // Update every 30 seconds
    </script>
</body>
</html>
```

---

## Alerting Configuration

### Alert Channels

Configure notifications for different severity levels:

#### Email Alerts (High Priority)

```python
# config/alerts.json
{
  "email_alerts": {
    "recipient": "ops-team@example.com",
    "enabled": true,
    "triggers": [
      "system_unhealthy",
      "error_rate_high",
      "database_disconnected",
      "storage_critical"
    ]
  }
}
```

#### Slack Alerts (Real-time)

```python
# src/monitoring/slack_alerts.py
import requests

class SlackAlerter:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def alert(self, severity, message):
        color_map = {
            'critical': '#FF0000',
            'warning': '#FFA500',
            'info': '#0000FF'
        }
        
        payload = {
            'attachments': [{
                'color': color_map[severity],
                'title': f'{severity.upper()} Alert',
                'text': message,
                'ts': int(time.time())
            }]
        }
        
        requests.post(self.webhook_url, json=payload)
```

#### PagerDuty Integration (Critical)

```python
# src/monitoring/pagerduty_alerts.py
import requests

class PagerDutyAlerter:
    def __init__(self, api_key, service_id):
        self.api_key = api_key
        self.service_id = service_id
    
    def trigger_incident(self, title, description):
        headers = {
            'Authorization': f'Token token={self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'incident': {
                'type': 'incident',
                'title': title,
                'service': {'id': self.service_id, 'type': 'service_reference'},
                'body': {'type': 'incident_body', 'details': description}
            }
        }
        
        response = requests.post(
            'https://api.pagerduty.com/incidents',
            headers=headers,
            json=payload
        )
        return response.json()
```

### Response Time SLA

Define expected resolution times:

| Severity | Response Time | Resolution Time |
|----------|---|---|
| **Critical** | 5 minutes | 1 hour |
| **High** | 15 minutes | 4 hours |
| **Medium** | 1 hour | 8 hours |
| **Low** | Next business day | 48 hours |

---

## Troubleshooting

### Problem: High Error Rate

**Symptoms**: Error count exceeds thresholds

**Investigation Steps**:
1. Check error logs: `tail -f logs/error.log | jq`
2. Group by error type: `grep ERROR logs/error.log | jq .error_type | sort | uniq -c`
3. Check most recent error: `tail -1 logs/error.log | jq`
4. Restart service if cascading failures

---

### Problem: Queue Not Processing

**Symptoms**: Queue depth continuously growing

**Investigation Steps**:
1. Check Redis/queue service status: `redis-cli ping`
2. Check queue worker logs: `logs/worker.log`
3. Verify network connectivity
4. Restart queue worker service

---

### Problem: High Response Time

**Symptoms**: Latency exceeds thresholds

**Investigation Steps**:
1. Check CPU/memory usage
2. Query slow logs: `logs/slow_queries.log`
3. Check database connection pool
4. Look for long-running workflows
5. Scale horizontally or optimize queries

---

### Problem: Memory Leak

**Symptoms**: Memory usage constantly increasing

**Investigation Steps**:
1. Monitor process memory: `ps aux | grep python`
2. Enable Python memory profiling
3. Check for unclosed file handles
4. Review logs for retry loops
5. Schedule periodic restarts if necessary

---

## Monitoring Checklist

### Daily Tasks
- [ ] Review health endpoint (up/down)
- [ ] Check error logs for critical issues
- [ ] Verify queue is processing
- [ ] Monitor system resources

### Weekly Tasks
- [ ] Review performance metrics
- [ ] Analyze error trends
- [ ] Check log file sizes (rotate if needed)
- [ ] Verify backups completed

### Monthly Tasks
- [ ] Generate performance report
- [ ] Review SLA compliance
- [ ] Update alert thresholds if needed
- [ ] Plan capacity for next quarter
- [ ] Security audit of access logs

---

## Resources

- **Log Files**: `logs/` directory
- **Health Check**: `http://localhost:8000/health`
- **Metrics**: `http://localhost:8000/api/metrics`
- **Configuration**: `config/logging_config.json`

---

**Last Updated**: February 2026  
**Version**: 1.0.0
