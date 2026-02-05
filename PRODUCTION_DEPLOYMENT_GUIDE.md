# Production Deployment Guide
# Complete guide for deploying Automation Orchestrator to production

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Database Configuration](#database-configuration)
4. [Deployment Options](#deployment-options)
5. [Security Hardening](#security-hardening)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

Before deploying to production, ensure:

- [ ] All security vulnerabilities resolved (see SECURITY_AUDIT_REPORT.md)
- [ ] SSL/TLS certificates obtained (Let's Encrypt or commercial CA)
- [ ] Database backups automated and tested
- [ ] Monitoring and alerting configured
- [ ] Load balancer configured with health checks
- [ ] Domain name configured and DNS propagated
- [ ] Environment variables documented and secured
- [ ] Rate limiting and DDoS protection configured
- [ ] API documentation reviewed and published
- [ ] Team trained on monitoring and incident response

---

## Environment Setup

### 1. Domain Configuration

```bash
# Create DNS A record
# Your Domain: automation-orchestrator.example.com
# Points to: Your Load Balancer IP (e.g., 34.67.12.45)

# Verify DNS propagation
nslookup automation-orchestrator.example.com
dig automation-orchestrator.example.com
```

### 2. SSL/TLS Certificates

#### Using Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --standalone \
  -d automation-orchestrator.example.com \
  -d api.automation-orchestrator.example.com \
  --agree-tos \
  -m admin@example.com

# Verify certificate
sudo certbot certificates

# Renew certificate (automated)
sudo certbot renew --dry-run
```

#### Certificate Paths
- **Certificate**: `/etc/letsencrypt/live/automation-orchestrator.example.com/fullchain.pem`
- **Private Key**: `/etc/letsencrypt/live/automation-orchestrator.example.com/privkey.pem`

### 3. Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH (with specific IP if possible)
sudo ufw allow from 203.0.113.0 to any port 22

# Block all other traffic
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Enable firewall
sudo ufw enable
```

### 4. Environment Variables

Create `.env.production`:

```bash
# API Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# Database
DATABASE_URL=postgresql://aouser:secure_password@db.example.com:5432/automation_orchestrator
DATABASE_POOL_SIZE=20
DATABASE_POOL_TIMEOUT=30

# Redis Cache
REDIS_URL=redis://redis.example.com:6379/0
REDIS_PASSWORD=secure_redis_password

# Authentication
JWT_SECRET=your-very-long-random-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Keys
API_KEY_PREFIX=ao_
API_KEY_LENGTH=32

# CORS
ALLOWED_ORIGINS=https://automation-orchestrator.example.com

# Email Notifications (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# APM & Monitoring (optional)
SENTRY_DSN=https://your-sentry-key@your-sentry-instance/12345
NEW_RELIC_LICENSE_KEY=your-newrelic-key
```

---

## Database Configuration

### 1. PostgreSQL Setup

#### On AWS RDS

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier automation-orchestrator \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.3 \
  --master-username aouser \
  --master-user-password your-secure-password \
  --allocated-storage 100 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-0123456789abcdef0 \
  --enable-iam-database-authentication \
  --backup-retention-period 30 \
  --enable-cloudwatch-logs-exports "postgresql"
```

#### Manual PostgreSQL Setup

```bash
# Connect to database server
psql -h db.example.com -U postgres

# Create database and user
CREATE DATABASE automation_orchestrator;
CREATE USER aouser WITH PASSWORD 'your-secure-password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE automation_orchestrator TO aouser;

# Enable extensions
\c automation_orchestrator
CREATE EXTENSION IF NOT EXISTS uuid-ossp;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 2. Database Migration

```bash
# Run migrations
python -m alembic upgrade head

# Verify schema
psql -h db.example.com -U aouser -d automation_orchestrator -c "\dt"
```

### 3. Backup Strategy

```bash
# Automated backup script (backup.sh)
#!/bin/bash
BACKUP_DIR="/backups/db"
BACKUP_FILE="$BACKUP_DIR/ao_backup_$(date +%Y%m%d_%H%M%S).sql.gz"

mkdir -p "$BACKUP_DIR"

# Full backup
pg_dump -h db.example.com -U aouser automation_orchestrator | \
  gzip > "$BACKUP_FILE"

# Keep only last 30 days
find "$BACKUP_DIR" -name "ao_backup_*.sql.gz" -mtime +30 -delete

# Upload to S3
aws s3 cp "$BACKUP_FILE" s3://your-backup-bucket/db-backups/
```

Setup cron job:
```bash
# Backup daily at 2 AM
0 2 * * * /scripts/backup.sh
```

---

## Deployment Options

### Option 1: Docker on EC2/VM

```bash
# 1. Build Docker image
docker build -t automation-orchestrator:latest .

# 2. Push to registry
docker tag automation-orchestrator:latest your-registry/automation-orchestrator:latest
docker push your-registry/automation-orchestrator:latest

# 3. Pull and run on server
cd /opt/automation-orchestrator
docker pull your-registry/automation-orchestrator:latest
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify running
docker-compose -f docker-compose.prod.yml ps
docker logs automation-orchestrator-api
```

### Option 2: Kubernetes (Recommended for Scale)

```bash
# 1. Create namespace
kubectl create namespace automation-orchestrator

# 2. Create secrets
kubectl create secret generic ao-secrets \
  --from-literal=JWT_SECRET=your-secret \
  --from-literal=DATABASE_URL=postgresql://... \
  --from-literal=REDIS_URL=redis://... \
  -n automation-orchestrator

# 3. Apply manifests
kubectl apply -f k8s/deployment.yaml -n automation-orchestrator
kubectl apply -f k8s/ingress.yaml -n automation-orchestrator

# 4. Verify deployment
kubectl get pods -n automation-orchestrator
kubectl logs -f deployment/automation-orchestrator-api -n automation-orchestrator

# 5. Check ingress
kubectl get ingress -n automation-orchestrator
```

### Option 3: AWS Elastic Beanstalk

```bash
# 1. Initialize EB
eb init -p docker automation-orchestrator --region us-east-1

# 2. Create environment
eb create prod-environment --instance-type t3.medium

# 3. Deploy
eb deploy

# 4. Monitor
eb status
eb logs
```

### Option 4: Lambda + API Gateway (Serverless)

Supported but requires significant refactoring. See AWS Lambda guide for details.

---

## Security Hardening

### 1. Network Security

```bash
# Enable VPC endpoint for RDS
# Enable VPC endpoint for S3
# Use security groups to restrict access

# Security Group for API (inbound)
- SSH (22): From specific admin IPs only
- HTTP (80): From load balancer
- HTTPS (443): From load balancer

# Security Group for DB (inbound)
- PostgreSQL (5432): From API security group only
```

### 2. Application Security

```python
# In api.py - Add security headers
from fastapi.middleware import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["automation-orchestrator.example.com"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://automation-orchestrator.example.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Secret Management

```bash
# Using AWS Secrets Manager
aws secretsmanager create-secret \
  --name automation-orchestrator/jwt-secret \
  --secret-string "your-very-long-random-secret"

# Retrieve secret in application
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='automation-orchestrator/jwt-secret')
```

### 4. Image Security

```bash
# Scan Docker image for vulnerabilities
docker scout cves automation-orchestrator:latest

# Sign Docker images
cosign sign --key cosign.key automation-orchestrator:latest
```

---

## Monitoring & Alerting

### 1. Prometheus Scraping

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'automation-orchestrator'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 2. Grafana Dashboards

Import pre-built dashboards:
- FastAPI Dashboard: ID 12114
- PostgreSQL Dashboard: ID 3742
- Redis Dashboard: ID 11114

### 3. Alert Rules

```yaml
# alerts.yml
groups:
  - name: automation-orchestrator
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / 1024 / 1024 / 1024 > 0.9
        for: 5m
        annotations:
          summary: "High memory usage"

      - alert: DatabaseConnectionPoolExhausted
        expr: pg_stat_activity_count > 18
        for: 2m
        annotations:
          summary: "Database connection pool exhausted"
```

### 4. CloudWatch Integration (AWS)

```python
# Using AWS CloudWatch
import boto3
import logging

cloudwatch = boto3.client('cloudwatch')

# Custom metrics
cloudwatch.put_metric_data(
    Namespace='AutomationOrchestrator',
    MetricData=[
        {
            'MetricName': 'RequestLatency',
            'Value': latency_ms,
            'Unit': 'Milliseconds'
        }
    ]
)
```

---

## Backup & Recovery

### 1. Full Backup Strategy

```bash
# Database backup
0 2 * * * /scripts/backup_database.sh

# Application files backup (if stateful)
0 3 * * * /scripts/backup_files.sh

# Configuration backup
0 4 * * * /scripts/backup_config.sh
```

### 2. Recovery Procedure

```bash
# 1. Restore database
pg_restore -h db.example.com -U aouser -d automation_orchestrator < backup.sql

# 2. Restart application
docker-compose restart api

# 3. Verify
curl https://automation-orchestrator.example.com/health
```

### 3. Disaster Recovery Plan

- **RTO** (Recovery Time Objective): 1 hour
- **RPO** (Recovery Point Objective): 1 hour
- Test recovery monthly
- Document runbooks for all scenarios

---

## Troubleshooting

### Common Issues

#### 1. SSL Certificate Errors

```bash
# Verify certificate
openssl s_client -connect automation-orchestrator.example.com:443

# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/.../fullchain.pem -noout -dates

# Renew certificate
certbot renew --force-renewal
```

#### 2. Database Connection Failures

```bash
# Test database connection
psql -h db.example.com -U aouser -d automation_orchestrator -c "SELECT NOW();"

# Check logs
docker logs automation-orchestrator-api | grep -i "database"

# Verify network connectivity
telnet db.example.com 5432
```

#### 3. High Memory Usage

```bash
# Check memory stats
docker stats automation-orchestrator-api

# Identify memory leaks
python -m memory_profiler your_script.py

# Restart container
docker restart automation-orchestrator-api
```

#### 4. API Response Slow

```bash
# Check logs for slow queries
docker logs -f automation-orchestrator-api | grep "duration"

# Profile application
python -m cProfile -o profile.prof your_script.py

# Analyze profile
python -m pstats profile.prof
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Start with additional diagnostics
docker-compose -f docker-compose.prod.yml logs -f

# Interactive debugging
docker exec -it automation-orchestrator-api /bin/bash
```

---

## SLA & Performance Targets

- **Uptime**: 99.95%
- **Response Time (p95)**: < 200ms
- **Error Rate**: < 0.1%
- **Database Connections**: < 90% utilized
- **Memory Usage**: < 80% of limit
- **CPU Usage**: < 75% of limit

---

## Post-Deployment Checklist

- [ ] Health checks passing
- [ ] Monitoring active and alerting configured
- [ ] Backups running and verifiable
- [ ] SSL/TLS working correctly
- [ ] Team trained on deployment
- [ ] Runbooks documented
- [ ] Incident response plan reviewed
- [ ] Performance baseline established
- [ ] Load testing completed
- [ ] Documentation updated

---

For additional support, see:
- DATABASE_SETUP_GUIDE.md
- SSL_TLS_SETUP_GUIDE.md
- USER_SECURITY_IMPLEMENTATION.md
- SECURITY_AUDIT_REPORT.md
