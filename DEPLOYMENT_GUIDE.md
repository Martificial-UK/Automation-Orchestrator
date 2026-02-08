# Production Deployment Guide

**Audit System v3.0 - Performance Optimized**  
**Target Environment**: Production  
**Last Updated**: February 4, 2026

---

## Prerequisites Checklist

### System Requirements
- [ ] Python 3.8+ installed
- [ ] 500MB+ free disk space
- [ ] Write permissions to logs directory
- [ ] Network access for webhooks (if used)

### Dependencies
```bash
pip install requests loguru jsonschema

# Optional cloud storage
pip install boto3  # AWS S3
pip install azure-storage-blob  # Azure
pip install google-cloud-storage  # GCS
```

---

## Pre-Deployment Validation

### Step 1: Run Configuration Validator

```bash
cd 'c:\AI Automation\Automation Orchestrator'
python validate_config.py
```

**Expected Output**:
```
✅ VALIDATION PASSED - Configuration is ready for production
```

**If validation fails**:
1. Review error messages
2. Fix configuration constants in `src/automation_orchestrator/audit.py`
3. Re-run validation

### Step 2: Run Performance Tests

```bash
python test_audit_performance.py
```

**Expected Results**:
- Throughput: >500 events/sec
- Query cache: >5x speedup
- Compression: >2x ratio
- Overall grade: A or better

### Step 3: Run Integration Tests

```bash
python test_audit_integration.py
```

**Expected Output**:
```
Results: 6/6 tests passed
✓ ALL TESTS PASSED!
```

---

## Configuration Tuning

### Production Configuration (Recommended)

Edit [src/automation_orchestrator/audit.py](src/automation_orchestrator/audit.py) lines 38-44:

```python
# Performance constants
WRITE_BUFFER_SIZE = 100       # Events per batch
WRITE_FLUSH_INTERVAL = 5.0    # Flush every 5 seconds
QUERY_CACHE_SIZE = 128        # Cache 128 queries
COMPRESSION_LEVEL = 6         # Balanced compression
MAX_MEMORY_EVENTS = 10000     # Memory limit

# Security constants
MAX_DETAILS_SIZE = 50 * 1024  # 50KB per event
RATE_LIMIT_REQUESTS = 100     # Events per second
RATE_LIMIT_BURST = 200        # Burst capacity
```

### Environment-Specific Tuning

**High-Traffic (>1000 events/sec)**:
```python
WRITE_BUFFER_SIZE = 500
WRITE_FLUSH_INTERVAL = 10.0
QUERY_CACHE_SIZE = 256
COMPRESSION_LEVEL = 4  # Faster
```

**Low-Latency (<100ms)**:
```python
WRITE_BUFFER_SIZE = 50
WRITE_FLUSH_INTERVAL = 1.0
QUERY_CACHE_SIZE = 64
COMPRESSION_LEVEL = 6
```

**Storage-Optimized**:
```python
WRITE_BUFFER_SIZE = 100
WRITE_FLUSH_INTERVAL = 5.0
QUERY_CACHE_SIZE = 128
COMPRESSION_LEVEL = 9  # Maximum
```

---

## Deployment Steps

### 1. Directory Setup

```powershell
# Create required directories
New-Item -ItemType Directory -Force -Path "logs"
New-Item -ItemType Directory -Force -Path "backups/audit"

# Set permissions (Windows)
icacls "logs" /grant "Users:(OI)(CI)F"
```

### 2. Initial Configuration

```python
# In your main application file
from automation_orchestrator.audit import get_audit_logger
import atexit

# Initialize audit logger (singleton)
audit = get_audit_logger("logs/audit.log")

# Register graceful shutdown
atexit.register(audit.shutdown)

# Enable features as needed
audit.configure_rotation(
    max_size_mb=100,  # Rotate at 100MB
    retention_days=90  # Keep 90 days
)

# Optional: Configure alerts
audit.configure_alerts(
    email_config={
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "from_email": "alerts@yourdomain.com",
        "to_email": "admin@yourdomain.com",
        "username": "your-email@gmail.com",
        "password": "your-app-password"
    }
)

# Optional: Configure webhooks
audit.add_webhook("https://your-slack-webhook-url")
```

### 3. Start Application

```bash
# Start your application normally
python your_app.py

# The audit system will:
# - Start background worker thread automatically
# - Begin buffering events
# - Flush every 5 seconds or at 100 events
```

---

## Monitoring Setup

### Real-Time Dashboard

```bash
# Terminal monitoring
python monitor_audit.py --refresh 2

# Single snapshot
python monitor_audit.py --once

# Custom log file
python monitor_audit.py --log-file logs/custom.log
```

### Health Checks

```bash
# One-time health check
python health_check.py

# JSON output (for integrations)
python health_check.py --json

# Continuous monitoring
python health_check.py --watch 30  # Every 30 seconds

# Verbose mode
python health_check.py --verbose
```

**Integration with Monitoring Systems**:

```bash
# Nagios/Icinga
python health_check.py --json > /tmp/audit_health.json
# Exit code: 0=healthy, 1=warning, 2=critical

# Prometheus (add to exporter)
curl http://localhost:5000/health | jq .

# DataDog/New Relic
python health_check.py --json | \
  curl -X POST -H "Content-Type: application/json" \
  -d @- https://your-monitoring-endpoint
```

---

## Backup Strategy

### Automated Backups

#### Daily Backup Script

Create `backup_daily.ps1`:

```powershell
# Daily backup script
cd 'c:\AI Automation\Automation Orchestrator'

# Create backup
python backup_audit.py backup --cloud s3 --destination your-bucket-name

# Clean up old backups (keep last 30)
python backup_audit.py cleanup --keep 30

# Log result
Write-Host "Backup completed: $(Get-Date)"
```

**Schedule with Task Scheduler**:
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
  -Argument "-File 'C:\AI Automation\Automation Orchestrator\backup_daily.ps1'"

$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

Register-ScheduledTask -TaskName "AuditBackup" `
  -Action $action -Trigger $trigger
```

### Manual Backup

```bash
# Create local backup
python backup_audit.py backup

# Compress backup
python backup_audit.py backup --compress

# Upload to cloud
python backup_audit.py backup --cloud s3 --destination your-bucket

# List backups
python backup_audit.py list

# Restore from backup
python backup_audit.py restore backups/audit/audit_backup_20260204_120000.log.gz
```

### Cloud Storage Configuration

**AWS S3**:
```bash
# Set credentials
aws configure
# Or set environment variables
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

**Azure Blob**:
```bash
# Set connection string
export AZURE_STORAGE_CONNECTION_STRING="your-connection-string"
```

**Google Cloud Storage**:
```bash
# Authenticate
gcloud auth application-default login
```

---

## Troubleshooting

### Issue: High Buffer Size

**Symptoms**: `write_buffer.qsize()` > 500

**Diagnosis**:
```bash
python health_check.py --verbose
# Look for: write_buffer status=warning or critical
```

**Solutions**:
1. Increase flush frequency: Set `WRITE_FLUSH_INTERVAL = 2.0`
2. Increase batch size: Set `WRITE_BUFFER_SIZE = 200`
3. Check disk I/O: May be slow storage
4. Check worker thread: Ensure it's running

### Issue: Slow Queries

**Symptoms**: Query times >100ms

**Diagnosis**:
```python
from automation_orchestrator.audit import get_audit_logger
audit = get_audit_logger()

import time
start = time.time()
results = audit.query_events(event_type="test", limit=100)
print(f"Query time: {(time.time()-start)*1000:.1f}ms")
```

**Solutions**:
1. Increase cache size: Set `QUERY_CACHE_SIZE = 256`
2. Add indexes (future feature)
3. Use log rotation to keep files smaller
4. Use time-based queries to reduce scan

### Issue: Large Log Files

**Symptoms**: Log file >1GB

**Diagnosis**:
```bash
python health_check.py
# Look for: log_file status=warning (>1GB)
```

**Solutions**:
1. Trigger manual rotation:
   ```python
   audit._rotate_log()
   ```

2. Configure auto-rotation:
   ```python
   audit.configure_rotation(max_size_mb=100)
   ```

3. Check compressed logs:
   ```bash
   ls -lh logs/*.gz
   ```

### Issue: Security Events

**Symptoms**: Many validation_error or rate_limit_exceeded events

**Diagnosis**:
```bash
python health_check.py --verbose
# Check: security component
```

**Solutions**:
1. Review security log:
   ```bash
   cat logs/security_events.log
   ```

2. Identify attack sources:
   ```python
   events = audit.get_security_events(event_type="validation_error")
   sources = {}
   for e in events:
       source = e.get('details', {}).get('lead_id', 'unknown')
       sources[source] = sources.get(source, 0) + 1
   print(sorted(sources.items(), key=lambda x: x[1], reverse=True))
   ```

3. Adjust rate limits if legitimate:
   ```python
   # In audit.py
   RATE_LIMIT_REQUESTS = 200  # Increase limit
   ```

---

## Performance Monitoring

### Key Metrics to Track

1. **Event Rate**: Target 500-1500 events/sec
   ```bash
   python monitor_audit.py --once | grep "EVENT RATE"
   ```

2. **Buffer Size**: Target <100 events
   ```bash
   python health_check.py --json | jq '.checks[] | select(.component=="write_buffer")'
   ```

3. **Query Performance**: Target <50ms
   ```python
   # Add to your monitoring
   start = time.time()
   audit.query_events(event_type="lead_ingested", limit=100)
   latency = (time.time() - start) * 1000
   ```

4. **Disk Usage**: Track log file growth
   ```bash
   du -sh logs/
   du -sh backups/audit/
   ```

5. **Security Events**: Target <10/hour
   ```bash
   python -c "from automation_orchestrator.audit import get_audit_logger; \
              audit = get_audit_logger(); \
              events = audit.get_security_events(limit=100); \
              print(f'Security events: {len(events)}')"
   ```

### Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Buffer Size | >500 | >800 | Increase flush rate |
| Query Time | >100ms | >500ms | Increase cache size |
| Log Size | >1GB | >5GB | Trigger rotation |
| Security Events | >50/hr | >100/hr | Investigate source |
| Blocked Events | >100 | >500 | Review rate limits |

---

## Rollback Procedure

If issues occur in production:

### 1. Stop Application
```bash
# Stop gracefully to flush buffer
# Application should call audit.shutdown()
```

### 2. Restore Previous Backup
```bash
python backup_audit.py restore backups/audit/audit_backup_TIMESTAMP.log.gz \
  --target logs/audit.log.restored
```

### 3. Switch to Restored Log
```bash
# Backup current problematic log
mv logs/audit.log logs/audit.log.problem

# Use restored log
mv logs/audit.log.restored logs/audit.log
```

### 4. Restart Application
```bash
# Application will use restored log
python your_app.py
```

---

## Maintenance Schedule

### Daily
- [ ] Check health status: `python health_check.py`
- [ ] Review security events: `cat logs/security_events.log | tail -100`
- [ ] Monitor disk usage: `du -sh logs/`

### Weekly
- [ ] Run performance tests: `python test_audit_performance.py`
- [ ] Review buffer/cache metrics
- [ ] Check backup status: `python backup_audit.py list`

### Monthly
- [ ] Clean old backups: `python backup_audit.py cleanup --keep 30`
- [ ] Review log rotation policy
- [ ] Performance tuning based on metrics

### Quarterly
- [ ] Full validation: `python validate_config.py`
- [ ] Review and update alert thresholds
- [ ] Security audit: Review blocked events and patterns

---

## Security Hardening

### Production Mode

Set in `audit.py`:
```python
PRODUCTION_MODE = True  # Hides stack traces
```

### Rate Limiting

Tune based on expected load:
```python
RATE_LIMIT_REQUESTS = 100   # Per source per second
RATE_LIMIT_BURST = 200      # Burst capacity
```

### Access Control

**Log File Permissions** (Windows):
```powershell
icacls "logs\audit.log" /grant "SYSTEM:F" /grant "Administrators:F" /deny "Users:R"
```

**Log File Permissions** (Linux):
```bash
chmod 600 logs/audit.log
chown app-user:app-user logs/audit.log
```

### Network Security

If using webhooks, whitelist destinations:
```python
# In audit.py _validate_url()
ALLOWED_WEBHOOK_DOMAINS = [
    'hooks.slack.com',
    'discord.com',
    'your-internal-domain.com'
]
```

---

## Support & Escalation

### Diagnostic Information

When reporting issues, include:

```bash
# 1. System info
python --version
pip list | grep -E "requests|loguru|jsonschema"

# 2. Configuration
python -c "import automation_orchestrator.audit as a; \
           print(f'Buffer: {a.WRITE_BUFFER_SIZE}'); \
           print(f'Flush: {a.WRITE_FLUSH_INTERVAL}'); \
           print(f'Cache: {a.QUERY_CACHE_SIZE}')"

# 3. Health status
python health_check.py --json > health_report.json

# 4. Recent logs
tail -100 logs/audit.log > recent_events.log
tail -100 logs/security_events.log > recent_security.log

# 5. Performance snapshot
python test_audit_performance.py > perf_results.txt 2>&1
```

### Contact Information

- Documentation: See `PERFORMANCE_REPORT.md`, `PERFORMANCE_SUMMARY.md`
- Test Suite: Run `python test_audit_integration.py`
- Configuration: Edit `src/automation_orchestrator/audit.py`

---

## Post-Deployment Verification

### Checklist

Within 24 hours of deployment:

- [ ] Verify events are being logged: `tail -f logs/audit.log`
- [ ] Check health status is "healthy": `python health_check.py`
- [ ] Confirm backups are running: `python backup_audit.py list`
- [ ] Monitor dashboard shows activity: `python monitor_audit.py --once`
- [ ] No critical security events: `python health_check.py --verbose`
- [ ] Performance meets targets: `python test_audit_performance.py`

### Success Criteria

✅ **Deployment successful if**:
- Health check returns `status: healthy`
- Event rate matches expected load
- Buffer size stays <100
- No critical errors in logs
- Backups completing successfully

---

## Quick Reference

```bash
# Daily operations
python health_check.py                    # Check system health
python monitor_audit.py --once            # View metrics
python backup_audit.py backup             # Create backup

# Troubleshooting
python health_check.py --verbose          # Detailed health
python validate_config.py                 # Validate config
python test_audit_integration.py          # Run tests

# Performance
python test_audit_performance.py          # Benchmark
python monitor_audit.py --refresh 5       # Live monitoring

# Maintenance
python backup_audit.py list               # List backups
python backup_audit.py cleanup --keep 30  # Clean old backups
```

---

## Appendix: Configuration Reference

### All Constants

| Constant | Default | Range | Impact |
|----------|---------|-------|--------|
| `WRITE_BUFFER_SIZE` | 100 | 10-1000 | Batch size |
| `WRITE_FLUSH_INTERVAL` | 5.0 | 0.5-30 | Write latency |
| `QUERY_CACHE_SIZE` | 128 | 16-1000 | Memory usage |
| `COMPRESSION_LEVEL` | 6 | 1-9 | CPU vs size |
| `MAX_MEMORY_EVENTS` | 10000 | 1000-100000 | Stats memory |
| `MAX_DETAILS_SIZE` | 51200 | 1024-1048576 | Event size limit |
| `RATE_LIMIT_REQUESTS` | 100 | 10-1000 | Events/sec/source |
| `RATE_LIMIT_BURST` | 200 | 50-2000 | Burst capacity |

### File Locations

| File | Purpose | Rotation |
|------|---------|----------|
| `logs/audit.log` | Main audit log | Auto at 100MB |
| `logs/audit.TIMESTAMP.log.gz` | Rotated compressed logs | 90 days |
| `logs/security_events.log` | Security monitoring | Manual |
| `backups/audit/` | Backup storage | Manual cleanup |
| `logs/.audit_secret` | HMAC secret key | Persistent |

---

**End of Deployment Guide**

For questions or issues, refer to:
- [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md) - Detailed optimization guide
- [PERFORMANCE_SUMMARY.md](PERFORMANCE_SUMMARY.md) - Quick reference
- [SECURITY_PHASE1_REPORT.md](SECURITY_PHASE1_REPORT.md) - Security fixes
- [SECURITY_PHASE2_REPORT.md](SECURITY_PHASE2_REPORT.md) - Advanced security
