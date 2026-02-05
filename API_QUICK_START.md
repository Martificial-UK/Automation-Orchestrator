# REST API Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd "c:\AI Automation\Automation Orchestrator"
pip install -r requirements.txt
```

### 2. Configure CRM Connection

Choose your CRM and copy the appropriate config:

**For Salesforce:**
```bash
cp config/salesforce_config.json config/active_config.json
```

**For HubSpot:**
```bash
cp config/hubspot_config.json config/active_config.json
```

edit `config/active_config.json` and add your credentials

### 3. Start API Server

```bash
# Using environment variable
set AO_CONFIG=./config/active_config.json
python -m automation_orchestrator.main --api

# Or direct config path
python -m automation_orchestrator.main --api --config ./config/active_config.json
```

You should see:
```
✓ Starting REST API Server
  Host: 0.0.0.0
  Port: 8000
  Documentation: http://0.0.0.0:8000/api/docs
  OpenAPI Schema: http://0.0.0.0:8000/api/openapi.json
```

### 4. Access API

Open browser to:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### 5. Test with Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "api": "running",
    "audit": "running",
    "crm_connector": "ready",
    "lead_ingest": "ready",
    "workflow_runner": "running"
  }
}
```

---

## Common Tasks

### Create Your First Lead

```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-123-4567",
    "company": "Your Company",
    "source": "api_test"
  }'
```

### Configure CRM

**Salesforce:**
```bash
curl -X POST http://localhost:8000/api/crm/config \
  -H "Content-Type: application/json" \
  -d '{
    "crm_type": "salesforce",
    "instance_url": "https://na1.salesforce.com",
    "access_token": "your_access_token"
  }'
```

**HubSpot:**
```bash
curl -X POST http://localhost:8000/api/crm/config \
  -H "Content-Type: application/json" \
  -d '{
    "crm_type": "hubspot",
    "api_key": "pat-na1-your-api-key"
  }'
```

### Check CRM Status

```bash
curl http://localhost:8000/api/crm/status
```

### Trigger Workflow

```bash
curl -X POST http://localhost:8000/api/workflows/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "welcome_sequence",
    "lead_data": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "company": "Your Company"
    }
  }'
```

---

## Salesforce Configuration

### Get Your Credentials

1. **Login to Salesforce**
   - https://login.salesforce.com

2. **Create Connected App**
   - Setup → App Manager → New Connected App
   - Enable OAuth Settings
   - Set Redirect URI to: `http://localhost:8000/callback`
   - Note your Client ID and Client Secret

3. **Generate Security Token**
   - Your Name → Settings → Reset My Security Token
   - Check your email for token

4. **Get Instance URL**
   - Your Name → Settings → API (Web Services)
   - Copy REST API Endpoint (e.g., https://na1.salesforce.com)

### Configure

Edit `config/active_config.json`:
```json
{
  "crm": {
    "crm_type": "salesforce",
    "instance_url": "https://na1.salesforce.com",
    "client_id": "3MVG9ph....",
    "client_secret": "1234567890abcdef",
    "username": "your_username@example.com",
    "password": "your_password",
    "security_token": "1a2b3c4d5e6f"
  }
}
```

---

## HubSpot Configuration

### Get Your Credentials

1. **Login to HubSpot**
   - https://app.hubspot.com

2. **Create Private App**
   - Settings → Developer & API → Private Apps
   - Create New Private App
   - Select scopes: crm.objects.contacts.read and crm.objects.contacts.write
   - Generate access token

3. **Copy Access Token**
   - Note: Save this immediately, you won't see it again!

### Configure

Edit `config/active_config.json`:
```json
{
  "crm": {
    "crm_type": "hubspot",
    "api_key": "pat-na1-abcd1234-5678-9012-efgh-ijklmnopqrst"
  }
}
```

---

## API Endpoint Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | System health check |
| GET | `/api/status` | API status |
| POST | `/api/leads` | Create lead |
| GET | `/api/leads` | List leads |
| GET | `/api/leads/{id}` | Get lead |
| PUT | `/api/leads/{id}` | Update lead |
| POST | `/api/workflows/trigger` | Trigger workflow |
| GET | `/api/workflows/{id}/status` | Check workflow status |
| POST | `/api/crm/config` | Configure CRM |
| GET | `/api/crm/status` | Check CRM status |
| POST | `/api/email/send` | Send email |

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for full details.

---

## Troubleshooting

### "Module not found" errors

Make sure you're in the right directory:
```bash
cd "c:\AI Automation\Automation Orchestrator"
```

### FastAPI not found

Install requirements:
```bash
pip install -r requirements.txt
```

### CRM Connection Failed

1. Check credentials in config file
2. Test connectivity: `telnet instance.salesforce.com 443`
3. Verify API token/key is valid
4. Check firewall permissions

### Port 8000 Already in Use

Use a different port:
```bash
python -m automation_orchestrator.main --api --port 8080
```

---

## Next Steps

1. ✓ REST API running
2. ✓ CRM connected
3. ⏭️ [Build Dashboard](../docs/dashboard.md)
4. ⏭️ [Set Up Multi-Tenancy](../docs/multi-tenancy.md)
5. ⏭️ [Create Custom Workflows](../docs/workflows.md)

---

## Support Files

- **Full API Docs**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Salesforce Config Example**: [config/salesforce_config.json](config/salesforce_config.json)
- **HubSpot Config Example**: [config/hubspot_config.json](config/hubspot_config.json)
