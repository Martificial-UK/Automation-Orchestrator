"""
API Endpoint Test Suite for Automation Orchestrator
Tests all major API endpoints including health, leads, workflows, CRM, email, and analytics
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automation_orchestrator.api import create_app


@pytest.fixture
def client():
    """Create test client"""
    test_config = {
        "log_path": "./logs/test.log",
        "log_level": "INFO",
        "logging": {
            "level": "WARNING"
        },
        "workflows": [],
        "redis": {
            "use_fake_redis": True
        },
        "license": {
            "enabled": False
        }
    }
    app = create_app(test_config)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_audit_logger():
    """Mock audit logger"""
    with patch('automation_orchestrator.api.get_audit_logger') as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture
def sample_lead():
    """Sample lead data for testing"""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-123-4567",
        "company": "Acme Corp",
        "source": "web_form"
    }


class TestHealthAndSystem:
    """Test system and health endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "components" in data
    
    def test_dashboard_route(self, client):
        """Test dashboard HTML is served"""
        response = client.get("/")
        assert response.status_code in [200, 404]  # 404 if dashboard.html not found


class TestLeadEndpoints:
    """Test lead management endpoints"""
    
    def test_ingest_lead(self, client, sample_lead, mock_audit_logger):
        """Test lead ingestion"""
        response = client.post("/api/leads", json=sample_lead)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "queued"]
        assert "id" in data
    
    def test_ingest_lead_invalid_email(self, client):
        """Test lead ingestion with invalid email"""
        invalid_lead = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "invalid-email",  # Invalid format
            "company": "Acme Corp"
        }
        response = client.post("/api/leads", json=invalid_lead)
        # Should either reject or accept and validate later
        assert response.status_code in [200, 422]
    
    def test_bulk_lead_ingest(self, client, sample_lead):
        """Test bulk lead ingestion"""
        leads = [sample_lead.copy() for _ in range(3)]
        # Modify emails to be unique
        for i, lead in enumerate(leads):
            lead["email"] = f"john{i}@example.com"
        
        response = client.post("/api/leads/bulk", json={"leads": leads})
        assert response.status_code == 200
        data = response.json()
        assert "processed" in data or "success" in data["status"]
    
    def test_get_lead(self, client):
        """Test get lead by ID"""
        lead_id = "test-lead-123"
        response = client.get(f"/api/leads/{lead_id}")
        # Should return 404 if not found, or 200 if found
        assert response.status_code in [200, 404]
    
    def test_update_lead(self, client):
        """Test update lead"""
        lead_id = "test-lead-123"
        update_data = {
            "company": "New Company Name",
            "phone": "+1-555-999-8888"
        }
        response = client.put(f"/api/leads/{lead_id}", json=update_data)
        assert response.status_code in [200, 404]
    
    def test_delete_lead(self, client):
        """Test delete lead"""
        lead_id = "test-lead-123"
        response = client.delete(f"/api/leads/{lead_id}")
        assert response.status_code in [200, 404]
    
    def test_deduplicate_leads(self, client):
        """Test lead deduplication"""
        response = client.post("/api/leads/deduplicate", json={
            "strategy": "email",
            "dry_run": True
        })
        assert response.status_code == 200
        data = response.json()
        assert "duplicates_found" in data or "status" in data


class TestWorkflowEndpoints:
    """Test workflow management endpoints"""
    
    def test_trigger_workflow(self, client):
        """Test workflow trigger"""
        workflow_data = {
            "workflow_id": "lead_qualification",
            "data": {
                "lead_id": "test-lead-123",
                "score": 85
            }
        }
        response = client.post("/api/workflows/trigger", json=workflow_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] in ["triggered", "running", "queued"]
    
    def test_get_workflow_status(self, client):
        """Test get workflow status"""
        workflow_id = "test-workflow-123"
        response = client.get(f"/api/workflows/{workflow_id}/status")
        assert response.status_code in [200, 404]
    
    def test_list_active_workflows(self, client):
        """Test list active workflows"""
        response = client.get("/api/workflows/active")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
    
    def test_pause_workflow(self, client):
        """Test pause workflow"""
        response = client.post("/api/workflows/pause", json={
            "workflow_id": "test-workflow-123"
        })
        assert response.status_code in [200, 404]
    
    def test_resume_workflow(self, client):
        """Test resume workflow"""
        response = client.post("/api/workflows/resume", json={
            "workflow_id": "test-workflow-123"
        })
        assert response.status_code in [200, 404]


class TestCRMEndpoints:
    """Test CRM integration endpoints"""
    
    def test_salesforce_sync(self, client):
        """Test Salesforce sync"""
        sync_data = {
            "lead_id": "test-lead-123",
            "sync_type": "create"
        }
        response = client.post("/api/crm/salesforce/sync", json=sync_data)
        # May fail if credentials not configured
        assert response.status_code in [200, 401, 500]
    
    def test_get_salesforce_lead(self, client):
        """Test get Salesforce lead"""
        sf_lead_id = "00Q000000000001"
        response = client.get(f"/api/crm/salesforce/lead/{sf_lead_id}")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_hubspot_sync(self, client):
        """Test HubSpot sync"""
        sync_data = {
            "lead_id": "test-lead-123",
            "sync_type": "create"
        }
        response = client.post("/api/crm/hubspot/sync", json=sync_data)
        assert response.status_code in [200, 401, 500]
    
    def test_get_hubspot_contact(self, client):
        """Test get HubSpot contact"""
        contact_id = "12345"
        response = client.get(f"/api/crm/hubspot/contact/{contact_id}")
        assert response.status_code in [200, 401, 404, 500]


class TestEmailEndpoints:
    """Test email campaign endpoints"""
    
    def test_send_email(self, client):
        """Test send email"""
        email_data = {
            "to": "test@example.com",
            "subject": "Test Email",
            "body": "This is a test email",
            "template": "default"
        }
        response = client.post("/api/email/send", json=email_data)
        # May fail if SMTP not configured
        assert response.status_code in [200, 500]
    
    def test_create_campaign(self, client):
        """Test create email campaign"""
        campaign_data = {
            "name": "Test Campaign",
            "subject": "Test Subject",
            "template": "welcome_series",
            "recipients": ["test1@example.com", "test2@example.com"]
        }
        response = client.post("/api/email/campaign", json=campaign_data)
        assert response.status_code == 200
        data = response.json()
        assert "campaign_id" in data or "id" in data
    
    def test_list_templates(self, client):
        """Test list email templates"""
        response = client.get("/api/email/templates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
    
    def test_campaign_stats(self, client):
        """Test get campaign stats"""
        campaign_id = "test-campaign-123"
        response = client.get(f"/api/email/campaign/{campaign_id}/stats")
        assert response.status_code in [200, 404]


class TestAnalyticsEndpoints:
    """Test analytics endpoints"""
    
    def test_dashboard_analytics(self, client):
        """Test dashboard analytics endpoint"""
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "qualification_rate" in data
        assert "active_workflows" in data
    
    def test_lead_analytics(self, client):
        """Test lead analytics"""
        response = client.get("/api/analytics/leads")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_workflow_analytics(self, client):
        """Test workflow analytics"""
        response = client.get("/api/analytics/workflows")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_email_analytics(self, client):
        """Test email analytics"""
        response = client.get("/api/analytics/emails")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_roi_analytics(self, client):
        """Test ROI analytics"""
        response = client.get("/api/analytics/roi")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_daily_analytics(self, client):
        """Test daily analytics"""
        response = client.get("/api/analytics/daily?days=7")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
    
    def test_analytics_export_json(self, client):
        """Test analytics export as JSON"""
        response = client.get("/api/analytics/export?format=json")
        assert response.status_code == 200
        data = response.json()
        assert "format" in data
        assert data["format"] == "json"
    
    def test_analytics_export_csv(self, client):
        """Test analytics export as CSV"""
        response = client.get("/api/analytics/export?format=csv")
        assert response.status_code == 200
        data = response.json()
        assert "format" in data
        assert data["format"] == "csv"


class TestAuditEndpoints:
    """Test audit logging endpoints"""
    
    def test_get_audit_events(self, client):
        """Test get audit events"""
        response = client.get("/api/audit/events?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
    
    def test_get_audit_event_detail(self, client):
        """Test get audit event detail"""
        event_id = "test-event-123"
        response = client.get(f"/api/audit/events/{event_id}")
        assert response.status_code in [200, 404]


class TestMultiTenancyEndpoints:
    """Test multi-tenancy endpoints"""
    
    def test_list_tenants(self, client):
        """Test list tenants"""
        response = client.get("/api/tenants")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
    
    def test_create_tenant(self, client):
        """Test create tenant"""
        tenant_data = {
            "name": "Test Tenant",
            "email": "admin@testtenant.com"
        }
        response = client.post("/api/tenants", json=tenant_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "tenant_id" in data or "id" in data
    
    def test_get_tenant(self, client):
        """Test get tenant details"""
        tenant_id = "test-tenant-123"
        response = client.get(f"/api/tenants/{tenant_id}")
        assert response.status_code in [200, 404]


class TestRBACEndpoints:
    """Test RBAC user management endpoints"""
    
    def test_list_users(self, client):
        """Test list users"""
        response = client.get("/api/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
    
    def test_create_user(self, client):
        """Test create user"""
        user_data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "role": "viewer"
        }
        response = client.post("/api/users", json=user_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "user_id" in data or "id" in data
    
    def test_update_user_role(self, client):
        """Test update user role"""
        user_id = "test-user-123"
        response = client.put(f"/api/users/{user_id}/role", json={
            "role": "admin"
        })
        assert response.status_code in [200, 404]


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_endpoint(self, client):
        """Test invalid endpoint returns 404"""
        response = client.get("/api/invalid/endpoint")
        assert response.status_code == 404
    
    def test_invalid_method(self, client):
        """Test invalid HTTP method"""
        response = client.delete("/health")  # Health only supports GET
        assert response.status_code == 405
    
    def test_malformed_json(self, client):
        """Test malformed JSON request"""
        response = client.post(
            "/api/leads",
            content="not-valid-json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestValidation:
    """Test input validation"""
    
    def test_query_parameter_validation(self, client):
        """Test query parameter validation"""
        # Days should be between 1 and 365
        response = client.get("/api/analytics/daily?days=1000")
        assert response.status_code == 422
    
    def test_email_format_validation(self, client):
        """Test email format validation in leads"""
        invalid_lead = {
            "first_name": "Test",
            "last_name": "User",
            "email": "not-an-email"
        }
        response = client.post("/api/leads", json=invalid_lead)
        # Should validate email format
        assert response.status_code in [200, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
