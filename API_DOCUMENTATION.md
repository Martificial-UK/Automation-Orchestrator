# REST API Documentation

## Overview

The Automation Orchestrator REST API provides comprehensive endpoints for:
- Lead management and CRUD operations
- Workflow execution and monitoring  
- CRM configuration and status
- Email campaign management
- System health and status

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run API Server

```bash
# Default: localhost:8000
python -m automation_orchestrator.main --api

# Custom host/port
python -m automation_orchestrator.main --api --host 0.0.0.0 --port 8080

# With custom config
python -m automation_orchestrator.main --api --config ./config/production.json
```

### 3. Access Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI Schema**: http://localhost:8000/api/openapi.json

---

## API Endpoints

### Health & Status

#### `GET /health`
Check system health status.

**Response:**
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

#### `GET /api/status`
Get detailed API status.

**Response:**
```json
{
  "api_version": "1.0.0",
  "status": "online",
  "timestamp": "2024-01-15T10:30:00Z",
  "endpoints": {
    "leads": "available",
    "workflows": "available",
    "crm": "available",
    "email": "available"
  }
}
```

---

## Lead Management

### Create Lead

#### `POST /api/leads`
Create a new lead and optionally create in CRM.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1-555-123-4567",
  "company": "Acme Corporation",
  "source": "web_form",
  "custom_fields": {
    "industry": "Technology",
    "employee_count": "100-500"
  }
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "created",
  "message": "Lead created successfully",
  "crm_id": "00Q4z00000IZ3TEAA4",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-123-4567",
    "company": "Acme Corporation",
    "source": "web_form"
  }
}
```

**Triggers:**
- Audit event: `lead_ingested`
- CRM creation (if configured)
- Workflow execution (if configured)

---

### Get Lead

#### `GET /api/leads/{lead_id}`
Retrieve lead details.

**Parameters:**
- `lead_id` (path): Lead ID or CRM ID

**Response (200):**
```json
{
  "id": "00Q4z00000IZ3TEAA4",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1-555-123-4567",
  "company": "Acme Corporation",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

**Error (404):**
```json
{
  "error": "Lead not found",
  "status_code": 404,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### List Leads

#### `GET /api/leads`
List leads with optional filtering and pagination.

**Query Parameters:**
- `skip` (int, default: 0): Number of records to skip
- `limit` (int, default: 100, max: 1000): Records to return
- `source` (string, optional): Filter by lead source
- `email` (string, optional): Filter by email

**Example:**
```
GET /api/leads?skip=0&limit=50&source=web_form
```

**Response (200):**
```json
{
  "total": 150,
  "skip": 0,
  "limit": 50,
  "leads": [
    {
      "id": "00Q4z00000IZ3TEAA4",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "company": "Acme Corporation",
      "source": "web_form"
    },
    {
      "id": "00Q4z00000IZ3UFAA4",
      "first_name": "Jane",
      "last_name": "Smith",
      "email": "jane.smith@example.com",
      "company": "Tech Innovations",
      "source": "web_form"
    }
  ]
}
```

---

### Update Lead

#### `PUT /api/leads/{lead_id}`
Update lead information.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@newemail.com",
  "phone": "+1-555-987-6543",
  "company": "New Company",
  "source": "web_form"
}
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "updated",
  "message": "Lead updated successfully",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@newemail.com",
    "phone": "+1-555-987-6543",
    "company": "New Company",
    "source": "web_form"
  }
}
```

**Triggers:**
- Audit event: `crm_update`
- CRM update (if configured)

---

## Workflow Management

### Trigger Workflow

#### `POST /api/workflows/trigger`
Manually trigger a workflow execution.

**Request Body:**
```json
{
  "workflow_id": "workflow_001",
  "lead_id": "550e8400-e29b-41d4-a716-446655440000",
  "lead_data": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "company": "Acme Corp"
  },
  "custom_context": {
    "priority": "high",
    "campaign_id": "campaign_2024_q1"
  }
}
```

**Response (202):**
```json
{
  "workflow_id": "workflow_001",
  "execution_id": "exec_550e8400-e29b-41d4-a716-446655440000",
  "status": "triggered",
  "message": "Workflow execution started",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Triggers:**
- Audit event: `workflow_started`
- Background workflow execution

---

### Get Workflow Status

#### `GET /api/workflows/{workflow_id}/status`
Check workflow execution status.

**Parameters:**
- `workflow_id` (path): Workflow ID

**Response (200):**
```json
{
  "workflow_id": "workflow_001",
  "status": "running",
  "execution_count": 42,
  "last_execution": {
    "execution_id": "exec_550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "leads_processed": 5,
    "completed_at": "2024-01-15T10:25:00Z"
  }
}
```

---

## CRM Management

### Configure CRM

#### `POST /api/crm/config`
Configure or update CRM connection.

**Request Body - Salesforce:**
```json
{
  "crm_type": "salesforce",
  "instance_url": "https://na1.salesforce.com",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "username": "your_username@example.com",
  "password": "your_password",
  "security_token": "your_security_token",
  "mapping": {
    "source": "LeadSource",
    "company": "Company"
  }
}
```

**Request Body - HubSpot:**
```json
{
  "crm_type": "hubspot",
  "api_key": "pat-na1-your-api-key",
  "field_mapping": {
    "source": "hs_lead_status",
    "company": "company"
  }
}
```

**Valid CRM Types:**
- `salesforce`
- `hubspot`
- `dynamics`
- `zoho`
- `generic` (for custom APIs)

**Response (200):**
```json
{
  "status": "configured",
  "crm_type": "salesforce",
  "message": "CRM configuration updated"
}
```

**Error (400):**
```json
{
  "error": "Invalid CRM type. Must be one of: salesforce, hubspot, dynamics, zoho, generic",
  "status_code": 400,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### Check CRM Status

#### `GET /api/crm/status`
Check CRM connection status and test connection.

**Response (200) - Connected:**
```json
{
  "status": "connected",
  "connector_type": "SalesforceConnector",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response (200) - Not Configured:**
```json
{
  "status": "not_configured",
  "message": "No CRM connector configured"
}
```

**Response (500) - Connection Error:**
```json
{
  "error": "Internal server error",
  "status_code": 500,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Email Management

### Send Email

#### `POST /api/email/send`
Send email to a lead using a template.

**Query Parameters:**
- `lead_id` (required): Target lead ID
- `template_id` (required): Email template ID
- `custom_subject` (optional): Override template subject

**Request:**
```
POST /api/email/send?lead_id=550e8400-e29b-41d4-a716-446655440000&template_id=welcome_email&custom_subject=Welcome%20to%20Acme
```

**Response (202):**
```json
{
  "status": "sent",
  "execution_id": "email_550e8400-e29b-41d4-a716-446655440000",
  "lead_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Triggers:**
- Audit event: `email_sent`
- Background email delivery

---

## Error Handling

All endpoints follow standard HTTP status codes:

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Lead retrieved |
| 201 | Created | New lead created |
| 202 | Accepted | Workflow triggered (async) |
| 400 | Bad Request | Invalid CRM type |
| 404 | Not Found | Lead doesn't exist |
| 500 | Server Error | Internal error |

**Error Response Format:**
```json
{
  "error": "Description of error",
  "status_code": 400,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Authentication

The current API uses no authentication by default. For production, consider adding:

- **API Key Authentication**: Bearer tokens in Authorization header
- **OAuth 2.0**: For user-based access
- **JWT**: For stateless authentication
- **TLS/HTTPS**: Always use HTTPS in production

---

## Rate Limiting

Current rate limiting (configurable):
- **Default**: 100 events per second per source
- **Burst**: 200 events allowed

---

## Examples

### Python Example

```python
import requests

# Create a lead
lead_data = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "company": "Acme Corp",
    "source": "api"
}

response = requests.post(
    "http://localhost:8000/api/leads",
    json=lead_data
)

if response.status_code == 201:
    lead = response.json()
    print(f"Created lead: {lead['id']}")
    
    # Trigger workflow
    workflow_data = {
        "workflow_id": "welcome_sequence",
        "lead_id": lead['id'],
        "lead_data": lead_data
    }
    
    workflow_response = requests.post(
        "http://localhost:8000/api/workflows/trigger",
        json=workflow_data
    )
    print(f"Triggered workflow: {workflow_response.json()['execution_id']}")
```

### cURL Examples

```bash
# Check health
curl http://localhost:8000/health

# Create lead
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "company": "Acme Corp"
  }'

# List leads
curl "http://localhost:8000/api/leads?limit=10&source=web_form"

# Configure Salesforce
curl -X POST http://localhost:8000/api/crm/config \
  -H "Content-Type: application/json" \
  -d '{
    "crm_type": "salesforce",
    "instance_url": "https://na1.salesforce.com",
    "access_token": "your_access_token"
  }'

# Check CRM status
curl http://localhost:8000/api/crm/status

# Trigger workflow
curl -X POST http://localhost:8000/api/workflows/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "welcome_sequence",
    "lead_data": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com"
    }
  }'
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8000';

// Create a lead
async function createLead(leadData) {
  try {
    const response = await axios.post(`${API_URL}/api/leads`, leadData);
    console.log('Lead created:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error creating lead:', error.response.data);
  }
}

// Trigger workflow
async function triggerWorkflow(workflowId, leadData) {
  try {
    const response = await axios.post(`${API_URL}/api/workflows/trigger`, {
      workflow_id: workflowId,
      lead_data: leadData
    });
    console.log('Workflow triggered:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error triggering workflow:', error.response.data);
  }
}

// Usage
const lead = await createLead({
  first_name: 'John',
  last_name: 'Doe',
  email: 'john@example.com',
  company: 'Acme Corp'
});

await triggerWorkflow('welcome_sequence', lead.data);
```

---

## Configuration

The API server reads configuration from the same JSON config file as CLI mode:

```json
{
  "log_path": "./logs/automation_orchestrator.log",
  "log_level": "INFO",
  "crm": {
    "crm_type": "salesforce",
    "instance_url": "https://na1.salesforce.com",
    "access_token": "your_token"
  },
  "lead_ingest": {},
  "email": {},
  "workflow": {}
}
```

---

## Monitoring & Logging

All API requests are logged to:
- **Audit log**: `logs/audit.log` - All operations
- **Error log**: `logs/security_events.log` - Security events
- **Application log**: `logs/automation_orchestrator.log` - General logs

---

## Support & Documentation

- **API Docs**: http://localhost:8000/api/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health
- **Status**: http://localhost:8000/api/status
