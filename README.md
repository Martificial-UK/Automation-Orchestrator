# Automation Orchestrator

Enterprise-grade, config-driven automation platform built on JohnEngine. Automate lead management, CRM integration, email campaigns, and workflow orchestration with a modern web dashboard and comprehensive REST API. Designed for on-prem, one-time installation.

## 🚀 Features

### Core Capabilities
- **Lead Management** - Ingest, validate, score, and route leads automatically
- **CRM Integration** - Bi-directional sync with Salesforce and HubSpot
- **Workflow Orchestration** - Config-driven automation workflows with triggers and actions
- **Email Campaigns** - Automated nurture sequences and transactional emails
- **Analytics Dashboard** - Real-time metrics with Recharts visualizations
- **Audit Logging** - Comprehensive security and compliance tracking
- **REST API** - 60+ endpoints with OpenAPI documentation
- **Multi-tenancy** - Isolated workspaces for enterprise deployments
- **RBAC** - Role-based access control with fine-grained permissions

### Security
✅ **42 vulnerabilities fixed** (7 Critical, 15 High, 12 Medium, 8 Low)
- SMTP/Email injection prevention
- SSRF protection for webhooks
- Path traversal prevention
- PII anonymization
- Rate limiting & DOS protection
- Security event logging
- Input validation & output sanitization

## 📋 Prerequisites

- **Python 3.8+**
- **pip** package manager
- **Git** (optional, for cloning)

## 🛠️ Installation

### 1. Install Dependencies
```bash
cd "c:\AI Automation\Automation Orchestrator"
pip install -r requirements.txt
```

**Core packages installed:**
- `fastapi>=0.128.1` - REST API framework
- `uvicorn>=0.40.0` - ASGI server
- `pydantic>=2.12.5` - Data validation
- `requests` - HTTP client
- Additional security and integration packages

### 2. Configure Environment
Copy the example environment file:
```bash
copy .env.example .env
```

Edit `.env` and add your credentials:
```env
# CRM Integration
SALESFORCE_CLIENT_ID=your_client_id
SALESFORCE_CLIENT_SECRET=your_client_secret
HUBSPOT_API_KEY=your_api_key

# Email (SMTP)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password

# Security
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here
```

### 3. Review Configuration
Sample config located at: `src/config/sample_config.json`

Customize workflows, integrations, and security settings as needed.

## 🔑 Licensing & Support (On-Prem)

- **Trial**: 7-day trial on first start
- **License**: One-time license key unlocks full access
- **Support**: Optional Bronze/Silver/Gold packages

See [INSTALL.md](INSTALL.md) and [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) for details.

## 🚦 Quick Start

### Option 1: Run API Server with Dashboard
```bash
cd "c:\AI Automation\Automation Orchestrator\src"
python -m automation_orchestrator.main --api --host 127.0.0.1 --port 8000
```

**Access points:**
- **Dashboard**: http://127.0.0.1:8000/
- **API Docs**: http://127.0.0.1:8000/api/docs
- **OpenAPI Schema**: http://127.0.0.1:8000/api/openapi.json

### Option 1b: Run Frontend Dev Server (Optional)
```bash
cd "c:\AI Automation\Automation Orchestrator\frontend"
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000` and will proxy API calls to `http://localhost:8000`.

### Option 2: Run CLI Mode
```bash
cd "c:\AI Automation\Automation Orchestrator\src"
python -m automation_orchestrator.main --config ./config/sample_config.json
```

## 📊 Dashboard

Modern analytics dashboard with real-time metrics:

### Features
- **6 Live Stat Cards**: Total Leads, Qualification Rate, Active Workflows, Emails Sent, Revenue, System Events
- **4 Recharts Visualizations**:
  - Lead Performance (bar chart)
  - Workflow Success Rate (doughnut chart)
  - Email Engagement (bar chart)
  - ROI Metrics (bar chart)
- **Recent Activity Feed** with status badges
- **Auto-refresh** every 30 seconds
- **Responsive design** for mobile and desktop

### Technology Stack
- React 18 - Modern frontend framework
- Vite - Fast dev server and build tooling
- Tailwind CSS - Utility-first styling
- Recharts - Data visualization
- Lucide React - Icon library
- Axios - API client

## 🔌 API Reference

### Core Endpoints

**System & Health**
- `GET /` - Serve dashboard
- `GET /health` - Health check
- `GET /health/detailed` - Detailed health status
- `GET /metrics` - Metrics endpoint
- `GET /api/docs` - Interactive API documentation
- `GET /api/openapi.json` - OpenAPI schema

**Authentication**
- `POST /api/auth/login` - Login and receive JWT
- `GET /api/auth/me` - Current user info
- `POST /api/auth/keys` - Create API key
- `GET /api/auth/keys` - List API keys
- `DELETE /api/auth/keys/{key_id}` - Revoke API key

**License**
- `GET /api/license/status` - License status
- `GET /api/license/purchase` - Purchase URL
- `POST /api/license/activate` - Activate license (admin)

**Monitoring**
- `GET /api/monitoring/alerts` - Active alerts
- `GET /api/monitoring/performance` - Performance metrics
- `POST /api/monitoring/alerts/threshold` - Update alert threshold
- `POST /api/monitoring/metrics/export` - Export metrics

**Lead Management**
- `POST /api/leads` - Ingest new lead
- `POST /api/leads/bulk` - Bulk lead import
- `GET /api/leads/{lead_id}` - Get lead details
- `PUT /api/leads/{lead_id}` - Update lead
- `DELETE /api/leads/{lead_id}` - Delete lead
- `POST /api/leads/deduplicate` - Deduplicate leads

**Deduplication**
- `POST /api/dedup` - Deduplicate batch
- `GET /api/dedup/config` - Deduplication config/statistics

**Workflow Management**
- `POST /api/workflows/trigger` - Trigger workflow
- `GET /api/workflows/{workflow_id}/status` - Get workflow status
- `GET /api/workflows/active` - List active workflows
- `POST /api/workflows/pause` - Pause workflow
- `POST /api/workflows/resume` - Resume workflow

**Workflow Builder**
- `GET /api/builder/templates` - Workflow templates

**CRM Integration**
- `POST /api/crm/salesforce/sync` - Sync to Salesforce
- `GET /api/crm/salesforce/lead/{sf_lead_id}` - Get Salesforce lead
- `POST /api/crm/hubspot/sync` - Sync to HubSpot
- `GET /api/crm/hubspot/contact/{contact_id}` - Get HubSpot contact
- `POST /api/crm/config` - Configure CRM
- `GET /api/crm/status` - Check CRM status

**Campaigns**
- `POST /api/campaigns/webhook` - Campaign webhook
- `GET /api/campaigns` - List campaigns
- `GET /api/campaigns/{campaign_id}/metrics` - Campaign metrics

**Email Campaigns**
- `POST /api/email/send` - Send email
- `POST /api/email/campaign` - Create campaign
- `GET /api/email/templates` - List templates
- `GET /api/email/campaign/{campaign_id}/stats` - Campaign stats

**Analytics**
- `GET /api/analytics/dashboard` - Dashboard metrics
- `GET /api/analytics/leads` - Lead analytics
- `GET /api/analytics/workflows` - Workflow analytics
- `GET /api/analytics/emails` - Email analytics
- `GET /api/analytics/roi` - ROI metrics
- `GET /api/analytics/daily` - Daily breakdown
- `GET /api/analytics/export` - Export analytics (JSON/CSV)

**Security & Audit**
- `GET /api/audit/events` - Audit event log
- `GET /api/audit/events/{event_id}` - Event details

**Admin (Audit Maintenance)**
- `POST /api/admin/audit/backup` - Backup audit log
- `GET /api/admin/audit/backups` - List audit backups

**Multi-tenancy**
- `GET /api/tenants` - List tenants
- `POST /api/tenants` - Create tenant
- `GET /api/tenants/{tenant_id}` - Get tenant details
- `PUT /api/tenants/{tenant_id}/plan` - Update tenant plan

**User Management (RBAC)**
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `PUT /api/users/{user_id}/role` - Update user role
- `GET /api/users/{user_id}` - Get user
- `POST /api/users/{user_id}/activate` - Activate user
- `POST /api/users/{user_id}/deactivate` - Deactivate user

### Endpoint Inventory (Generated from api.py)

Total endpoints: 65

| Method | Path |
|--------|------|
| GET | / |
| GET | /{full_path:path} |
| POST | /api/admin/audit/backup |
| GET | /api/admin/audit/backups |
| GET | /api/analytics/daily |
| GET | /api/analytics/dashboard |
| GET | /api/analytics/emails |
| GET | /api/analytics/export |
| GET | /api/analytics/leads |
| GET | /api/analytics/roi |
| GET | /api/analytics/workflows |
| GET | /api/audit/events |
| GET | /api/audit/events/{event_id} |
| GET | /api/auth/keys |
| POST | /api/auth/keys |
| DELETE | /api/auth/keys/{key_id} |
| POST | /api/auth/login |
| GET | /api/auth/me |
| GET | /api/builder/templates |
| GET | /api/campaigns |
| GET | /api/campaigns/{campaign_id}/metrics |
| POST | /api/campaigns/webhook |
| POST | /api/crm/config |
| GET | /api/crm/hubspot/contact/{contact_id} |
| POST | /api/crm/hubspot/sync |
| GET | /api/crm/salesforce/lead/{sf_lead_id} |
| POST | /api/crm/salesforce/sync |
| GET | /api/crm/status |
| POST | /api/dedup |
| GET | /api/dedup/config |
| POST | /api/email/campaign |
| GET | /api/email/campaign/{campaign_id}/stats |
| POST | /api/email/send |
| GET | /api/email/templates |
| GET | /api/leads |
| POST | /api/leads |
| DELETE | /api/leads/{lead_id} |
| GET | /api/leads/{lead_id} |
| PUT | /api/leads/{lead_id} |
| POST | /api/leads/bulk |
| POST | /api/leads/deduplicate |
| POST | /api/license/activate |
| GET | /api/license/purchase |
| GET | /api/license/status |
| GET | /api/monitoring/alerts |
| POST | /api/monitoring/alerts/threshold |
| POST | /api/monitoring/metrics/export |
| GET | /api/monitoring/performance |
| GET | /api/status |
| GET | /api/tenants |
| POST | /api/tenants |
| GET | /api/tenants/{tenant_id} |
| PUT | /api/tenants/{tenant_id}/plan |
| GET | /api/users |
| POST | /api/users |
| GET | /api/users/{user_id} |
| POST | /api/users/{user_id}/activate |
| POST | /api/users/{user_id}/deactivate |
| PUT | /api/users/{user_id}/role |
| GET | /api/workflows/{workflow_id}/status |
| GET | /api/workflows/active |
| POST | /api/workflows/trigger |
| GET | /health |
| GET | /health/detailed |
| GET | /metrics |

### Authentication
Most endpoints require authentication. Include API key in headers:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://127.0.0.1:8000/api/leads
```

## 🔒 Security

### Implemented Protections
1. **Email/SMTP Injection** - Validates and sanitizes email content
2. **SSRF Prevention** - Webhook URL validation with allowlist
3. **Path Traversal** - File path validation and sandboxing
4. **PII Protection** - Automatic anonymization of sensitive data
5. **Rate Limiting** - Request throttling per IP
6. **Input Validation** - Strict schema validation on all inputs
7. **XSS Prevention** - Output sanitization
8. **Audit Logging** - All security events tracked

### Configuration
See [SECURITY_CONFIG_GUIDE.md](SECURITY_CONFIG_GUIDE.md) for detailed security setup.

### Testing
Run security validation:
```bash
python security_validation.py
```

Expected: **9/9 tests passing**

## 🧪 Testing

### Run API Tests
```bash
cd "c:\AI Automation\Automation Orchestrator"
python -m pytest tests/test_api_endpoints.py -v
```

### Run Security Tests
```bash
python security_validation.py
```

### Run All Tests
```bash
python -m pytest tests/ -v
```

## 📁 Project Structure

```
Automation Orchestrator/
├── src/
│   ├── automation_orchestrator/
│   │   ├── main.py              # Entry point
│   │   ├── api.py               # FastAPI application (790 lines)
│   │   ├── lead_ingest.py       # Lead ingestion logic
│   │   ├── audit.py             # Audit logging
│   │   ├── security.py          # Security utilities (680 lines)
│   │   ├── salesforce_connector.py
│   │   ├── hubspot_connector.py
│   │   └── dashboard.html       # Web dashboard (800 lines)
│   └── config/
│       └── sample_config.json   # Sample configuration
├── tests/
│   └── test_api_endpoints.py    # API test suite
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── SECURITY_CONFIG_GUIDE.md     # Security documentation
└── API_DOCUMENTATION.md         # Detailed API docs
```

## 🔧 Configuration

### Workflow Configuration
Define workflows in `sample_config.json`:

```json
{
  "workflows": [
    {
      "id": "lead_qualification",
      "name": "Lead Qualification Workflow",
      "enabled": true,
      "triggers": ["new_lead", "lead_updated"],
      "actions": [
        {"type": "validate_lead"},
        {"type": "score_lead"},
        {"type": "sync_to_crm"}
      ]
    }
  ]
}
```

### Integration Configuration
Enable CRM integrations:

```json
{
  "integrations": {
    "salesforce": {
      "enabled": true,
      "instance_url": "https://your-instance.salesforce.com",
      "api_version": "v58.0"
    },
    "hubspot": {
      "enabled": true,
      "api_endpoint": "https://api.hubapi.com"
    }
  }
}
```

## 📖 Additional Documentation

- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference
- **[SECURITY_CONFIG_GUIDE.md](SECURITY_CONFIG_GUIDE.md)** - Security setup guide
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment instructions
- **[API_QUICK_START.md](API_QUICK_START.md)** - API usage examples

## 🐛 Troubleshooting

### API won't start
**Error**: `ModuleNotFoundError: No module named 'automation_orchestrator'`

**Solution**: Run from `src/` directory using module syntax:
```bash
cd src
python -m automation_orchestrator.main --api
```

### Dashboard shows no data
**Issue**: Mock data displayed instead of real data

**Solution**: Connect CRM integrations in `.env` and `sample_config.json`

### Deprecation warnings
**Issue**: Pydantic or FastAPI warnings

**Solution**: Already fixed in latest version. Update to latest code.

## 📝 License

Proprietary - JohnEngine Platform

## 🤝 Support

For issues, questions, or feature requests, contact the JohnEngine team.
