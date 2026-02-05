# Monitoring & Alerting Configuration Guide

## Table of Contents
1. [Overview](#overview)
2. [Prometheus Configuration](#prometheus-configuration)
3. [Alert Rules](#alert-rules)
4. [Grafana Dashboards](#grafana-dashboards)
5. [External Monitoring](#external-monitoring)
6. [Health Endpoints](#health-endpoints)
7. [Log Aggregation](#log-aggregation)

---

## Overview

Comprehensive monitoring setup with:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notifications
- **Loki**: Log aggregation
- **Node Exporter**: System metrics

---

## Prometheus Configuration

### prometheus.yml Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'automation-orchestrator'
    environment: 'production'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - 'alerts.yml'
  - 'recording_rules.yml'

scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # API Service
  - job_name: 'automation-orchestrator'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    relabel_configs:
      - source_labels: [__scheme__]
        target_label: __scheme__
        replacement: http

  # PostgreSQL Exporter
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis Exporter
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Node Exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
```

---

## Alert Rules

### alerts.yml

```yaml
groups:
  - name: automation-orchestrator
    interval: 30s
    rules:
      # API Service Alerts
      - alert: APIDown
        expr: up{job="automation-orchestrator"} == 0
        for: 1m
        labels:
          severity: critical
          component: api
        annotations:
          summary: "API service is down"
          description: "API has been unreachable for more than 1 minute"

      - alert: HighErrorRate
        expr: |
          (sum(rate(http_requests_total{job="automation-orchestrator", status=~"5.."}[5m])) by (job)) 
          / 
          (sum(rate(http_requests_total{job="automation-orchestrator"}[5m])) by (job))
          > 0.05
        for: 5m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "High error rate detected (> 5%)"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.95, 
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 1
        for: 5m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "Slow response times (p95 > 1s)"
          description: "95th percentile response time is {{ $value }}s"

      - alert: HighMemoryUsage
        expr: |
          (container_memory_usage_bytes{name="automation-orchestrator-api"} / 
           container_spec_memory_limit_bytes{name="automation-orchestrator-api"}) > 0.85
        for: 5m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "High memory usage (> 85%)"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      - alert: HighCPUUsage
        expr: |
          rate(container_cpu_usage_seconds_total{name="automation-orchestrator-api"}[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "High CPU usage (> 80%)"
          description: "CPU usage is {{ $value | humanizePercentage }}"

      # Database Alerts
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
          component: database
        annotations:
          summary: "PostgreSQL is down"
          description: "Database has been unreachable for more than 1 minute"

      - alert: HighDatabaseConnections
        expr: |
          pg_stat_activity_count{job="postgres"} / 
          pg_settings_max_connections{job="postgres"} > 0.9
        for: 5m
        labels:
          severity: warning
          component: database
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "{{ $value | humanizePercentage }} of connections in use"

      - alert: HighDatabaseDiskUsage
        expr: |
          (pg_database_size_bytes{job="postgres"} / 
           node_filesystem_size_bytes{device="/dev/sda1"}) > 0.85
        for: 10m
        labels:
          severity: warning
          component: database
        annotations:
          summary: "Database disk usage high (> 85%)"
          description: "Database disk usage is {{ $value | humanizePercentage }}"

      - alert: SlowDatabaseQueries
        expr: |
          pg_stat_statements_mean_time_seconds{job="postgres"} > 1
        for: 5m
        labels:
          severity: warning
          component: database
        annotations:
          summary: "Slow database queries detected"
          description: "Mean query time is {{ $value }}s"

      # Redis Alerts
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
          component: redis
        annotations:
          summary: "Redis is down"
          description: "Redis has been unreachable for more than 1 minute"

      - alert: RedisHighMemory
        expr: |
          (redis_memory_used_bytes{job="redis"} / 
           redis_memory_max_bytes{job="redis"}) > 0.9
        for: 5m
        labels:
          severity: warning
          component: redis
        annotations:
          summary: "Redis memory usage high (> 90%)"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      # System Alerts
      - alert: NodeDown
        expr: up{job="node"} == 0
        for: 1m
        labels:
          severity: critical
          component: system
        annotations:
          summary: "Node is down"
          description: "Node has been unreachable for more than 1 minute"

      - alert: HighDiskUsage
        expr: |
          (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) > 0.85
        for: 10m
        labels:
          severity: warning
          component: system
        annotations:
          summary: "High disk usage (> 85%)"
          description: "Disk usage is {{ $value | humanizePercentage }}"

      - alert: HighLoadAverage
        expr: |
          node_load15 / count(node_cpu_seconds_total{mode="idle"}) > 2
        for: 5m
        labels:
          severity: warning
          component: system
        annotations:
          summary: "High load average"
          description: "Load average is {{ $value }}"
```

### recording_rules.yml

```yaml
groups:
  - name: automation-orchestrator-recording
    interval: 15s
    rules:
      # Request rate
      - record: 'api:request_rate:1m'
        expr: 'sum(rate(http_requests_total[1m])) by (method, endpoint, status)'

      - record: 'api:error_rate:1m'
        expr: 'sum(rate(http_requests_total{status=~"5.."}[1m])) by (endpoint)'

      # Response time
      - record: 'api:response_time_p50:1m'
        expr: 'histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))'

      - record: 'api:response_time_p95:1m'
        expr: 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))'

      # Database performance
      - record: 'db:query_rate:1m'
        expr: 'sum(rate(pg_stat_statements_calls_total[1m])) by (query)'

      - record: 'db:slow_queries:1m'
        expr: 'count(count(pg_stat_statements_mean_time_seconds > 1) by (query))'
```

---

## Grafana Dashboards

### Dashboard 1: API Overview

```json
{
  "dashboard": {
    "title": "Automation Orchestrator - API Overview",
    "panels": [
      {
        "title": "Requests Per Second",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[1m]))"
          }
        ]
      },
      {
        "title": "Error Rate (%)",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[1m])) / sum(rate(http_requests_total[1m])) * 100"
          }
        ]
      },
      {
        "title": "Response Time (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
          }
        ]
      },
      {
        "title": "Active Requests",
        "targets": [
          {
            "expr": "sum(http_requests_in_progress)"
          }
        ]
      }
    ]
  }
}
```

### Dashboard 2: Database Performance

```json
{
  "dashboard": {
    "title": "Automation Orchestrator - Database",
    "panels": [
      {
        "title": "Database Connections",
        "targets": [
          {
            "expr": "pg_stat_activity_count / pg_settings_max_connections"
          }
        ]
      },
      {
        "title": "Query Duration (p95)",
        "targets": [
          {
            "expr": "pg_stat_statements_mean_time_seconds"
          }
        ]
      },
      {
        "title": "Cache Hit Ratio",
        "targets": [
          {
            "expr": "pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)"
          }
        ]
      },
      {
        "title": "Database Size",
        "targets": [
          {
            "expr": "pg_database_size_bytes / 1024 / 1024 / 1024"
          }
        ]
      }
    ]
  }
}
```

---

## External Monitoring

### Sentry Integration (Error Tracking)

```python
# In main application
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT")
)
```

### New Relic Integration (APM)

```python
# Run with New Relic agent
# newrelic-admin run-program python -m uvicorn main:app

# Or programmatically
import newrelic.agent
newrelic.agent.initialize(os.getenv("NEW_RELIC_CONFIG_FILE"))
```

### DataDog Integration

```python
# Using datadog-api-client
from datadog_api_client import ApiClient, Configuration

configuration = Configuration()
configuration.api_key["apiKeyAuth"] = os.getenv("DATADOG_API_KEY")

with ApiClient(configuration) as api_client:
    api_instance = MetricsApi(api_client)
    # Send custom metrics
```

---

## Health Endpoints

### API Health Check

```python
# In api.py
from datetime import datetime
import psutil

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health/detailed")
async def health_detailed(db: Session = Depends(get_db)):
    """Detailed health check including dependencies"""
    try:
        # Check database
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    try:
        # Check Redis
        redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        "database": db_status,
        "redis": redis_status,
        "uptime": get_uptime(),
        "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024,
        "cpu_usage": psutil.Process().cpu_percent(interval=1)
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")
```

---

## Log Aggregation

### Loki Configuration (logs/loki-config.yml)

```yaml
auth_enabled: false

ingester:
  chunk_idle_period: 3m
  chunk_retain_period: 1m
  max_chunk_age: 1h
  max_streams_per_user: 10000

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema:
        version: v11
        index:
          prefix: index_
          period: 24h

server:
  http_listen_port: 3100

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```

### Promtail Configuration (logs/promtail-config.yml)

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Docker containers
  - job_name: docker
    static_configs:
      - targets:
          - localhost
        labels:
          job: docker
          __path__: /var/lib/docker/containers/*/*-json.log
    pipeline_stages:
      - json:
          expressions:
            output: log
            stream: stream
      - output:
          source: output
      - labels:
          stream:

  # Application logs
  - job_name: application
    static_configs:
      - targets:
          - localhost
        labels:
          job: automation-orchestrator
          __path__: /app/logs/*.log
```

### Log Query Examples

```promql
# Recent errors
{job="automation-orchestrator"} | json | status="500"

# Request latency
{job="automation-orchestrator"} | json | duration > 1000

# Authentication failures
{job="automation-orchestrator"} | json | message="auth_failed"

# Database query slow
{job="automation-orchestrator"} | json | db_duration > 5000
```

---

## Alert Notification Channels

### AlertManager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'
        description: '{{ .GroupLabels.alertname }}'

  - name: 'email'
    email_configs:
      - to: 'ops-team@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.example.com:587'
```

---

## Maintenance & Best Practices

### Retention Policies

```yaml
retention:
  # Keep metrics for 30 days
  prometheus_retention: 30d
  
  # Keep logs for 7 days
  loki_retention: 7d
  
  # Keep traces for 3 days
  jaeger_retention: 3d
```

### Regular Tasks

- Review dashboards weekly
- Audit alert rules monthly
- Clean up old data quarterly
- Update thresholds based on baselines
- Test alert notifications monthly

For more details, see PRODUCTION_DEPLOYMENT_GUIDE.md
